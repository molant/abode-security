"""Integration tests for the SocketIO push path against the mock server.

Covers EventController's four push-event handlers end-to-end:

- ``com.goabode.device.update`` → entity refresh
- ``com.goabode.gateway.mode``  → alarm mode update
- ``com.goabode.gateway.timeline`` → HA bus event for the matched group
- ``com.goabode.automation``    → automation_edited group callback

Each test wires the real ``Client`` against the mock at
``mock_server_client["base_url"]``, lets the vendored SocketIO client connect,
then asks the mock to broadcast a frame via ``POST /api/test/emit``. The
test-emit hook is intentionally minimal: it only calls ``sio.emit`` and never
mutates the mock's REST-side state. Tests that need a changed device/automation
update the mock through its regular REST endpoints first, then emit the push.

The vendored client's connect handshake takes a few hundred ms; tests poll
``abode.events.connected`` before emitting. After emitting they poll for the
expected entity state (or bus event) rather than relying on a fixed sleep —
otherwise a slow CI runner trips the assertion before the
``_async_refresh_device_and_dispatch`` chain completes.

HTTP calls from inside the async tests go through ``aiohttp.ClientSession``
rather than ``requests``: ruff's ASYNC210 forbids blocking HTTP from async
code, and the integration suite already runs on aiohttp anyway.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

import aiohttp
import pytest
from homeassistant.components.alarm_control_panel import AlarmControlPanelState
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import Event, HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.abode_security import DOMAIN
from custom_components.abode_security.const import CONF_POLLING

from .test_constants import ALARM_ENTITY_ID, AUTOMATION_UID

FRONT_DOOR_DEVICE_ID = "RF:01430030"
FRONT_DOOR_ENTITY_ID = "binary_sensor.front_door"
EVENT_CONTROLLER_LOGGER = "custom_components.abode_security.abode.event_controller"

# The vendored client's connect handshake + session-cookie poll runs ~100-200ms
# on a healthy mock; cap it at 10s so a stuck mock fails fast instead of
# burning the integration job's wall clock.
CONNECT_TIMEOUT = 10.0
# After emitting a push, the SocketIO receive task + EventController dispatch
# usually completes inside one event-loop tick; 2s is a generous cap to absorb
# CI variance without masking a regression that breaks the path entirely.
DISPATCH_TIMEOUT = 2.0


@asynccontextmanager
async def _abode_integration_setup(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> AsyncIterator[MockConfigEntry]:
    """Set up the integration against the mock server with the env-var dance.

    Mirrors the pattern in test_alarm_control_panel.py / test_binary_sensor.py:
    set ``ABODE_BASE_URL``, reload the ``urls`` module so ``URL.BASE`` reflects
    the mock, then tear down via the config-entry unload path. The reload step
    matters because ``urls.BASE`` is evaluated at import time.
    """
    from custom_components.abode_security.abode.helpers import urls

    original_url = os.environ.get("ABODE_BASE_URL")
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]
    importlib.reload(urls)

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: mock_server_client["username"],
            CONF_PASSWORD: mock_server_client["password"],
            CONF_POLLING: False,
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    try:
        yield config_entry
    finally:
        await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


async def _wait_for_socketio_connected(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Block until the vendored SocketIO client reports connected.

    Without this, ``POST /api/test/emit`` would broadcast to zero subscribers
    on a slow CI runner and the assertion would race the handshake.
    """
    abode_system = config_entry.runtime_data
    deadline = asyncio.get_running_loop().time() + CONNECT_TIMEOUT
    while asyncio.get_running_loop().time() < deadline:
        if abode_system.abode.events.connected:
            return
        await asyncio.sleep(0.05)
        await hass.async_block_till_done()
    pytest.fail(f"SocketIO did not connect within {CONNECT_TIMEOUT}s")


async def _wait_for(
    hass: HomeAssistant,
    predicate: Callable[[], bool],
    *,
    deadline_seconds: float = DISPATCH_TIMEOUT,
    message: str = "predicate never became true",
) -> None:
    """Poll ``predicate`` until it returns True or the deadline elapses."""
    deadline = asyncio.get_running_loop().time() + deadline_seconds
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.05)
        await hass.async_block_till_done()
    pytest.fail(f"{message} (after {deadline_seconds}s)")


