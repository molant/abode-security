"""Tests for the ActionTriggerCoordinator module."""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import Event, HomeAssistant, ServiceCall
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.abode_security.action_manager import ActionManager
from custom_components.abode_security.action_trigger import ActionTriggerCoordinator
from custom_components.abode_security.const import DOMAIN


async def async_fire_time_changed_and_wait(
    hass: HomeAssistant, delta: timedelta
) -> None:
    """Fire time changed event and wait for processing."""
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    future = dt_util.utcnow() + delta
    async_fire_time_changed(hass, future)
    await hass.async_block_till_done()


@pytest.fixture(autouse=True)
def seed_alarm_switches(hass):
    """Make the alarm switches these tests target actually exist.

    `_execute_action` refuses to report an alarm as raised when its entity is
    absent — Home Assistant logs and swallows `switch.turn_on` against a
    missing entity, so without this pre-check a stale entity_id was recorded
    as a successful arm. In a real install the switch always exists, so the
    tests have to model that rather than firing at a phantom entity.
    """
    for entity_id in ("switch.panic_alarm", "switch.medical_alarm"):
        hass.states.async_set(entity_id, "off")


@pytest.fixture
async def action_manager(hass):
    """Create an ActionManager for testing."""
    manager = ActionManager(hass)
    await manager.async_setup()
    return manager


@pytest.fixture
async def setup_coordinator(hass, action_manager):
    """Set up coordinator with required hass.data."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["action_manager"] = action_manager
    hass.data[DOMAIN]["config"] = {"debounce_seconds": 0.1}  # Short debounce for tests
    return action_manager


def _get_manager(hass):
    """Get ActionManager from hass.data."""
    return hass.data[DOMAIN]["action_manager"]


# --- Sub-Phase A: Coordinator Core ---


@pytest.mark.usefixtures("mock_abode", "setup_coordinator")
class TestCoordinatorCore:
    """Tests for coordinator initialization and basic operations."""

    async def test_coordinator_init(self, hass) -> None:
        """Test coordinator initialization."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        assert coordinator is not None

    async def test_coordinator_start_stop(self, hass) -> None:
        """Test coordinator start and stop."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()
        await coordinator.async_stop()
        # Should not raise

    async def test_coordinator_get_mode_standby(self, hass) -> None:
        """Test get current mode returns standby for disarmed."""
        hass.states.async_set("alarm_control_panel.abode_alarm", "disarmed")
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        mode = coordinator._get_current_mode()
        assert mode == "standby"

    async def test_coordinator_get_mode_home(self, hass) -> None:
        """Test get current mode returns home for armed_home."""
        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        mode = coordinator._get_current_mode()
        assert mode == "home"

    async def test_coordinator_get_mode_away(self, hass) -> None:
        """Test get current mode returns away for armed_away."""
        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_away")
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        mode = coordinator._get_current_mode()
        assert mode == "away"

    async def test_coordinator_get_mode_no_panel(self, hass) -> None:
        """Test get current mode returns None when no alarm panel."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        mode = coordinator._get_current_mode()
        assert mode is None


# --- Sub-Phase B: State Change Handling ---


