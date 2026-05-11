"""Integration tests for Actions functionality.

These tests verify the full action system including:
- WebSocket API through actual HA WebSocket client
- ActionTriggerCoordinator with real state changes
- End-to-end action trigger flow

These tests require the mock Abode server to be running.
"""

import pytest
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from custom_components.abode_security.action_manager import ActionManager
from custom_components.abode_security.action_trigger import ActionTriggerCoordinator
from custom_components.abode_security.config_store import ConfigStore
from custom_components.abode_security.const import DOMAIN
from custom_components.abode_security.websocket_api import (
    async_register_websocket_commands,
)


@pytest.fixture
async def integration_action_manager(hass: HomeAssistant):
    """Create an ActionManager for integration testing."""
    manager = ActionManager(hass)
    await manager.async_setup()
    return manager


@pytest.fixture
async def integration_config_store(hass: HomeAssistant):
    """Create a ConfigStore for integration testing."""
    store = ConfigStore(hass)
    await store.async_load()
    return store


@pytest.fixture
async def integration_setup(
    hass: HomeAssistant,
    integration_action_manager: ActionManager,
    integration_config_store: ConfigStore,
):
    """Set up the full integration environment for testing."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["action_manager"] = integration_action_manager
    hass.data[DOMAIN]["config_store"] = integration_config_store
    hass.data[DOMAIN]["config"] = integration_config_store.get_config()

    # Register WebSocket commands
    async_register_websocket_commands(hass)

    # Create and start the coordinator
    coordinator = ActionTriggerCoordinator(hass, integration_action_manager)
    await coordinator.async_start()
    hass.data[DOMAIN]["action_trigger"] = coordinator

    yield {
        "action_manager": integration_action_manager,
        "config_store": integration_config_store,
        "coordinator": coordinator,
    }

    # Cleanup
    await coordinator.async_stop()


@pytest.mark.integration
class TestActionsIntegration:
    """Integration tests for the actions system."""

    async def test_full_action_crud_flow(
        self,
        hass: HomeAssistant,
        hass_ws_client,
        integration_setup,  # noqa: ARG002
    ) -> None:
        """Test complete CRUD flow through WebSocket API."""
        client = await hass_ws_client(hass)

        # 1. List actions (should be empty)
        await client.send_json({"id": 1, "type": "abode_security/actions/list"})
        response = await client.receive_json()
        assert response["success"]
        assert response["result"]["actions"] == []

        # 2. Create an action
        await client.send_json(
            {
                "id": 2,
                "type": "abode_security/actions/create",
                "name": "Integration Test Action",
                "modes": ["home", "away"],
                "sensor_entity_ids": ["binary_sensor.front_door"],
                "alarm_entity_ids": ["switch.abode_panic_alarm"],
                "delay_seconds": 5,
            }
        )
        response = await client.receive_json()
        assert response["success"]
        action = response["result"]
        assert action["name"] == "Integration Test Action"
        assert action["modes"] == ["home", "away"]
        assert action["enabled"] is True
        action_id = action["id"]

        # 3. Get the action
        await client.send_json(
            {
                "id": 3,
                "type": "abode_security/actions/get",
                "action_id": action_id,
            }
        )
        response = await client.receive_json()
        assert response["success"]
        assert response["result"]["name"] == "Integration Test Action"

        # 4. Update the action
        await client.send_json(
            {
                "id": 4,
                "type": "abode_security/actions/update",
                "action_id": action_id,
                "name": "Updated Action Name",
                "delay_seconds": 10,
            }
        )
        response = await client.receive_json()
        assert response["success"]
        assert response["result"]["name"] == "Updated Action Name"
        assert response["result"]["delay_seconds"] == 10

        # 5. Toggle the action
        await client.send_json(
            {
                "id": 5,
                "type": "abode_security/actions/toggle",
                "action_id": action_id,
            }
        )
        response = await client.receive_json()
        assert response["success"]
        assert response["result"]["enabled"] is False

        # 6. Delete the action
        await client.send_json(
            {
                "id": 6,
                "type": "abode_security/actions/delete",
                "action_id": action_id,
            }
        )
        response = await client.receive_json()
        assert response["success"]

        # 7. Verify deletion
        await client.send_json({"id": 7, "type": "abode_security/actions/list"})
        response = await client.receive_json()
        assert response["success"]
        assert response["result"]["actions"] == []

    async def test_modes_list_returns_correct_format(
        self,
        hass: HomeAssistant,
        hass_ws_client,
        integration_setup,  # noqa: ARG002
    ) -> None:
        """Test that modes list returns properly formatted response."""
        client = await hass_ws_client(hass)

        await client.send_json({"id": 1, "type": "abode_security/modes/list"})
        response = await client.receive_json()

        assert response["success"]
        # Response should have 'modes' key containing list
        assert "modes" in response["result"]
        modes = response["result"]["modes"]

        # Should have 3 modes
        assert len(modes) == 3

        # Each mode should have required fields
        for mode in modes:
            assert "id" in mode
            assert "name" in mode
            assert "icon" in mode
            assert "action_count" in mode
            assert "active" in mode

        # Verify specific modes exist
        mode_ids = [m["id"] for m in modes]
        assert "standby" in mode_ids
        assert "home" in mode_ids
        assert "away" in mode_ids

    async def test_sensors_list_returns_correct_format(
        self,
        hass: HomeAssistant,
        hass_ws_client,
        integration_setup,  # noqa: ARG002
    ) -> None:
        """Test that sensors list returns properly formatted response."""
        # Add some test binary sensors
        hass.states.async_set(
            "binary_sensor.test_door",
            STATE_OFF,
            {"device_class": "door", "friendly_name": "Test Door"},
        )
        hass.states.async_set(
            "binary_sensor.test_motion",
            STATE_OFF,
            {"device_class": "motion", "friendly_name": "Test Motion"},
        )

        client = await hass_ws_client(hass)

        await client.send_json({"id": 1, "type": "abode_security/entities/sensors"})
        response = await client.receive_json()

        assert response["success"]
        # Response should have 'sensors' key
        assert "sensors" in response["result"]
        sensors = response["result"]["sensors"]

        # Sensors should be grouped by device class
        assert isinstance(sensors, dict)

        # Our test sensors should be in appropriate groups
        assert "door" in sensors
        assert "motion" in sensors

        # Each sensor should have required fields
        for device_class, sensor_list in sensors.items():
            for sensor in sensor_list:
                assert "entity_id" in sensor
                assert "name" in sensor
                assert "state" in sensor

    async def test_alarms_list_returns_correct_format(
        self,
        hass: HomeAssistant,
        hass_ws_client,
        integration_setup,  # noqa: ARG002
    ) -> None:
        """Test that alarms list returns properly formatted response."""
        # Add test Abode alarm switches
        hass.states.async_set(
            "switch.abode_panic_alarm",
            STATE_OFF,
            {"friendly_name": "Abode Panic Alarm"},
        )
        hass.states.async_set(
            "switch.abode_fire_alarm",
            STATE_OFF,
            {"friendly_name": "Abode Fire Alarm"},
        )

        client = await hass_ws_client(hass)

        await client.send_json({"id": 1, "type": "abode_security/entities/alarms"})
        response = await client.receive_json()

        assert response["success"]
        # Response should have 'alarms' key
        assert "alarms" in response["result"]
        alarms = response["result"]["alarms"]

        # Should have found the Abode alarm switches
        assert len(alarms) >= 2

        # Each alarm should have required fields
        for alarm in alarms:
            assert "entity_id" in alarm
            assert "name" in alarm
            assert "type" in alarm

        # Verify alarm types are detected
        alarm_types = {a["type"] for a in alarms}
        assert "panic" in alarm_types
        assert "fire" in alarm_types

    async def test_config_get_and_set(
        self,
        hass: HomeAssistant,
        hass_ws_client,
        integration_setup,  # noqa: ARG002
    ) -> None:
        """Test config get and set through WebSocket."""
        client = await hass_ws_client(hass)

        # Get initial config
        await client.send_json({"id": 1, "type": "abode_security/config/get"})
        response = await client.receive_json()
        assert response["success"]
        assert "debounce_seconds" in response["result"]

        # Update config
        new_debounce = 3.5
        await client.send_json(
            {
                "id": 2,
                "type": "abode_security/config/set",
                "debounce_seconds": new_debounce,
            }
        )
        response = await client.receive_json()
        assert response["success"]
        assert response["result"]["debounce_seconds"] == new_debounce

        # Verify change persisted
        await client.send_json({"id": 3, "type": "abode_security/config/get"})
        response = await client.receive_json()
        assert response["success"]
        assert response["result"]["debounce_seconds"] == new_debounce

    async def test_action_validation_errors(
        self,
        hass: HomeAssistant,
        hass_ws_client,
        integration_setup,  # noqa: ARG002
    ) -> None:
        """Test that validation errors are returned properly."""
        client = await hass_ws_client(hass)

        # Try to create action with empty name
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/create",
                "name": "",
                "modes": ["home"],
                "sensor_entity_ids": ["binary_sensor.door"],
                "alarm_entity_ids": ["switch.panic_alarm"],
            }
        )
        response = await client.receive_json()
        assert not response["success"]
        assert response["error"]["code"] == "validation_error"

        # Try to create action with no modes (should fail voluptuous validation)
        await client.send_json(
            {
                "id": 2,
                "type": "abode_security/actions/create",
                "name": "Test",
                "modes": [],
                "sensor_entity_ids": ["binary_sensor.door"],
                "alarm_entity_ids": ["switch.panic_alarm"],
            }
        )
        response = await client.receive_json()
        assert not response["success"]

    async def test_modes_action_count_updates(
        self,
        hass: HomeAssistant,
        hass_ws_client,
        integration_setup,  # noqa: ARG002
    ) -> None:
        """Test that mode action counts update when actions are added/removed."""
        client = await hass_ws_client(hass)

        # Get initial mode counts
        await client.send_json({"id": 1, "type": "abode_security/modes/list"})
        response = await client.receive_json()
        initial_counts = {
            m["id"]: m["action_count"] for m in response["result"]["modes"]
        }

        # Create an action for 'home' mode
        await client.send_json(
            {
                "id": 2,
                "type": "abode_security/actions/create",
                "name": "Count Test Action",
                "modes": ["home"],
                "sensor_entity_ids": ["binary_sensor.door"],
                "alarm_entity_ids": ["switch.panic_alarm"],
            }
        )
        response = await client.receive_json()
        assert response["success"]
        action_id = response["result"]["id"]

        # Check mode counts updated
        await client.send_json({"id": 3, "type": "abode_security/modes/list"})
        response = await client.receive_json()
        new_counts = {m["id"]: m["action_count"] for m in response["result"]["modes"]}

        assert new_counts["home"] == initial_counts["home"] + 1
        assert new_counts["away"] == initial_counts["away"]
        assert new_counts["standby"] == initial_counts["standby"]

        # Delete the action
        await client.send_json(
            {
                "id": 4,
                "type": "abode_security/actions/delete",
                "action_id": action_id,
            }
        )
        await client.receive_json()

        # Verify count went back down
        await client.send_json({"id": 5, "type": "abode_security/modes/list"})
        response = await client.receive_json()
        final_counts = {m["id"]: m["action_count"] for m in response["result"]["modes"]}
        assert final_counts["home"] == initial_counts["home"]


@pytest.mark.integration
class TestActionTriggerIntegration:
    """Integration tests for action triggering."""

    async def test_coordinator_triggers_on_sensor_change(
        self, hass: HomeAssistant, integration_setup
    ) -> None:
        """Test that coordinator triggers actions when sensors change state."""
        action_manager = integration_setup["action_manager"]

        # Set up test entities
        hass.states.async_set(
            "alarm_control_panel.abode_alarm",
            "armed_home",  # This maps to 'home' mode
        )
        hass.states.async_set(
            "binary_sensor.test_sensor",
            STATE_OFF,
        )
        hass.states.async_set(
            "switch.abode_panic_alarm",
            STATE_OFF,
        )

        # Create an action that should trigger
        action = await action_manager.async_create(
            name="Trigger Test",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.test_sensor"],
            alarm_entity_ids=["switch.abode_panic_alarm"],
            delay_seconds=0,
        )

        # Verify initial state
        assert action.trigger_count == 0

        # Trigger the sensor
        hass.states.async_set(
            "binary_sensor.test_sensor",
            STATE_ON,
        )

        # Give the coordinator time to process
        await hass.async_block_till_done()

        # Check that action was triggered
        updated_action = await action_manager.async_get(action.id)
        assert updated_action is not None
        assert updated_action.trigger_count == 1
        assert updated_action.last_triggered is not None

    async def test_coordinator_respects_mode_filter(
        self, hass: HomeAssistant, integration_setup
    ) -> None:
        """Test that coordinator only triggers for matching modes."""
        action_manager = integration_setup["action_manager"]

        # Set up test entities - alarm is in 'away' mode
        hass.states.async_set(
            "alarm_control_panel.abode_alarm",
            "armed_away",  # This maps to 'away' mode
        )
        hass.states.async_set(
            "binary_sensor.mode_test_sensor",
            STATE_OFF,
        )

        # Create an action only for 'home' mode
        action = await action_manager.async_create(
            name="Mode Filter Test",
            modes=["home"],  # Only triggers in home mode
            sensor_entity_ids=["binary_sensor.mode_test_sensor"],
            alarm_entity_ids=["switch.abode_panic_alarm"],
        )

        # Trigger the sensor
        hass.states.async_set(
            "binary_sensor.mode_test_sensor",
            STATE_ON,
        )
        await hass.async_block_till_done()

        # Action should NOT have triggered (wrong mode)
        updated_action = await action_manager.async_get(action.id)
        assert updated_action is not None
        assert updated_action.trigger_count == 0

    async def test_coordinator_respects_enabled_state(
        self, hass: HomeAssistant, integration_setup
    ) -> None:
        """Test that disabled actions are not triggered."""
        action_manager = integration_setup["action_manager"]

        # Set up test entities
        hass.states.async_set(
            "alarm_control_panel.abode_alarm",
            "armed_home",
        )
        hass.states.async_set(
            "binary_sensor.enabled_test_sensor",
            STATE_OFF,
        )

        # Create a disabled action
        action = await action_manager.async_create(
            name="Disabled Action Test",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.enabled_test_sensor"],
            alarm_entity_ids=["switch.abode_panic_alarm"],
            enabled=False,
        )

        # Trigger the sensor
        hass.states.async_set(
            "binary_sensor.enabled_test_sensor",
            STATE_ON,
        )
        await hass.async_block_till_done()

        # Action should NOT have triggered (disabled)
        updated_action = await action_manager.async_get(action.id)
        assert updated_action is not None
        assert updated_action.trigger_count == 0

    async def test_coordinator_fires_event(
        self, hass: HomeAssistant, integration_setup
    ) -> None:
        """Test that coordinator fires HA event when action triggers."""
        action_manager = integration_setup["action_manager"]
        events_fired = []

        # Listen for events
        def event_listener(event):
            events_fired.append(event)

        hass.bus.async_listen("abode_security.action_triggered", event_listener)

        # Set up test entities
        hass.states.async_set(
            "alarm_control_panel.abode_alarm",
            "armed_home",
        )
        hass.states.async_set(
            "binary_sensor.event_test_sensor",
            STATE_OFF,
        )

        # Create an action
        action = await action_manager.async_create(
            name="Event Test Action",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.event_test_sensor"],
            alarm_entity_ids=["switch.abode_panic_alarm"],
            delay_seconds=0,
        )

        # Trigger the sensor
        hass.states.async_set(
            "binary_sensor.event_test_sensor",
            STATE_ON,
        )
        await hass.async_block_till_done()

        # Verify event was fired
        assert len(events_fired) == 1
        event_data = events_fired[0].data
        assert event_data["action_id"] == action.id
        assert event_data["action_name"] == "Event Test Action"
        assert event_data["triggered_by"] == "binary_sensor.event_test_sensor"
        assert event_data["mode"] == "home"

    async def test_multiple_actions_can_trigger(
        self, hass: HomeAssistant, integration_setup
    ) -> None:
        """Test that multiple actions can trigger from the same sensor."""
        action_manager = integration_setup["action_manager"]

        # Set up test entities
        hass.states.async_set(
            "alarm_control_panel.abode_alarm",
            "armed_home",
        )
        hass.states.async_set(
            "binary_sensor.multi_test_sensor",
            STATE_OFF,
        )

        # Create two actions for the same sensor
        action1 = await action_manager.async_create(
            name="Multi Test 1",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.multi_test_sensor"],
            alarm_entity_ids=["switch.abode_panic_alarm"],
        )
        action2 = await action_manager.async_create(
            name="Multi Test 2",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.multi_test_sensor"],
            alarm_entity_ids=["switch.abode_fire_alarm"],
        )

        # Trigger the sensor
        hass.states.async_set(
            "binary_sensor.multi_test_sensor",
            STATE_ON,
        )
        await hass.async_block_till_done()

        # Both actions should have triggered
        updated1 = await action_manager.async_get(action1.id)
        updated2 = await action_manager.async_get(action2.id)

        assert updated1.trigger_count == 1
        assert updated2.trigger_count == 1
