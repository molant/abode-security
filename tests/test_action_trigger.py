"""Tests for the ActionTriggerCoordinator module."""

from datetime import timedelta

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

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

        await manager.async_create(
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

        # Should not raise error
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

    async def test_coordinator_fires_event(self, hass) -> None:
        """Test coordinator fires HA event."""
        manager = _get_manager(hass)
        coordinator = ActionTriggerCoordinator(hass, manager)
        await coordinator.async_start()

        # Register mock service
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
        hass.states.async_set("binary_sensor.door", "off")
        await hass.async_block_till_done()

        hass.states.async_set("binary_sensor.door", "on")
        await hass.async_block_till_done()

        assert len(events) == 1
        assert events[0].data["action_id"] == action.id
        assert events[0].data["triggered_by"] == "binary_sensor.door"
        assert events[0].data["mode"] == "home"

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