@pytest.mark.usefixtures("mock_abode", "setup_coordinator")
class TestStateChangeHandling:
    """Tests for state change handling."""

    async def test_coordinator_ignores_non_binary_sensor(self, hass) -> None:
        """Test coordinator ignores non-binary_sensor entities."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        action = await manager.async_create(
            name="Test",
            modes=["home"],
            sensor_entity_ids=["switch.test"],  # Not a binary_sensor
            alarm_entity_ids=["switch.panic_alarm"],
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set("switch.test", "off")
        hass.states.async_set("switch.test", "on")
        await hass.async_block_till_done()

        updated = await manager.async_get(action.id)
        assert updated.trigger_count == 0

        await coordinator.async_stop()

    async def test_coordinator_ignores_off_state(self, hass) -> None:
        """Test coordinator ignores transitions to off state."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        action = await manager.async_create(
            name="Test",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set("binary_sensor.door", "on")
        await hass.async_block_till_done()

        # Transition to off
        hass.states.async_set("binary_sensor.door", "off")
        await hass.async_block_till_done()

        updated = await manager.async_get(action.id)
        assert updated is not None
        assert updated.trigger_count == 0

        await coordinator.async_stop()

    async def test_coordinator_matches_sensor_and_mode(self, hass) -> None:
        """Test coordinator matches sensor and mode correctly."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        # Register mock service
        calls = []

        async def mock_service(call):
            calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)

        action = await manager.async_create(
            name="Door Alert",
            modes=["away"],
            sensor_entity_ids=["binary_sensor.front_door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_away")
        hass.states.async_set("binary_sensor.front_door", "off")
        await hass.async_block_till_done()

        hass.states.async_set("binary_sensor.front_door", "on")
        await hass.async_block_till_done()

        updated = await manager.async_get(action.id)
        assert updated.trigger_count == 1

        await coordinator.async_stop()

    async def test_coordinator_no_match_wrong_mode(self, hass) -> None:
        """Test coordinator doesn't trigger for wrong mode."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        # Register mock service
        calls = []

        async def mock_service(call):
            calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)

        action = await manager.async_create(
            name="Away Only",
            modes=["away"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        # Set to HOME mode, not away
        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set("binary_sensor.door", "off")
        await hass.async_block_till_done()

        hass.states.async_set("binary_sensor.door", "on")
        await hass.async_block_till_done()

        updated = await manager.async_get(action.id)
        assert updated.trigger_count == 0

        await coordinator.async_stop()

    async def test_coordinator_no_match_wrong_sensor(self, hass) -> None:
        """Test coordinator doesn't trigger for wrong sensor."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        # Register mock service
        calls = []

        async def mock_service(call):
            calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)

        action = await manager.async_create(
            name="Motion Only",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.motion"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set("binary_sensor.door", "off")
        await hass.async_block_till_done()

        hass.states.async_set("binary_sensor.door", "on")
        await hass.async_block_till_done()

        updated = await manager.async_get(action.id)
        assert updated.trigger_count == 0

        await coordinator.async_stop()

    async def test_coordinator_debounce(self, hass) -> None:
        """Test debouncing prevents rapid triggers."""
        hass.data[DOMAIN]["config"]["debounce_seconds"] = 1.0

        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        # Register mock service
        calls = []

        async def mock_service(call):
            calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)

        action = await manager.async_create(
            name="Test",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")

        # Rapid triggers
        for _ in range(5):
            hass.states.async_set("binary_sensor.door", "off")
            await hass.async_block_till_done()
            hass.states.async_set("binary_sensor.door", "on")
            await hass.async_block_till_done()

        updated = await manager.async_get(action.id)
        assert updated.trigger_count == 1  # Only triggered once due to debounce

        await coordinator.async_stop()


# --- Sub-Phase C: Action Execution ---


@pytest.mark.usefixtures("mock_abode", "setup_coordinator")
class TestActionExecution:
    """Tests for action execution."""

    async def test_unavailable_alarm_is_never_reported_as_armed(self, hass) -> None:
        """An unavailable switch must be a failure, not a silent success.

        Home Assistant drops unavailable entities before dispatching an entity
        service call and only logs it (helpers/service.py filters
        `entity_candidates` on `e.available`). Abode entities mark themselves
        unavailable whenever the SocketIO stream is down — which happens on
        every ~30-minute session recreation — so without this check an action
        firing during a reconnect would report "Alarm raised." while no
        request ever left the process.
        """
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)

        hass.states.async_set("switch.panic_alarm", "unavailable")
        calls = []

        async def mock_service(call):
            calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)

        reason = await coordinator.async_arm_alarm("switch.panic_alarm", "Test")

        assert reason == "entity_unavailable"
        assert calls == [], "must not even attempt the service call"

    async def test_available_alarm_arms_cleanly(self, hass) -> None:
        """The happy path must stay clean — no false failures."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)

        hass.states.async_set("switch.panic_alarm", "off")

        async def mock_service(_call):
            hass.states.async_set("switch.panic_alarm", "on")

        hass.services.async_register("switch", "turn_on", mock_service)

        assert await coordinator.async_arm_alarm("switch.panic_alarm", "Test") is None

    async def test_missing_alarm_entity_is_reported(self, hass) -> None:
        """A stale entity_id must not count as a successful arm."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)

        reason = await coordinator.async_arm_alarm("switch.does_not_exist", "Test")
        assert reason == "entity_missing"

    async def test_non_switch_entity_is_reported(self, hass) -> None:
        """An existing entity outside the switch domain must not count as armed.

        `cv.entity_id` on the create/update schemas checks the format only, so
        a stored action can name `light.porch`. That entity exists and is
        available, so both other guards pass — but `switch.turn_on` matches no
        switch entity and returns without raising, which is the same silent
        no-op as a missing entity.
        """
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)

        hass.states.async_set("light.porch", "off")
        calls = []

        async def mock_service(call):
            calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)

        reason = await coordinator.async_arm_alarm("light.porch", "Test")

        assert reason == "entity_wrong_domain"
        assert calls == [], "must not even attempt the service call"

    async def test_disconnect_during_the_call_is_not_a_failure(self, hass) -> None:
        """An alarm that WAS dispatched must never be reported as failed.

        `AbodeManualAlarmSwitch.async_turn_on` blocks on an inline timeline
        lookup whose retry delays sum to 67 seconds, and it ends in
        `async_write_ha_state()`. If the SocketIO stream drops at any point in
        that window, HA's `_stringify_state` stamps the entity `unavailable` —
        for an alarm that was successfully raised. Any post-call state re-read
        would turn that into a critical "ALARM DID NOT FIRE" notification plus
        a repair issue. It is only safe to check availability *before* the
        call, so this must stay a success.
        """
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)

        hass.states.async_set("switch.panic_alarm", "off")

        async def mock_service(_call):
            # The alarm reached Abode, then the connection dropped mid-call.
            hass.states.async_set("switch.panic_alarm", "unavailable")

        hass.services.async_register("switch", "turn_on", mock_service)

        assert await coordinator.async_arm_alarm("switch.panic_alarm", "Test") is None

    async def test_coordinator_triggers_alarm_service(self, hass) -> None:
        """Test coordinator triggers alarm service."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        service_calls = []

        async def mock_service(call):
            service_calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)

        await manager.async_create(
            name="Test",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set("binary_sensor.door", "off")
        await hass.async_block_till_done()

        hass.states.async_set("binary_sensor.door", "on")
        await hass.async_block_till_done()

        assert len(service_calls) == 1
        assert service_calls[0].data["entity_id"] == "switch.panic_alarm"

        await coordinator.async_stop()

    async def test_notification_only_action_fires_event_without_alarm(
        self, hass
    ) -> None:
        """Action with empty alarm_entity_ids fires the event and skips switch.turn_on."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        switch_calls = []

        async def mock_service(call):
            switch_calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)

        events = []
        hass.bus.async_listen(
            "abode_security.action_triggered", lambda e: events.append(e)
        )

        action = await manager.async_create(
            name="Notify Only",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=[],
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set("binary_sensor.door", "off")
        await hass.async_block_till_done()

        hass.states.async_set("binary_sensor.door", "on")
        await hass.async_block_till_done()

        assert switch_calls == []
        assert len(events) == 1
        assert events[0].data["alarms_triggered"] == []
        assert events[0].data["alarms_failed"] == []
        assert events[0].data["action_name"] == "Notify Only"

        # trigger_count / last_triggered must still update — the value of a
        # notification-only action is that the rest of the trigger pipeline
        # runs identically. Guards against a future early-return refactor.
        refreshed = await manager.async_get(action.id)
        assert refreshed is not None
        assert refreshed.trigger_count == 1
        assert refreshed.last_triggered is not None

        await coordinator.async_stop()

    async def test_coordinator_fires_event(self, hass) -> None:
        """Test coordinator fires HA event and existing payload keys are unchanged."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        async def mock_service(call):
            pass

        hass.services.async_register("switch", "turn_on", mock_service)

        action = await manager.async_create(
            name="Test",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        events = []
        hass.bus.async_listen(
            "abode_security.action_triggered", lambda e: events.append(e)
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set(
            "binary_sensor.door",
            "off",
            {"friendly_name": "Front Door", "device_class": "door"},
        )
        await hass.async_block_till_done()

        hass.states.async_set(
            "binary_sensor.door",
            "on",
            {"friendly_name": "Front Door", "device_class": "door"},
        )
        await hass.async_block_till_done()

        assert len(events) == 1
        event_data = events[0].data

        # Verify original 7 keys are present with correct types — backwards-compat guardrail.
        existing_keys = (
            "action_id",
            "action_name",
            "triggered_by",
            "mode",
            "alarms_triggered",
            "alarms_failed",
            "timestamp",
        )
        expected_existing = {
            "action_id": action.id,
            "action_name": "Test",
            "triggered_by": "binary_sensor.door",
            "mode": "home",
            "alarms_triggered": ["switch.panic_alarm"],
            "alarms_failed": [],
            "timestamp": event_data["timestamp"],  # opaque string; type checked below
        }
        assert {k: event_data[k] for k in existing_keys} == expected_existing
        assert isinstance(event_data["action_id"], str)
        assert isinstance(event_data["action_name"], str)
        assert isinstance(event_data["triggered_by"], str)
        assert isinstance(event_data["mode"], str)
        assert isinstance(event_data["alarms_triggered"], list)
        assert isinstance(event_data["alarms_failed"], list)
        assert isinstance(event_data["timestamp"], str)

        # Sub-Phase B: also assert new context keys are present with correct values
        assert event_data["sensor_friendly_name"] == "Front Door"
        assert event_data["sensor_device_class"] == "door"
        assert event_data["previous_state"] == "off"
        assert event_data["new_state"] == "on"
        assert event_data["sensor_area_id"] is None
        assert event_data["sensor_area_name"] is None

        await coordinator.async_stop()

    async def test_trigger_context_threaded_through_delay(self, hass) -> None:
        """Context captured at trigger time survives a delay even if state mutates.

        Verifies that the coordinator captures sensor attributes (e.g. friendly_name)
        at the moment of the off→on transition and carries them intact through the
        delayed-execution closure so _execute_action receives trigger-time data.

        Sub-Phase A: verifies the action fires without error after state mutation mid-delay.
        Sub-Phase B extends this to assert event_data["sensor_friendly_name"] == "Front Door".
        """
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        service_calls = []

        async def mock_service(call):
            service_calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)

        await manager.async_create(
            name="Delayed",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
            delay_seconds=5,
        )

        events = []
        hass.bus.async_listen(
            "abode_security.action_triggered", lambda e: events.append(e)
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set(
            "binary_sensor.door",
            "off",
            {"friendly_name": "Front Door", "device_class": "door"},
        )
        await hass.async_block_till_done()

        # Trigger the off→on transition with friendly_name set
        hass.states.async_set(
            "binary_sensor.door",
            "on",
            {"friendly_name": "Front Door", "device_class": "door"},
        )
        await hass.async_block_till_done()
        assert len(coordinator._pending_delays) == 1

        # Mutate state mid-delay to remove the attribute
        hass.states.async_set("binary_sensor.door", "on", {})
        await hass.async_block_till_done()

        # Fire the delay timer
        await async_fire_time_changed_and_wait(hass, timedelta(seconds=6))

        # Trigger should have fired with trigger-time context preserved
        assert len(events) == 1
        # The friendly_name was removed from state mid-delay but the context captured
        # at trigger time still carries it (Sub-Phase B assertion).
        assert events[0].data["sensor_friendly_name"] == "Front Door"

        await coordinator.async_stop()

    async def test_trigger_context_built_for_sensor_without_area(self, hass) -> None:
        """No exception when sensor has no area_id and no device_id.

        Sub-Phase A: verifies no exception and the event fires (area_id=None path).
        Sub-Phase B: asserts sensor_area_id and sensor_area_name are None.
        """
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        async def mock_service(call):
            pass

        hass.services.async_register("switch", "turn_on", mock_service)

        events = []
        hass.bus.async_listen(
            "abode_security.action_triggered", lambda e: events.append(e)
        )

        await manager.async_create(
            name="No Area Test",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.bare_sensor"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        # Set sensor state without any area_id or device registration
        hass.states.async_set("binary_sensor.bare_sensor", "off", {})
        await hass.async_block_till_done()

        hass.states.async_set("binary_sensor.bare_sensor", "on", {})
        await hass.async_block_till_done()

        # No exception; event still fires
        assert len(events) == 1
        # Sub-Phase B: area fields are None for an unregistered sensor
        assert events[0].data["sensor_area_id"] is None
        assert events[0].data["sensor_area_name"] is None

        await coordinator.async_stop()

    async def test_coordinator_multiple_actions(self, hass) -> None:
        """Test coordinator triggers multiple actions for same sensor."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        service_calls = []

        async def mock_service(call):
            service_calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)

        action1 = await manager.async_create(
            name="Action 1",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        action2 = await manager.async_create(
            name="Action 2",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.medical_alarm"],
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set("binary_sensor.door", "off")
        await hass.async_block_till_done()

        hass.states.async_set("binary_sensor.door", "on")
        await hass.async_block_till_done()

        updated1 = await manager.async_get(action1.id)
        updated2 = await manager.async_get(action2.id)
        assert updated1.trigger_count == 1
        assert updated2.trigger_count == 1

        await coordinator.async_stop()

    async def test_coordinator_disabled_action_not_triggered(self, hass) -> None:
        """Test disabled actions are not triggered."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        service_calls = []

        async def mock_service(call):
            service_calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)

        action = await manager.async_create(
            name="Test",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        await manager.async_update(action.id, enabled=False)

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set("binary_sensor.door", "off")
        await hass.async_block_till_done()

        hass.states.async_set("binary_sensor.door", "on")
        await hass.async_block_till_done()

        updated = await manager.async_get(action.id)
        assert updated.trigger_count == 0

        await coordinator.async_stop()

    async def test_coordinator_delayed_action(self, hass) -> None:
        """Test delayed action execution."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        service_calls = []

        async def mock_service(call):
            service_calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)

        await manager.async_create(
            name="Delayed",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
            delay_seconds=5,  # Use larger delay to ensure test timing works
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set("binary_sensor.door", "off")

        hass.states.async_set("binary_sensor.door", "on")
        await hass.async_block_till_done()

        # Verify pending delay is registered
        assert len(coordinator._pending_delays) == 1

        # Fire time change to trigger the delay
        await async_fire_time_changed_and_wait(hass, timedelta(seconds=6))

        assert len(service_calls) == 1

        await coordinator.async_stop()

    async def test_coordinator_delayed_action_cancelled_on_delete(self, hass) -> None:
        """Test delayed action is cancelled when action is deleted."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        manager.set_trigger_coordinator(coordinator)
        await coordinator.async_start()

        service_calls = []

        async def mock_service(call):
            service_calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)

        action = await manager.async_create(
            name="Delayed",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
            delay_seconds=5,
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set("binary_sensor.door", "off")

        hass.states.async_set("binary_sensor.door", "on")
        await hass.async_block_till_done()

        # Verify pending delay is registered
        assert len(coordinator._pending_delays) == 1

        # Delete action before delay completes
        await manager.async_delete(action.id)

        # Verify pending delay was cancelled
        assert len(coordinator._pending_delays) == 0

        # Fire time change past the delay
        await async_fire_time_changed_and_wait(hass, timedelta(seconds=6))

        # Should NOT have triggered
        assert len(service_calls) == 0

        await coordinator.async_stop()

    async def test_coordinator_delayed_action_cancelled_on_disable(self, hass) -> None:
        """Test delayed action is cancelled when action is disabled."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        manager.set_trigger_coordinator(coordinator)
        await coordinator.async_start()

        service_calls = []

        async def mock_service(call):
            service_calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)

        action = await manager.async_create(
            name="Delayed",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
            delay_seconds=5,
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set("binary_sensor.door", "off")

        hass.states.async_set("binary_sensor.door", "on")
        await hass.async_block_till_done()

        # Verify pending delay is registered
        assert len(coordinator._pending_delays) == 1

        # Disable action before delay completes
        await manager.async_update(action.id, enabled=False)

        # Verify pending delay was cancelled
        assert len(coordinator._pending_delays) == 0

        # Fire time change past the delay
        await async_fire_time_changed_and_wait(hass, timedelta(seconds=6))

        # Should NOT have triggered
        assert len(service_calls) == 0

        await coordinator.async_stop()

    async def test_coordinator_multi_alarm_continues_on_failure(self, hass) -> None:
        """Test multi-alarm action continues after failure."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        service_calls = []
        call_count = 0

        async def mock_service(call):
            nonlocal call_count
            call_count += 1
            if call.data["entity_id"] == "switch.panic_alarm":
                raise Exception("Service failed")
            service_calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)

        await manager.async_create(
            name="Test",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm", "switch.medical_alarm"],
        )

        events = []
        hass.bus.async_listen(
            "abode_security.action_triggered", lambda e: events.append(e)
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set("binary_sensor.door", "off")
        await hass.async_block_till_done()

        hass.states.async_set("binary_sensor.door", "on")
        await hass.async_block_till_done()

        # Both were attempted
        assert call_count == 2
        # One succeeded
        assert len(service_calls) == 1
        # Event includes failure info
        assert len(events) == 1
        assert "switch.medical_alarm" in events[0].data["alarms_triggered"]
        assert "switch.panic_alarm" in events[0].data["alarms_failed"]

        await coordinator.async_stop()

    async def test_coordinator_cancel_pending_for_action(self, hass) -> None:
        """Test cancel_pending_for_action method."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        service_calls = []

        async def mock_service(call):
            service_calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)

        action = await manager.async_create(
            name="Delayed",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
            delay_seconds=5,
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set("binary_sensor.door", "off")

        hass.states.async_set("binary_sensor.door", "on")
        await hass.async_block_till_done()

        # Verify pending delay is registered
        assert len(coordinator._pending_delays) == 1

        # Manually cancel pending delays
        coordinator.cancel_pending_for_action(action.id)

        # Verify pending delay was cancelled
        assert len(coordinator._pending_delays) == 0

        # Fire time change past the delay
        await async_fire_time_changed_and_wait(hass, timedelta(seconds=6))

        # Should NOT have triggered
        assert len(service_calls) == 0

        await coordinator.async_stop()

    async def test_event_payload_null_when_attributes_missing(self, hass) -> None:
        """sensor_friendly_name and sensor_device_class are None when attrs absent."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        async def mock_service(_call):
            pass

        hass.services.async_register("switch", "turn_on", mock_service)

        events = []
        hass.bus.async_listen(
            "abode_security.action_triggered", lambda e: events.append(e)
        )

        await manager.async_create(
            name="No Attrs",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.bare"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set("binary_sensor.bare", "off", {})
        await hass.async_block_till_done()

        hass.states.async_set("binary_sensor.bare", "on", {})
        await hass.async_block_till_done()

        assert len(events) == 1
        event_data = events[0].data
        assert event_data["sensor_friendly_name"] is None
        assert event_data["sensor_device_class"] is None
        assert event_data["sensor_area_id"] is None
        assert event_data["sensor_area_name"] is None

        await coordinator.async_stop()

    async def test_event_payload_area_resolved_via_entity_registry(self, hass) -> None:
        """sensor_area_id/name are populated when the entity has a direct area."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        async def mock_service(_call):
            pass

        hass.services.async_register("switch", "turn_on", mock_service)

        events = []
        hass.bus.async_listen(
            "abode_security.action_triggered", lambda e: events.append(e)
        )

        # Create an area and register the entity in it
        area_reg = ar.async_get(hass)
        area = area_reg.async_create("Living Room")

        entity_reg = er.async_get(hass)
        entity_entry = entity_reg.async_get_or_create(
            "binary_sensor", "test_integration", "door_sensor"
        )
        entity_reg.async_update_entity(entity_entry.entity_id, area_id=area.id)

        await manager.async_create(
            name="Area Entity Test",
            modes=["home"],
            sensor_entity_ids=[entity_entry.entity_id],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set(entity_entry.entity_id, "off", {})
        await hass.async_block_till_done()

        hass.states.async_set(entity_entry.entity_id, "on", {})
        await hass.async_block_till_done()

        assert len(events) == 1
        event_data = events[0].data
        assert event_data["sensor_area_id"] == area.id
        assert event_data["sensor_area_name"] == "Living Room"

        await coordinator.async_stop()

    async def test_event_payload_area_resolved_via_device_fallback(self, hass) -> None:
        """sensor_area_id/name populate via device when entity has no direct area."""
        from pytest_homeassistant_custom_component.common import MockConfigEntry

        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        async def mock_service(_call):
            pass

        hass.services.async_register("switch", "turn_on", mock_service)

        events = []
        hass.bus.async_listen(
            "abode_security.action_triggered", lambda e: events.append(e)
        )

        # Create an area, a device in that area, and an entity under the device
        area_reg = ar.async_get(hass)
        area = area_reg.async_create("Garage")

        config_entry = MockConfigEntry(domain="test_fallback")
        config_entry.add_to_hass(hass)

        device_reg = dr.async_get(hass)
        device = device_reg.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            identifiers={("test_fallback", "device_1")},
        )
        device_reg.async_update_device(device.id, area_id=area.id)

        entity_reg = er.async_get(hass)
        entity_entry = entity_reg.async_get_or_create(
            "binary_sensor",
            "test_fallback",
            "garage_motion",
            device_id=device.id,
        )
        # Entity has no direct area_id (area_id defaults to None)

        await manager.async_create(
            name="Device Fallback Test",
            modes=["home"],
            sensor_entity_ids=[entity_entry.entity_id],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set(entity_entry.entity_id, "off", {})
        await hass.async_block_till_done()

        hass.states.async_set(entity_entry.entity_id, "on", {})
        await hass.async_block_till_done()

        assert len(events) == 1
        event_data = events[0].data
        assert event_data["sensor_area_id"] == area.id
        assert event_data["sensor_area_name"] == "Garage"

        await coordinator.async_stop()

    async def test_event_payload_preserves_existing_keys_exact_types(
        self, hass
    ) -> None:
        """Original 7 payload keys retain their exact pre-Phase-1 types."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        async def mock_service(_call):
            pass

        hass.services.async_register("switch", "turn_on", mock_service)

        action = await manager.async_create(
            name="Type Guard",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.sensor_types"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        events = []
        hass.bus.async_listen(
            "abode_security.action_triggered", lambda e: events.append(e)
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set("binary_sensor.sensor_types", "off")
        await hass.async_block_till_done()

        hass.states.async_set("binary_sensor.sensor_types", "on")
        await hass.async_block_till_done()

        assert len(events) == 1
        event_data = events[0].data

        assert isinstance(event_data["action_id"], str)
        assert isinstance(event_data["action_name"], str)
        assert isinstance(event_data["triggered_by"], str)
        assert isinstance(event_data["mode"], str)
        assert isinstance(event_data["alarms_triggered"], list)
        assert isinstance(event_data["alarms_failed"], list)
        assert isinstance(event_data["timestamp"], str)

        # Exact values to catch silent type changes
        assert event_data["action_id"] == action.id
        assert event_data["action_name"] == "Type Guard"
        assert event_data["triggered_by"] == "binary_sensor.sensor_types"
        assert event_data["mode"] == "home"
        assert event_data["alarms_triggered"] == ["switch.panic_alarm"]
        assert event_data["alarms_failed"] == []

        await coordinator.async_stop()


# --- Regression tests for state-transition correctness ---


@pytest.mark.usefixtures("mock_abode", "setup_coordinator")
class TestStateTransitionRegressions:
    """Regression tests for subtle state-transition bugs."""

    async def test_unavailable_to_on_does_not_trigger(self, hass) -> None:
        """An 'unavailable' -> 'on' transition (e.g. on HA restart) must not fire.

        Previously, any transition where old_state != 'on' and new_state == 'on'
        would trigger the action, so a currently-open sensor would fire the
        alarm on every HA restart.
        """
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        service_calls = []

        async def mock_service(call):
            service_calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)

        await manager.async_create(
            name="Door Alert",
            modes=["away"],
            sensor_entity_ids=["binary_sensor.front_door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        # Deliberately skip priming the sensor to "off" — this test simulates
        # the restart recovery path where the sensor is re-created as
        # "unavailable" and immediately becomes "on".
        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_away")
        hass.states.async_set("binary_sensor.front_door", "unavailable")
        await hass.async_block_till_done()

        hass.states.async_set("binary_sensor.front_door", "on")
        await hass.async_block_till_done()

        assert service_calls == []

        await coordinator.async_stop()

    async def test_unknown_to_on_does_not_trigger(self, hass) -> None:
        """'unknown' -> 'on' must also be ignored; only 'off' -> 'on' is real."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        service_calls = []

        async def mock_service(call):
            service_calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)

        await manager.async_create(
            name="Test",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.motion"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set("binary_sensor.motion", "unknown")
        await hass.async_block_till_done()
        hass.states.async_set("binary_sensor.motion", "on")
        await hass.async_block_till_done()

        assert service_calls == []

        await coordinator.async_stop()

    async def test_refire_during_pending_delay_fires_once(self, hass) -> None:
        """Re-firing a sensor during a pending delay must cancel the old timer.

        Without cancelling the prior unsub, both timers would fire and the
        action executed twice.
        """
        hass.data[DOMAIN]["config"]["debounce_seconds"] = 0.0

        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        service_calls = []

        async def mock_service(call):
            service_calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)

        await manager.async_create(
            name="Delayed",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
            delay_seconds=5,
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set("binary_sensor.door", "off")
        await hass.async_block_till_done()

        hass.states.async_set("binary_sensor.door", "on")
        await hass.async_block_till_done()

        hass.states.async_set("binary_sensor.door", "off")
        await hass.async_block_till_done()
        hass.states.async_set("binary_sensor.door", "on")
        await hass.async_block_till_done()

        await async_fire_time_changed_and_wait(hass, timedelta(seconds=6))

        # The discriminator: with the prior bug both timers survived and fired.
        assert len(service_calls) == 1

        await coordinator.async_stop()

    async def test_delayed_action_skipped_when_mode_changes_during_delay(
        self, hass
    ) -> None:
        """Disarming during a pending delay must suppress an away-only action.

        Reproduces #53: `_delayed_execute` re-checked existence + enabled but
        not the current alarm mode, so an away-only delayed action would still
        fire after the user disarmed during the delay window. The test uses a
        5s delay for speed; the real-world report involved a 60s delay.
        """
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        service_calls = []

        async def mock_service(call):
            service_calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)

        await manager.async_create(
            name="Away Only Delayed",
            modes=["away"],
            sensor_entity_ids=["binary_sensor.front_door"],
            alarm_entity_ids=["switch.panic_alarm"],
            delay_seconds=5,
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_away")
        hass.states.async_set("binary_sensor.front_door", "off")
        await hass.async_block_till_done()

        hass.states.async_set("binary_sensor.front_door", "on")
        await hass.async_block_till_done()

        assert len(coordinator._pending_delays) == 1

        # User disarms during the delay.
        hass.states.async_set("alarm_control_panel.abode_alarm", "disarmed")
        await hass.async_block_till_done()

        # Advance past the delay; the timer fires but mode no longer matches.
        await async_fire_time_changed_and_wait(hass, timedelta(seconds=6))

        assert service_calls == []

        await coordinator.async_stop()


@pytest.mark.usefixtures("mock_abode", "setup_coordinator")
class TestCloseTransitionNeverTriggers:
    """A sensor returning to its resting state must not fire an action.

    Issue #149's scenario: arm home on a hot summer night with a bedroom
    window open, then close that window hours later when it gets chilly.
    The close is an `on` -> `off` transition and has to be inert, while the
    *next* open is a genuine activation and still has to fire. The
    open-before-arming ordering matters — the sensor is already `on` when the
    mode changes, so nothing in the sequence looks like a fresh activation
    until the window is opened again.

    Scoped to the transition guard. A sensor that closes *during* an action's
    delay window is deliberately not covered: `_delayed_execute` re-checks the
    action and the mode but never re-reads the sensor, so that action still
    fires — an intruder closing the window behind them does not call the
    alarm off.
    """

    WINDOW = "binary_sensor.bedroom_window"
    ATTRS = {"friendly_name": "Bedroom Window", "device_class": "window"}

    @staticmethod
    def _listen(hass) -> tuple[list[ServiceCall], list[Event]]:
        """Record `switch.turn_on` calls and `action_triggered` events."""
        switch_calls: list[ServiceCall] = []
        events: list[Event] = []

        async def mock_service(call):
            switch_calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)
        hass.bus.async_listen(
            "abode_security.action_triggered", lambda e: events.append(e)
        )
        return switch_calls, events

    async def _arm_home_over_an_open_window(self, hass, manager):
        """Open the window, then arm home over it — the #149 starting state."""
        # Sensor state first, so `async_create` resolves a real entity the way
        # it would in an install where the user picks the sensor from a list.
        hass.states.async_set(self.WINDOW, "on", self.ATTRS)
        await hass.async_block_till_done()

        action = await manager.async_create(
            name="Bedroom Window",
            modes=["home"],
            sensor_entity_ids=[self.WINDOW],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        await hass.async_block_till_done()
        return action

    async def test_close_of_window_open_since_arming_does_not_trigger(
        self, hass
    ) -> None:
        """Closing a window that was already open at arming fires nothing."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        switch_calls, events = self._listen(hass)
        action = await self._arm_home_over_an_open_window(hass, manager)

        # Middle of the night: the window is closed.
        hass.states.async_set(self.WINDOW, "off", self.ATTRS)
        await hass.async_block_till_done()

        assert switch_calls == []
        assert events == []
        updated = await manager.async_get(action.id)
        assert updated is not None
        assert updated.trigger_count == 0
        assert updated.last_triggered is None

        await coordinator.async_stop()

    async def test_reopening_after_a_close_still_triggers(self, hass) -> None:
        """The close arms nothing, but re-opening the window still fires."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        switch_calls, events = self._listen(hass)
        action = await self._arm_home_over_an_open_window(hass, manager)

        hass.states.async_set(self.WINDOW, "off", self.ATTRS)
        await hass.async_block_till_done()
        assert events == []

        # Same night, later: the window is opened again. That *is* an
        # activation — the close must not have left the sensor latched shut.
        hass.states.async_set(self.WINDOW, "on", self.ATTRS)
        await hass.async_block_till_done()

        assert len(switch_calls) == 1
        assert switch_calls[0].data["entity_id"] == "switch.panic_alarm"
        assert len(events) == 1
        assert events[0].data["triggered_by"] == self.WINDOW
        assert events[0].data["previous_state"] == "off"
        assert events[0].data["new_state"] == "on"

        updated = await manager.async_get(action.id)
        assert updated is not None
        assert updated.trigger_count == 1

        await coordinator.async_stop()

    async def test_open_close_reopen_fires_once_per_open(self, hass) -> None:
        """Across a full cycle, only the two opens count as activations."""
        # The fixture's 0.1s debounce is there to swallow sensor chatter; a
        # real open/close/re-open cycle is minutes apart, so take it out of
        # the picture rather than have it decide this assertion.
        hass.data[DOMAIN]["config"]["debounce_seconds"] = 0

        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        switch_calls, events = self._listen(hass)

        hass.states.async_set(self.WINDOW, "off", self.ATTRS)
        await hass.async_block_till_done()

        action = await manager.async_create(
            name="Bedroom Window",
            modes=["home"],
            sensor_entity_ids=[self.WINDOW],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        await hass.async_block_till_done()

        hass.states.async_set(self.WINDOW, "on", self.ATTRS)
        await hass.async_block_till_done()
        assert len(events) == 1

        hass.states.async_set(self.WINDOW, "off", self.ATTRS)
        await hass.async_block_till_done()
        assert len(events) == 1

        hass.states.async_set(self.WINDOW, "on", self.ATTRS)
        await hass.async_block_till_done()
        assert len(events) == 2

        assert len(switch_calls) == 2
        updated = await manager.async_get(action.id)
        assert updated is not None
        assert updated.trigger_count == 2

        await coordinator.async_stop()


# --- Sub-Phase B: Snapshot integration ---


def _setup_sensor_with_camera(
    hass: HomeAssistant,
) -> tuple[str, str]:
    """Register a binary_sensor and camera on the same device.

    Returns (sensor_entity_id, camera_entity_id).
    Intended for one call per test — identifiers are fixed; relies on a fresh hass fixture per test.
    """
    config_entry = MockConfigEntry(domain="test_snap")
    config_entry.add_to_hass(hass)

    device_reg = dr.async_get(hass)
    device = device_reg.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={("test_snap", "snap_dev")},
    )

    entity_reg = er.async_get(hass)
    sensor_entry = entity_reg.async_get_or_create(
        "binary_sensor", "test_snap", "door_sensor", device_id=device.id
    )
    camera_entry = entity_reg.async_get_or_create(
        "camera", "test_snap", "door_cam", device_id=device.id
    )
    return sensor_entry.entity_id, camera_entry.entity_id


@pytest.mark.usefixtures("mock_abode", "setup_coordinator")
class TestSnapshotIntegration:
    """Tests for snapshot capture wired into _execute_action (Sub-Phase B)."""

    async def test_event_payload_includes_snapshot_in_home_mode(
        self, hass: HomeAssistant
    ) -> None:
        """Snapshot is captured and snapshot_path is populated when mode is home."""
        sensor_entity_id, camera_entity_id = _setup_sensor_with_camera(hass)

        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        async def mock_switch(_call):
            pass

        hass.services.async_register("switch", "turn_on", mock_switch)

        events = []
        hass.bus.async_listen(
            "abode_security.action_triggered", lambda e: events.append(e)
        )

        await manager.async_create(
            name="Snap Home",
            modes=["home"],
            sensor_entity_ids=[sensor_entity_id],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set(sensor_entity_id, "off")
        await hass.async_block_till_done()

        with patch(
            "custom_components.abode_security.action_trigger.snapshot.async_capture",
            new=AsyncMock(return_value=None),
        ):
            hass.states.async_set(sensor_entity_id, "on")
            await hass.async_block_till_done()

        assert len(events) == 1
        event_data = events[0].data
        assert event_data["camera_entity_id"] == camera_entity_id
        assert event_data["snapshot_path"] is not None
        assert event_data["snapshot_path"].startswith(
            "/local/abode_security_snapshots/"
        )
        assert event_data["snapshot_error"] is None

        await coordinator.async_stop()

    async def test_event_payload_includes_snapshot_in_away_mode(
        self, hass: HomeAssistant
    ) -> None:
        """Snapshot is captured and snapshot_path is populated when mode is away."""
        sensor_entity_id, camera_entity_id = _setup_sensor_with_camera(hass)

        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        async def mock_switch(_call):
            pass

        hass.services.async_register("switch", "turn_on", mock_switch)

        events = []
        hass.bus.async_listen(
            "abode_security.action_triggered", lambda e: events.append(e)
        )

        await manager.async_create(
            name="Snap Away",
            modes=["away"],
            sensor_entity_ids=[sensor_entity_id],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_away")
        hass.states.async_set(sensor_entity_id, "off")
        await hass.async_block_till_done()

        with patch(
            "custom_components.abode_security.action_trigger.snapshot.async_capture",
            new=AsyncMock(return_value=None),
        ):
            hass.states.async_set(sensor_entity_id, "on")
            await hass.async_block_till_done()

        assert len(events) == 1
        event_data = events[0].data
        assert event_data["camera_entity_id"] == camera_entity_id
        assert event_data["snapshot_path"] is not None
        assert event_data["snapshot_error"] is None

        await coordinator.async_stop()

    async def test_event_payload_no_snapshot_in_standby_mode(
        self, hass: HomeAssistant
    ) -> None:
        """In standby, camera_entity_id is populated but no snapshot is taken."""
        sensor_entity_id, camera_entity_id = _setup_sensor_with_camera(hass)

        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        async def mock_switch(_call):
            pass

        hass.services.async_register("switch", "turn_on", mock_switch)

        events = []
        hass.bus.async_listen(
            "abode_security.action_triggered", lambda e: events.append(e)
        )

        await manager.async_create(
            name="Snap Standby",
            modes=["standby"],
            sensor_entity_ids=[sensor_entity_id],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "disarmed")
        hass.states.async_set(sensor_entity_id, "off")
        await hass.async_block_till_done()

        mock_capture = AsyncMock(return_value=None)
        with patch(
            "custom_components.abode_security.action_trigger.snapshot.async_capture",
            new=mock_capture,
        ):
            hass.states.async_set(sensor_entity_id, "on")
            await hass.async_block_till_done()

        assert len(events) == 1
        event_data = events[0].data
        assert event_data["camera_entity_id"] == camera_entity_id
        assert event_data["snapshot_path"] is None
        assert event_data["snapshot_error"] is None
        mock_capture.assert_not_called()

        await coordinator.async_stop()

    async def test_event_payload_camera_entity_null_when_no_co_located_camera(
        self, hass: HomeAssistant
    ) -> None:
        """All three snapshot keys are None when the sensor has no co-located camera."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        async def mock_switch(_call):
            pass

        hass.services.async_register("switch", "turn_on", mock_switch)

        events = []
        hass.bus.async_listen(
            "abode_security.action_triggered", lambda e: events.append(e)
        )

        # Sensor not in registry at all (no device, no co-located camera)
        await manager.async_create(
            name="No Camera",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.standalone"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        mock_capture = AsyncMock(return_value=None)
        with patch(
            "custom_components.abode_security.action_trigger.snapshot.async_capture",
            new=mock_capture,
        ):
            hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
            hass.states.async_set("binary_sensor.standalone", "off")
            await hass.async_block_till_done()

            hass.states.async_set("binary_sensor.standalone", "on")
            await hass.async_block_till_done()

        assert len(events) == 1
        event_data = events[0].data
        assert event_data["camera_entity_id"] is None
        assert event_data["snapshot_path"] is None
        assert event_data["snapshot_error"] is None
        mock_capture.assert_not_called()

        await coordinator.async_stop()

    async def test_event_payload_snapshot_error_on_timeout(
        self, hass: HomeAssistant
    ) -> None:
        """When async_capture returns an error, snapshot_path is None and event still fires."""
        sensor_entity_id, _camera_entity_id = _setup_sensor_with_camera(hass)

        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        service_calls = []

        async def mock_switch(call):
            service_calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_switch)

        events = []
        hass.bus.async_listen(
            "abode_security.action_triggered", lambda e: events.append(e)
        )

        await manager.async_create(
            name="Timeout Snap",
            modes=["home"],
            sensor_entity_ids=[sensor_entity_id],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set(sensor_entity_id, "off")
        await hass.async_block_till_done()

        with patch(
            "custom_components.abode_security.action_trigger.snapshot.async_capture",
            new=AsyncMock(return_value="timeout"),
        ):
            hass.states.async_set(sensor_entity_id, "on")
            await hass.async_block_till_done()

        assert len(events) == 1
        event_data = events[0].data
        assert event_data["snapshot_path"] is None
        assert event_data["snapshot_error"] == "timeout"
        # Alarms were still triggered despite snapshot failure
        assert event_data["alarms_triggered"] == ["switch.panic_alarm"]
        assert len(service_calls) == 1

        await coordinator.async_stop()

    async def test_snapshot_does_not_block_alarms(self, hass: HomeAssistant) -> None:
        """Event fires and alarms are recorded even when async_capture yields.

        The structural non-blocking guarantee (alarms before snapshot) comes from
        the sequential ordering in _execute_action, not from this test. This test
        verifies the event is eventually fired and alarms_triggered is populated
        when async_capture does a cooperative yield before returning.
        """
        sensor_entity_id, _camera_entity_id = _setup_sensor_with_camera(hass)

        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        service_calls = []

        async def mock_switch(call):
            service_calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_switch)

        events = []
        hass.bus.async_listen(
            "abode_security.action_triggered", lambda e: events.append(e)
        )

        await manager.async_create(
            name="Slow Snap",
            modes=["home"],
            sensor_entity_ids=[sensor_entity_id],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
        hass.states.async_set(sensor_entity_id, "off")
        await hass.async_block_till_done()

        async def slow_capture(_hass: object, **_kwargs: object) -> str | None:
            await asyncio.sleep(0)
            return None

        with patch(
            "custom_components.abode_security.action_trigger.snapshot.async_capture",
            new=slow_capture,
        ):
            hass.states.async_set(sensor_entity_id, "on")
            await hass.async_block_till_done()

        assert len(events) == 1
        assert events[0].data["alarms_triggered"] == ["switch.panic_alarm"]
        assert len(service_calls) == 1

        await coordinator.async_stop()


@pytest.mark.usefixtures("mock_abode", "setup_coordinator")
class TestFireTestNotification:
    """Tests for async_fire_test_notification (debug-only path)."""

    async def test_fires_event_with_snapshot_and_no_alarm_calls(
        self, hass: HomeAssistant
    ) -> None:
        """Forces snapshot, skips switch.turn_on, fills the synthesized context."""
        sensor_entity_id, camera_entity_id = _setup_sensor_with_camera(hass)

        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        switch_calls: list[object] = []

        async def mock_switch(call):
            switch_calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_switch)

        events = []
        hass.bus.async_listen(
            "abode_security.action_triggered", lambda e: events.append(e)
        )

        action = await manager.async_create(
            name="Test Notif",
            modes=["home"],
            sensor_entity_ids=[sensor_entity_id],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        # Sensor must have a state so the synthesized context picks up
        # friendly_name + new_state — exercises the same payload path the
        # blueprint depends on.
        hass.states.async_set(
            sensor_entity_id,
            "off",
            {"friendly_name": "Front Door", "device_class": "door"},
        )
        await hass.async_block_till_done()

        with patch(
            "custom_components.abode_security.action_trigger.snapshot.async_capture",
            new=AsyncMock(return_value=None),
        ):
            fired = await coordinator.async_fire_test_notification(
                action.id, sensor_entity_id
            )
            await hass.async_block_till_done()

        assert fired is True
        # No alarm switch should have been touched.
        assert switch_calls == []
        assert len(events) == 1
        data = events[0].data
        assert data["action_id"] == action.id
        assert data["action_name"] == "Test Notif"
        assert data["mode"] == "home"
        assert data["alarms_triggered"] == []
        assert data["alarms_failed"] == []
        assert data["sensor_friendly_name"] == "Front Door"
        assert data["sensor_device_class"] == "door"
        assert data["camera_entity_id"] == camera_entity_id
        assert data["snapshot_path"] is not None
        assert data["snapshot_error"] is None

        await coordinator.async_stop()

    async def test_forces_snapshot_in_standby(self, hass: HomeAssistant) -> None:
        """Snapshot is captured even in standby — that's the point of the debug path."""
        sensor_entity_id, camera_entity_id = _setup_sensor_with_camera(hass)

        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        events = []
        hass.bus.async_listen(
            "abode_security.action_triggered", lambda e: events.append(e)
        )

        action = await manager.async_create(
            name="Standby Test",
            modes=["standby"],
            sensor_entity_ids=[sensor_entity_id],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        hass.states.async_set(sensor_entity_id, "off")
        await hass.async_block_till_done()

        with patch(
            "custom_components.abode_security.action_trigger.snapshot.async_capture",
            new=AsyncMock(return_value=None),
        ):
            fired = await coordinator.async_fire_test_notification(
                action.id, sensor_entity_id, mode="standby"
            )
            await hass.async_block_till_done()

        assert fired is True
        assert len(events) == 1
        data = events[0].data
        assert data["mode"] == "standby"
        assert data["camera_entity_id"] == camera_entity_id
        assert data["snapshot_path"] is not None

        await coordinator.async_stop()

    async def test_returns_false_for_unknown_action(self, hass: HomeAssistant) -> None:
        sensor_entity_id, _ = _setup_sensor_with_camera(hass)

        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        events = []
        hass.bus.async_listen(
            "abode_security.action_triggered", lambda e: events.append(e)
        )

        fired = await coordinator.async_fire_test_notification(
            "no-such-action-id", sensor_entity_id
        )
        await hass.async_block_till_done()

        assert fired is False
        assert events == []

        await coordinator.async_stop()

    async def test_rejects_invalid_mode(self, hass: HomeAssistant) -> None:
        sensor_entity_id, _ = _setup_sensor_with_camera(hass)

        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        action = await manager.async_create(
            name="Bad Mode",
            modes=["home"],
            sensor_entity_ids=[sensor_entity_id],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        events = []
        hass.bus.async_listen(
            "abode_security.action_triggered", lambda e: events.append(e)
        )

        fired = await coordinator.async_fire_test_notification(
            action.id, sensor_entity_id, mode="bogus"
        )
        await hass.async_block_till_done()

        assert fired is False
        assert events == []

        await coordinator.async_stop()
