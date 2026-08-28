"""Integration test for the scheduled arming runtime.

Tests the full arm → disarm cycle end-to-end:
  1. Create a schedule via the WS API.
  2. Advance HA's virtual clock to the arm time.
  3. Verify the alarm_control_panel state transitions to armed_home.
  4. Advance to the disarm time.
  5. Verify the panel transitions to disarmed.
  6. Verify schedule_fired events on the bus.

Uses the HA test harness with a real ScheduleManager, HAScheduleClock, and
HAClock.  HAModeChanger is replaced by a thin stub that drives the HA state
directly so the test is self-contained (no Docker required).

``@pytest.mark.integration`` keeps these out of the normal ``uv run pytest``
run.  They are included in ``uv run pytest -m integration`` / ``-m ""``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import event as ha_event
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.abode_security.const import (
    DOMAIN,
    EVENT_SCHEDULE_FIRED,
    EVENT_SCHEDULE_SKIPPED,
)
from custom_components.abode_security.scheduling.clock import HAClock
from custom_components.abode_security.scheduling.manager import ScheduleManager
from custom_components.abode_security.scheduling.models import ChangeSource
from custom_components.abode_security.scheduling.scheduler import HAScheduleClock
from custom_components.abode_security.scheduling.store import SchedulesStore
from custom_components.abode_security.websocket_api import (
    async_register_websocket_commands,
)

# Arm/disarm times in 2030 so they're safely in the future.
_ARM_DT = datetime(2030, 1, 7, 22, 0, 0, tzinfo=UTC)
_DISARM_DT = datetime(2030, 1, 8, 6, 0, 0, tzinfo=UTC)

_PANEL = "alarm_control_panel.abode_test"


class _StateUpdatingModeChanger:
    """ModeChanger stub that drives the HA state directly."""

    TARGET_STATES = {
        "home": "armed_home",
        "standby": "disarmed",
        "away": "armed_away",
    }

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self.calls: list[dict[str, Any]] = []

    async def async_set_mode(
        self,
        target: str,
        source: ChangeSource,
        *,
        pair_id: str | None = None,
    ) -> None:
        self.calls.append({"target": target, "source": source, "pair_id": pair_id})
        new_state = self.TARGET_STATES.get(target, target)
        self._hass.states.async_set(_PANEL, new_state)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def schedule_mgr(hass: HomeAssistant):
    # Use UTC so _ARM_DT / _DISARM_DT (UTC) equal the local wall-clock times that
    # async_track_time_change fires on (HA fires at local 22:00 / 06:00).
    await hass.config.async_set_time_zone("UTC")
    store = SchedulesStore(hass)
    mode_changer = _StateUpdatingModeChanger(hass)
    mgr = ScheduleManager(
        hass, store, HAClock(hass), HAScheduleClock(hass), mode_changer
    )
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["schedule_manager"] = mgr
    await mgr.async_setup()
    async_register_websocket_commands(hass)
    yield mgr
    await mgr.async_shutdown()


async def _advance(hass: HomeAssistant, dt: datetime) -> None:
    """Patch both dt_util.utcnow and time_tracker_utcnow, then fire time change."""
    with (
        patch.object(ha_event, "time_tracker_utcnow", return_value=dt),
        patch("homeassistant.util.dt.utcnow", return_value=dt),
    ):
        async_fire_time_changed(hass, dt, fire_all=True)
        await hass.async_block_till_done(wait_background_tasks=True)


def _capture(hass: HomeAssistant, event_name: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    async def _listener(ev: Any) -> None:
        events.append(ev.data)

    hass.bus.async_listen(event_name, _listener)
    return events


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestScheduleIntegration:
    async def test_arm_and_disarm_cycle(
        self, hass: HomeAssistant, schedule_mgr: ScheduleManager, hass_ws_client: Any
    ) -> None:
        """End-to-end: create schedule, arm fires, disarm fires, events correct."""
        hass.states.async_set(_PANEL, "disarmed")
        fired = _capture(hass, EVENT_SCHEDULE_FIRED)

        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/schedules/create",
                "name": "Integration Test",
                "weekdays": ["mon"],  # 2030-01-07 is a Monday
                "arm_time": "22:00",
                "disarm_time": "06:00",
            }
        )
        resp = await client.receive_json()
        assert resp["success"], resp
        pair_id = resp["result"]["id"]

        # Advance to arm time (22:00 UTC Mon Jan 7 2030).
        await _advance(hass, _ARM_DT)
        panel_state = hass.states.get(_PANEL)
        assert panel_state is not None
        assert panel_state.state == "armed_home"

        # Advance to disarm time (06:00 UTC Tue Jan 8 2030).
        await _advance(hass, _DISARM_DT)
        panel_state = hass.states.get(_PANEL)
        assert panel_state is not None
        assert panel_state.state == "disarmed"

        # Verify schedule_fired events.
        arm_events = [e for e in fired if e.get("action") == "arm"]
        disarm_events = [e for e in fired if e.get("action") == "disarm"]
        assert len(arm_events) == 1
        assert len(disarm_events) == 1
        assert arm_events[0]["schedule_id"] == pair_id
        assert disarm_events[0]["schedule_id"] == pair_id

    async def test_already_home_extends_pair(
        self, hass: HomeAssistant, schedule_mgr: ScheduleManager, hass_ws_client: Any
    ) -> None:
        """If panel already armed_home at arm time, pair takes ownership."""
        hass.states.async_set(_PANEL, "armed_home")
        skipped = _capture(hass, EVENT_SCHEDULE_SKIPPED)
        fired = _capture(hass, EVENT_SCHEDULE_FIRED)

        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/schedules/create",
                "weekdays": ["mon"],
                "arm_time": "22:00",
                "disarm_time": "06:00",
            }
        )
        resp = await client.receive_json()
        assert resp["success"], resp

        await _advance(hass, _ARM_DT)

        # No arm call (already_home), but schedule_skipped fired.
        assert any(e.get("reason") == "already_home" for e in skipped)

        # Disarm should still fire.
        await _advance(hass, _DISARM_DT)
        panel_state = hass.states.get(_PANEL)
        assert panel_state is not None
        assert panel_state.state == "disarmed"
        assert any(e.get("action") == "disarm" for e in fired)

    async def test_away_active_skips_both_arm_and_disarm(
        self, hass: HomeAssistant, schedule_mgr: ScheduleManager, hass_ws_client: Any
    ) -> None:
        """Panel armed_away at arm time → skip arm and disarm."""
        hass.states.async_set(_PANEL, "armed_away")
        skipped = _capture(hass, EVENT_SCHEDULE_SKIPPED)

        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/schedules/create",
                "weekdays": ["mon"],
                "arm_time": "22:00",
                "disarm_time": "06:00",
            }
        )
        resp = await client.receive_json()
        assert resp["success"], resp

        await _advance(hass, _ARM_DT)

        assert any(e.get("reason") == "away_active" for e in skipped)
        panel_state = hass.states.get(_PANEL)
        assert panel_state is not None
        assert panel_state.state == "armed_away"  # Panel unchanged

        # The arm never fired, so no one-shot disarm was ever registered.
        await _advance(hass, _DISARM_DT)
        panel_state = hass.states.get(_PANEL)
        assert panel_state is not None
        assert panel_state.state == "armed_away"
