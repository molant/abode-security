"""Tests for scheduling/mode_changer.py."""

from __future__ import annotations

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.abode_security.const import CONTEXT_ID_PREFIX, DOMAIN
from custom_components.abode_security.scheduling.mode_changer import (
    HAModeChanger,
    ModeChangeFailed,
)
from custom_components.abode_security.scheduling.models import ChangeSource


@pytest.fixture
def mode_changer(hass):
    return HAModeChanger(hass)


@pytest.mark.usefixtures("mock_abode")
class TestHAModeChanger:
    async def test_set_mode_home_calls_alarm_arm_home(self, hass, mode_changer) -> None:
        """async_set_mode("home", USER_WS) calls alarm_control_panel.alarm_arm_home."""
        hass.states.async_set("alarm_control_panel.abode_alarm", "disarmed")
        calls = []

        async def mock_service(call):
            calls.append(call)

        hass.services.async_register(
            "alarm_control_panel", "alarm_arm_home", mock_service
        )

        await mode_changer.async_set_mode("home", ChangeSource.USER_WS)

        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "alarm_control_panel.abode_alarm"

    async def test_set_mode_user_ws_context_is_not_schedule_prefixed(
        self, hass, mode_changer
    ) -> None:
        """USER_WS source: context.id does not start with CONTEXT_ID_PREFIX."""
        hass.states.async_set("alarm_control_panel.abode_alarm", "disarmed")
        calls = []

        async def mock_service(call):
            calls.append(call)

        hass.services.async_register(
            "alarm_control_panel", "alarm_arm_home", mock_service
        )

        await mode_changer.async_set_mode("home", ChangeSource.USER_WS)

        assert len(calls) == 1
        # context is None (default) for USER_WS — HA creates a fresh Context
        assert not calls[0].context.id.startswith(CONTEXT_ID_PREFIX)

    async def test_set_mode_schedule_arm_stamps_context_id(
        self, hass, mode_changer
    ) -> None:
        """SCHEDULE_ARM source: context.id starts with CONTEXT_ID_PREFIX + pair_id."""
        hass.states.async_set("alarm_control_panel.abode_alarm", "disarmed")
        calls = []

        async def mock_service(call):
            calls.append(call)

        hass.services.async_register(
            "alarm_control_panel", "alarm_arm_home", mock_service
        )

        pair_id = "abc-123"
        await mode_changer.async_set_mode(
            "home", ChangeSource.SCHEDULE_ARM, pair_id=pair_id
        )

        assert len(calls) == 1
        assert calls[0].context.id.startswith(f"{CONTEXT_ID_PREFIX}{pair_id}_")

    async def test_set_mode_schedule_arm_without_pair_id_raises_value_error(
        self, hass, mode_changer
    ) -> None:
        """SCHEDULE_ARM without pair_id raises ValueError.

        Panel must exist so that execution reaches _build_context (the pair_id
        check lives there, after the panel lookup).
        """
        hass.states.async_set("alarm_control_panel.abode_alarm", "disarmed")

        with pytest.raises(ValueError, match="pair_id required"):
            await mode_changer.async_set_mode("home", ChangeSource.SCHEDULE_ARM)

    async def test_set_mode_invalid_target_raises_value_error(
        self, mode_changer
    ) -> None:
        """Invalid mode target raises ValueError."""

        with pytest.raises(ValueError, match="Invalid mode"):
            await mode_changer.async_set_mode("invalid", ChangeSource.USER_WS)

    async def test_set_mode_no_panel_raises_mode_change_failed(
        self, mode_changer
    ) -> None:
        """No alarm_control_panel entity → ModeChangeFailed."""
        # No panel state set.
        with pytest.raises(ModeChangeFailed, match="No Abode alarm_control_panel"):
            await mode_changer.async_set_mode("home", ChangeSource.USER_WS)

    async def test_set_mode_service_error_raises_mode_change_failed(
        self, hass, mode_changer
    ) -> None:
        """hass.services.async_call raising HomeAssistantError → ModeChangeFailed."""
        hass.states.async_set("alarm_control_panel.abode_alarm", "disarmed")

        async def failing_service(_call):
            raise HomeAssistantError("Abode SDK error")

        hass.services.async_register(
            "alarm_control_panel", "alarm_arm_home", failing_service
        )

        with pytest.raises(ModeChangeFailed):
            await mode_changer.async_set_mode("home", ChangeSource.USER_WS)

    async def test_set_mode_standby_calls_alarm_disarm(
        self, hass, mode_changer
    ) -> None:
        """async_set_mode("standby", USER_WS) calls alarm_disarm."""
        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        calls = []

        async def mock_service(call):
            calls.append(call)

        hass.services.async_register(
            "alarm_control_panel", "alarm_disarm", mock_service
        )

        await mode_changer.async_set_mode("standby", ChangeSource.USER_WS)

        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "alarm_control_panel.abode_alarm"

    async def test_set_mode_schedule_disarm_stamps_context_id(
        self, hass, mode_changer
    ) -> None:
        """SCHEDULE_DISARM source: context.id starts with CONTEXT_ID_PREFIX + pair_id."""
        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        calls = []

        async def mock_service(call):
            calls.append(call)

        hass.services.async_register(
            "alarm_control_panel", "alarm_disarm", mock_service
        )

        pair_id = "pair-xyz-789"
        await mode_changer.async_set_mode(
            "standby", ChangeSource.SCHEDULE_DISARM, pair_id=pair_id
        )

        assert len(calls) == 1
        assert calls[0].context.id.startswith(f"{CONTEXT_ID_PREFIX}{pair_id}_")

    async def test_set_mode_reconcile_disarm_stamps_context_id(
        self, hass, mode_changer
    ) -> None:
        """RECONCILE_DISARM source: context.id starts with CONTEXT_ID_PREFIX + pair_id."""
        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        calls = []

        async def mock_service(call):
            calls.append(call)

        hass.services.async_register(
            "alarm_control_panel", "alarm_disarm", mock_service
        )

        pair_id = "reconcile-pair-001"
        await mode_changer.async_set_mode(
            "standby", ChangeSource.RECONCILE_DISARM, pair_id=pair_id
        )

        assert len(calls) == 1
        assert calls[0].context.id.startswith(f"{CONTEXT_ID_PREFIX}{pair_id}_")

    async def test_set_mode_resolves_renamed_panel_via_registry(
        self, hass, mode_changer
    ) -> None:
        """Renamed alarm panel (non-prefix entity_id) still resolves via entity registry."""
        registry = er.async_get(hass)
        registry.async_get_or_create(
            domain="alarm_control_panel",
            platform=DOMAIN,
            unique_id="abode-test-uid",
            suggested_object_id="house",
        )
        hass.states.async_set("alarm_control_panel.house", "disarmed")
        calls = []

        async def mock_service(call):
            calls.append(call)

        hass.services.async_register(
            "alarm_control_panel", "alarm_arm_home", mock_service
        )

        await mode_changer.async_set_mode("home", ChangeSource.USER_WS)

        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "alarm_control_panel.house"