async def _emit(
    session: aiohttp.ClientSession, mock_url: str, event: str, data: Any
) -> None:
    """POST to the mock's /api/test/emit hook and raise on non-2xx."""
    async with session.post(
        f"{mock_url}/api/test/emit", json={"event": event, "data": data}
    ) as response:
        response.raise_for_status()


async def _put_device(
    session: aiohttp.ClientSession,
    mock_url: str,
    device_id: str,
    payload: dict[str, Any],
) -> None:
    """PUT a device update on the mock; ignore the com.goabode.states emit."""
    async with session.put(
        f"{mock_url}/api/v1/devices/{device_id}", json=payload
    ) as response:
        response.raise_for_status()


# ---------------------------------------------------------------------------
# com.goabode.device.update
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_device_update_push_refreshes_entity_state(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """A com.goabode.device.update push refreshes the entity from the API.

    Sequence:
      1. Integration setup → front_door starts STATE_OFF (status=Closed).
      2. Mutate the mock's device store (PUT) so the next devices fetch
         returns status=Open.
      3. POST /api/test/emit { event=device.update, data=<device id> }.
      4. EventController._on_device_update fetches devices, dispatches the
         per-device callback, which updates _attr_is_on → STATE_ON.
    """
    mock_url = mock_server_client["base_url"]
    async with (
        _abode_integration_setup(hass, mock_server_client) as config_entry,
        aiohttp.ClientSession() as session,
    ):
        await _wait_for_socketio_connected(hass, config_entry)

        initial = hass.states.get(FRONT_DOOR_ENTITY_ID)
        assert initial is not None
        assert initial.state == STATE_OFF

        await _put_device(session, mock_url, FRONT_DOOR_DEVICE_ID, {"status": "Open"})
        await _emit(
            session, mock_url, "com.goabode.device.update", FRONT_DOOR_DEVICE_ID
        )

        await _wait_for(
            hass,
            lambda: (
                (s := hass.states.get(FRONT_DOOR_ENTITY_ID)) is not None
                and s.state == STATE_ON
            ),
            message=f"{FRONT_DOOR_ENTITY_ID} never transitioned to STATE_ON",
        )


# ---------------------------------------------------------------------------
# com.goabode.gateway.mode
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_mode_change_push_updates_alarm_state(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """A com.goabode.gateway.mode push flips the alarm panel's state directly.

    Unlike device.update, this handler doesn't refresh from the API — it
    forces ``alarm_device._state["mode"]["area_1"] = mode`` and dispatches
    the alarm's device callback. So the mock doesn't need to be mutated first.
    """
    mock_url = mock_server_client["base_url"]
    async with (
        _abode_integration_setup(hass, mock_server_client) as config_entry,
        aiohttp.ClientSession() as session,
    ):
        await _wait_for_socketio_connected(hass, config_entry)

        initial = hass.states.get(ALARM_ENTITY_ID)
        assert initial is not None
        assert initial.state == AlarmControlPanelState.DISARMED

        await _emit(session, mock_url, "com.goabode.gateway.mode", "away")

        await _wait_for(
            hass,
            lambda: (
                (s := hass.states.get(ALARM_ENTITY_ID)) is not None
                and s.state == AlarmControlPanelState.ARMED_AWAY
            ),
            message=f"{ALARM_ENTITY_ID} never transitioned to ARMED_AWAY",
        )


# ---------------------------------------------------------------------------
# com.goabode.gateway.timeline
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_timeline_push_fires_ha_bus_event(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """A timeline push routes through map_event_code and fires the HA bus.

    ``setup_abode_events`` (in ``custom_components/abode_security/__init__.py``)
    registers ``event_callback`` for a hard-coded subset of ``timeline.Groups``
    — ALARM, ALARM_END, PANEL_FAULT, PANEL_RESTORE, AUTOMATION, DISARM, ARM,
    ARM_FAULT, TEST, CAPTURE, DEVICE — but notably *not* AUTOMATION_EDIT (see
    the automation test for that group). A timeline push with event_code=1200
    falls in the ALARM range (1199-1298 in the vendored RangeMap) and so
    fires the ``abode_alarm`` HA bus event the integration bridges.
    """
    mock_url = mock_server_client["base_url"]
    async with (
        _abode_integration_setup(hass, mock_server_client) as config_entry,
        aiohttp.ClientSession() as session,
    ):
        await _wait_for_socketio_connected(hass, config_entry)

        captured: list[Event] = []
        hass.bus.async_listen("abode_alarm", captured.append)

        await _emit(
            session,
            mock_url,
            "com.goabode.gateway.timeline",
            {
                "event_type": "Alarm",
                "event_code": "1200",
                "event_name": "Test alarm",
                "device_id": FRONT_DOOR_DEVICE_ID,
            },
        )

        await _wait_for(
            hass,
            lambda: len(captured) >= 1,
            message="abode_alarm bus event never fired",
        )
        assert captured[0].data["event_code"] == "1200"


# ---------------------------------------------------------------------------
# com.goabode.automation
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_automation_push_invokes_automation_edit_callbacks(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """A com.goabode.automation push dispatches AUTOMATION_EDIT callbacks.

    ``_on_automation_update`` fires callbacks registered against
    ``Groups.AUTOMATION_EDIT``. The integration's ``setup_abode_events`` does
    *not* register a handler for that group (only ALARM/ARM/DISARM/CAPTURE/…),
    so we register a callback directly on EventController and assert it
    received the event. This still proves the SocketIO → handler dispatch path
    works end-to-end.
    """
    from custom_components.abode_security.abode.helpers.timeline import Groups

    mock_url = mock_server_client["base_url"]
    async with (
        _abode_integration_setup(hass, mock_server_client) as config_entry,
        aiohttp.ClientSession() as session,
    ):
        await _wait_for_socketio_connected(hass, config_entry)

        captured: list[dict[str, Any]] = []

        def _capture(event: dict[str, Any]) -> None:
            captured.append(event)

        config_entry.runtime_data.abode.events.add_event_callback(
            Groups.AUTOMATION_EDIT, _capture
        )

        await _emit(
            session,
            mock_url,
            "com.goabode.automation",
            {
                "id": AUTOMATION_UID,
                "event_type": "Automation",
                "event_name": "Test automation edited",
            },
        )

        await _wait_for(
            hass,
            lambda: len(captured) >= 1,
            message="AUTOMATION_EDIT callback never fired",
        )
        assert captured[0]["id"] == AUTOMATION_UID


# ---------------------------------------------------------------------------
# Negative cases
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_device_update_push_for_unknown_device_logs_and_continues(
    hass: HomeAssistant,
    mock_server_client: dict[str, str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An unknown device id hits the debug branch and the loop survives.

    Asserts on the actual ``"Got device update for unknown device after
    refresh: ..."`` log line emitted by
    ``_async_refresh_device_and_dispatch`` — that's the deterministic signal
    that the handler ran, replacing a fixed-sleep heuristic. Then verifies a
    subsequent valid push is still dispatched (the SocketIO task isn't dead).
    """
    mock_url = mock_server_client["base_url"]
    async with (
        _abode_integration_setup(hass, mock_server_client) as config_entry,
        aiohttp.ClientSession() as session,
    ):
        await _wait_for_socketio_connected(hass, config_entry)

        unknown_id = "RF:does-not-exist"
        caplog.set_level(logging.DEBUG, logger=EVENT_CONTROLLER_LOGGER)
        await _emit(session, mock_url, "com.goabode.device.update", unknown_id)

        # Wait for the actual log line — the only deterministic signal that
        # _async_refresh_device_and_dispatch completed for the bogus id.
        await _wait_for(
            hass,
            lambda: any(
                rec.name == EVENT_CONTROLLER_LOGGER
                and f"Got device update for unknown device after refresh: {unknown_id}"
                in rec.message
                for rec in caplog.records
            ),
            message="event_controller never logged the unknown-device branch",
        )
        state = hass.states.get(FRONT_DOOR_ENTITY_ID)
        assert state is not None
        assert state.state == STATE_OFF

        # Recovery: a subsequent valid push must still work.
        await _put_device(session, mock_url, FRONT_DOOR_DEVICE_ID, {"status": "Open"})
        await _emit(
            session, mock_url, "com.goabode.device.update", FRONT_DOOR_DEVICE_ID
        )

        await _wait_for(
            hass,
            lambda: (
                (s := hass.states.get(FRONT_DOOR_ENTITY_ID)) is not None
                and s.state == STATE_ON
            ),
            message="SocketIO loop did not recover after unknown-device push",
        )


@pytest.mark.integration
async def test_malformed_timeline_payload_is_ignored(
    hass: HomeAssistant,
    mock_server_client: dict[str, str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A timeline payload missing event_type/event_code is dropped.

    Asserts on the actual ``"Invalid timeline update event: ..."`` warning
    from ``_on_timeline_update`` to confirm the handler ran and took the
    early-return branch — replacing a fixed-sleep heuristic. Then verifies a
    well-formed push still fires (loop survived).
    """
    mock_url = mock_server_client["base_url"]
    async with (
        _abode_integration_setup(hass, mock_server_client) as config_entry,
        aiohttp.ClientSession() as session,
    ):
        await _wait_for_socketio_connected(hass, config_entry)

        captured: list[Event] = []
        hass.bus.async_listen("abode_alarm", captured.append)

        # Missing event_type/event_code — the handler logs WARNING and returns.
        caplog.set_level(logging.WARNING, logger=EVENT_CONTROLLER_LOGGER)
        await _emit(
            session,
            mock_url,
            "com.goabode.gateway.timeline",
            {"this": "is", "not": "valid"},
        )
        await _wait_for(
            hass,
            lambda: any(
                rec.name == EVENT_CONTROLLER_LOGGER
                and "Invalid timeline update event" in rec.message
                for rec in caplog.records
            ),
            message="event_controller never logged the malformed timeline event",
        )
        assert captured == []

        # Recovery: a well-formed timeline push must still fire.
        await _emit(
            session,
            mock_url,
            "com.goabode.gateway.timeline",
            {
                "event_type": "Alarm",
                "event_code": "1200",
                "event_name": "Recovery alarm",
            },
        )
        await _wait_for(
            hass,
            lambda: len(captured) >= 1,
            message="bus event never fired after malformed payload recovery",
        )


@pytest.mark.integration
async def test_disconnect_mid_emit_does_not_lose_subsequent_events(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """SocketIO survives a disconnect+reconnect cycle and resumes dispatching.

    Triggers a real server-side disconnect via the mock's
    ``/api/test/disconnect_all`` hook, which calls ``sio.disconnect`` on every
    connected client (delivering a CLOSE frame on the underlying websocket).
    The vendored client treats that as a transient disconnect and reconnects
    after its backoff window; after reconnection a fresh device.update push
    must still reach the entity.

    Observes both halves of the transition (connected → disconnected →
    connected) so a regression that breaks reconnection cannot silently pass.
    The reconnect backoff starts at ~1s, hence the longer timeout.
    """
    mock_url = mock_server_client["base_url"]
    async with (
        _abode_integration_setup(hass, mock_server_client) as config_entry,
        aiohttp.ClientSession() as session,
    ):
        await _wait_for_socketio_connected(hass, config_entry)
        abode_system = config_entry.runtime_data

        # Force a real CLOSE frame on the active websocket.
        async with session.post(f"{mock_url}/api/test/disconnect_all") as resp:
            resp.raise_for_status()

        # Wait for the client to *observe* the disconnect — otherwise a
        # broken reconnect path could pass this test because `connected`
        # never flipped to False.
        await _wait_for(
            hass,
            lambda: not abode_system.abode.events.connected,
            message="SocketIO never observed the forced disconnect",
        )

        # Then wait for automatic reconnection.
        await _wait_for(
            hass,
            lambda: abode_system.abode.events.connected,
            deadline_seconds=CONNECT_TIMEOUT,
            message="SocketIO did not reconnect after forced disconnect",
        )

        # Now mutate + emit — the post-reconnect channel must work.
        await _put_device(session, mock_url, FRONT_DOOR_DEVICE_ID, {"status": "Open"})
        await _emit(
            session, mock_url, "com.goabode.device.update", FRONT_DOOR_DEVICE_ID
        )

        await _wait_for(
            hass,
            lambda: (
                (s := hass.states.get(FRONT_DOOR_ENTITY_ID)) is not None
                and s.state == STATE_ON
            ),
            message="device.update push lost after reconnect",
        )
