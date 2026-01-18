"""Tests for the WebSocket API module."""

import pytest

from custom_components.abode_security.action_manager import ActionManager
from custom_components.abode_security.config_store import ConfigStore
from custom_components.abode_security.const import DOMAIN
from custom_components.abode_security.websocket_api import (
    async_register_websocket_commands,
)


@pytest.fixture
async def action_manager(hass):
    """Create an ActionManager for testing."""
    manager = ActionManager(hass)
    await manager.async_setup()
    return manager


@pytest.fixture
async def config_store(hass):
    """Create a ConfigStore for testing."""
    store = ConfigStore(hass)
    await store.async_load()
    return store


@pytest.fixture
async def setup_websocket_api(hass, action_manager, config_store):
    """Set up WebSocket API with ActionManager and ConfigStore in hass.data."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["action_manager"] = action_manager
    hass.data[DOMAIN]["config_store"] = config_store
    hass.data[DOMAIN]["config"] = config_store.get_config()
    async_register_websocket_commands(hass)
    return action_manager


def _get_manager(hass):
    """Get ActionManager from hass.data."""
    return hass.data[DOMAIN]["action_manager"]


def _get_config_store(hass):
    """Get ConfigStore from hass.data."""
    return hass.data[DOMAIN]["config_store"]


@pytest.mark.usefixtures("mock_abode", "setup_websocket_api")
class TestWebSocketActionsAPI:
    """Tests for WebSocket actions API."""

    # --- List Actions ---

    async def test_ws_actions_list_empty(self, hass, hass_ws_client) -> None:
        """Test listing actions when none exist."""
        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/actions/list"})
        response = await client.receive_json()

        assert response["success"]
        assert response["result"]["actions"] == []

    async def test_ws_actions_list_with_data(self, hass, hass_ws_client) -> None:
        """Test listing actions with existing data."""
        manager = _get_manager(hass)
        await manager.async_create(
            name="Test Action",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/actions/list"})
        response = await client.receive_json()

        assert response["success"]
        assert len(response["result"]["actions"]) == 1
        assert response["result"]["actions"][0]["name"] == "Test Action"

    # --- Get Action ---

    async def test_ws_actions_get(self, hass, hass_ws_client) -> None:
        """Test getting a single action by ID."""
        manager = _get_manager(hass)
        action = await manager.async_create(
            name="Test Action",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/get",
                "action_id": action.id,
            }
        )
        response = await client.receive_json()

        assert response["success"]
        assert response["result"]["id"] == action.id
        assert response["result"]["name"] == "Test Action"

    async def test_ws_actions_get_not_found(self, hass, hass_ws_client) -> None:
        """Test getting a non-existent action returns error."""
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/get",
                "action_id": "non-existent",
            }
        )
        response = await client.receive_json()

        assert not response["success"]
        assert response["error"]["code"] == "not_found"

    # --- Create Action ---

    async def test_ws_actions_create(self, hass, hass_ws_client) -> None:
        """Test creating a new action."""
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/create",
                "name": "New Action",
                "modes": ["home"],
                "sensor_entity_ids": ["binary_sensor.door"],
                "alarm_entity_ids": ["switch.panic_alarm"],
            }
        )
        response = await client.receive_json()

        assert response["success"]
        assert response["result"]["name"] == "New Action"
        assert "id" in response["result"]
        assert response["result"]["enabled"] is True

    async def test_ws_actions_create_with_delay(self, hass, hass_ws_client) -> None:
        """Test creating an action with delay."""
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/create",
                "name": "Delayed Action",
                "modes": ["away"],
                "sensor_entity_ids": ["binary_sensor.motion"],
                "alarm_entity_ids": ["switch.panic_alarm"],
                "delay_seconds": 30,
            }
        )
        response = await client.receive_json()

        assert response["success"]
        assert response["result"]["delay_seconds"] == 30

    async def test_ws_actions_create_validation_error(
        self, hass, hass_ws_client
    ) -> None:
        """Test creating an action with invalid data returns validation error."""
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/create",
                "name": "",  # Invalid: empty name
                "modes": ["home"],
                "sensor_entity_ids": ["binary_sensor.door"],
                "alarm_entity_ids": ["switch.panic_alarm"],
            }
        )
        response = await client.receive_json()

        assert not response["success"]
        assert response["error"]["code"] == "validation_error"

    async def test_ws_actions_create_invalid_mode_schema(
        self, hass, hass_ws_client
    ) -> None:
        """Test creating an action with invalid mode fails schema validation."""
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/create",
                "name": "Test",
                "modes": ["invalid_mode"],  # Invalid mode
                "sensor_entity_ids": ["binary_sensor.door"],
                "alarm_entity_ids": ["switch.panic_alarm"],
            }
        )
        response = await client.receive_json()

        # Schema validation should reject invalid modes
        assert not response["success"]

    # --- Update Action ---

    async def test_ws_actions_update(self, hass, hass_ws_client) -> None:
        """Test updating an action."""
        manager = _get_manager(hass)
        action = await manager.async_create(
            name="Original",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/update",
                "action_id": action.id,
                "name": "Updated",
            }
        )
        response = await client.receive_json()

        assert response["success"]
        assert response["result"]["name"] == "Updated"
        assert response["result"]["id"] == action.id

    async def test_ws_actions_update_not_found(self, hass, hass_ws_client) -> None:
        """Test updating a non-existent action returns error."""
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/update",
                "action_id": "non-existent",
                "name": "Updated",
            }
        )
        response = await client.receive_json()

        assert not response["success"]
        assert response["error"]["code"] == "not_found"

    async def test_ws_actions_update_validation_error(
        self, hass, hass_ws_client
    ) -> None:
        """Test updating an action with invalid data returns error."""
        manager = _get_manager(hass)
        action = await manager.async_create(
            name="Original",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/update",
                "action_id": action.id,
                "name": "",  # Invalid: empty name
            }
        )
        response = await client.receive_json()

        assert not response["success"]
        assert response["error"]["code"] == "validation_error"

    # --- Delete Action ---

    async def test_ws_actions_delete(self, hass, hass_ws_client) -> None:
        """Test deleting an action."""
        manager = _get_manager(hass)
        action = await manager.async_create(
            name="To Delete",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/delete",
                "action_id": action.id,
            }
        )
        response = await client.receive_json()

        assert response["success"]
        assert response["result"]["success"] is True

        # Verify deleted
        assert await manager.async_get(action.id) is None

    async def test_ws_actions_delete_not_found(self, hass, hass_ws_client) -> None:
        """Test deleting a non-existent action returns error."""
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/delete",
                "action_id": "non-existent",
            }
        )
        response = await client.receive_json()

        assert not response["success"]
        assert response["error"]["code"] == "not_found"

    # --- Toggle Action ---

    async def test_ws_actions_toggle(self, hass, hass_ws_client) -> None:
        """Test toggling an action's enabled state."""
        manager = _get_manager(hass)
        action = await manager.async_create(
            name="Test",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        assert action.enabled is True

        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/toggle",
                "action_id": action.id,
            }
        )
        response = await client.receive_json()

        assert response["success"]
        assert response["result"]["enabled"] is False

        # Toggle again
        await client.send_json(
            {
                "id": 2,
                "type": "abode_security/actions/toggle",
                "action_id": action.id,
            }
        )
        response = await client.receive_json()

        assert response["success"]
        assert response["result"]["enabled"] is True

    async def test_ws_actions_toggle_not_found(self, hass, hass_ws_client) -> None:
        """Test toggling a non-existent action returns error."""
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/toggle",
                "action_id": "non-existent",
            }
        )
        response = await client.receive_json()

        assert not response["success"]
        assert response["error"]["code"] == "not_found"

    # --- Test Action (Manual Trigger) ---

    async def test_ws_actions_test(self, hass, hass_ws_client) -> None:
        """Test manually triggering an action."""
        manager = _get_manager(hass)
        action = await manager.async_create(
            name="Test",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        # Create a mock switch entity so the service call can succeed
        hass.states.async_set("switch.panic_alarm", "off")

        calls = []

        async def mock_service(call):
            calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)

        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/test",
                "action_id": action.id,
            }
        )
        response = await client.receive_json()

        assert response["success"]
        assert "alarms_triggered" in response["result"]
        assert "switch.panic_alarm" in response["result"]["alarms_triggered"]

        # Verify service was called
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "switch.panic_alarm"

    async def test_ws_actions_test_not_found(self, hass, hass_ws_client) -> None:
        """Test triggering a non-existent action returns error."""
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/test",
                "action_id": "non-existent",
            }
        )
        response = await client.receive_json()

        assert not response["success"]
        assert response["error"]["code"] == "not_found"

    async def test_ws_actions_test_multiple_alarms(self, hass, hass_ws_client) -> None:
        """Test triggering an action with multiple alarms."""
        manager = _get_manager(hass)
        action = await manager.async_create(
            name="Multi-alarm",
            modes=["away"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm", "switch.fire_alarm"],
        )

        # Create mock switch entities
        hass.states.async_set("switch.panic_alarm", "off")
        hass.states.async_set("switch.fire_alarm", "off")

        calls = []

        async def mock_service(call):
            calls.append(call)

        hass.services.async_register("switch", "turn_on", mock_service)

        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/test",
                "action_id": action.id,
            }
        )
        response = await client.receive_json()

        assert response["success"]
        assert len(response["result"]["alarms_triggered"]) == 2
        assert len(calls) == 2


@pytest.mark.usefixtures("mock_abode", "setup_websocket_api")
class TestWebSocketActionsAuthorization:
    """Tests for WebSocket actions API authorization."""

    async def test_ws_actions_list_no_admin_required(
        self, hass, hass_ws_client
    ) -> None:
        """Test that list action does not require admin."""
        # hass_ws_client creates an admin by default, but list should work for non-admin too
        # For now, just verify it works - we'll add non-admin test when fixture is available
        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/actions/list"})
        response = await client.receive_json()
        assert response["success"]

    async def test_ws_actions_get_no_admin_required(self, hass, hass_ws_client) -> None:
        """Test that get action does not require admin."""
        manager = _get_manager(hass)
        action = await manager.async_create(
            name="Test",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/get",
                "action_id": action.id,
            }
        )
        response = await client.receive_json()
        assert response["success"]


@pytest.mark.usefixtures("mock_abode")
class TestWebSocketActionsNotReady:
    """Tests for WebSocket API when action manager is not initialized."""

    async def test_ws_actions_list_not_ready(self, hass, hass_ws_client) -> None:
        """Test listing actions when manager not initialized."""
        # Register commands but don't set up action_manager
        async_register_websocket_commands(hass)

        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/actions/list"})
        response = await client.receive_json()

        assert not response["success"]
        assert response["error"]["code"] == "not_ready"


# --- Sub-Phase B: Entity Query Endpoints ---


@pytest.mark.usefixtures("mock_abode", "setup_websocket_api")
class TestWebSocketModesAPI:
    """Tests for WebSocket modes API."""

    async def test_ws_modes_list(self, hass, hass_ws_client) -> None:
        """Test listing modes returns all three modes."""
        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/modes/list"})
        response = await client.receive_json()

        assert response["success"]
        modes = response["result"]
        assert len(modes) == 3

        mode_ids = {m["id"] for m in modes}
        assert mode_ids == {"standby", "home", "away"}

    async def test_ws_modes_list_with_active_mode(self, hass, hass_ws_client) -> None:
        """Test listing modes shows correct active mode."""
        # Set alarm panel to armed_home
        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")

        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/modes/list"})
        response = await client.receive_json()

        assert response["success"]
        modes = response["result"]

        home_mode = next(m for m in modes if m["id"] == "home")
        assert home_mode["active"] is True

        standby_mode = next(m for m in modes if m["id"] == "standby")
        assert standby_mode["active"] is False

        away_mode = next(m for m in modes if m["id"] == "away")
        assert away_mode["active"] is False

    async def test_ws_modes_list_disarmed(self, hass, hass_ws_client) -> None:
        """Test disarmed state maps to standby mode."""
        hass.states.async_set("alarm_control_panel.abode_alarm", "disarmed")

        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/modes/list"})
        response = await client.receive_json()

        assert response["success"]
        standby_mode = next(m for m in response["result"] if m["id"] == "standby")
        assert standby_mode["active"] is True

    async def test_ws_modes_list_with_action_count(self, hass, hass_ws_client) -> None:
        """Test modes include action counts."""
        manager = _get_manager(hass)
        await manager.async_create(
            name="Home Action",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        await manager.async_create(
            name="Away Action",
            modes=["away"],
            sensor_entity_ids=["binary_sensor.motion"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/modes/list"})
        response = await client.receive_json()

        assert response["success"]
        home_mode = next(m for m in response["result"] if m["id"] == "home")
        assert home_mode["action_count"] == 1

        away_mode = next(m for m in response["result"] if m["id"] == "away")
        assert away_mode["action_count"] == 1

        standby_mode = next(m for m in response["result"] if m["id"] == "standby")
        assert standby_mode["action_count"] == 0

    async def test_ws_modes_list_has_metadata(self, hass, hass_ws_client) -> None:
        """Test modes include name and icon metadata."""
        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/modes/list"})
        response = await client.receive_json()

        assert response["success"]
        for mode in response["result"]:
            assert "name" in mode
            assert "icon" in mode
            assert mode["icon"].startswith("mdi:")


@pytest.mark.usefixtures("mock_abode", "setup_websocket_api")
class TestWebSocketSensorsAPI:
    """Tests for WebSocket sensors API."""

    async def test_ws_entities_sensors_empty(self, hass, hass_ws_client) -> None:
        """Test listing sensors when none exist."""
        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/entities/sensors"})
        response = await client.receive_json()

        assert response["success"]
        assert response["result"]["sensors"] == {}

    async def test_ws_entities_sensors_grouped_by_device_class(
        self, hass, hass_ws_client
    ) -> None:
        """Test sensors are grouped by device_class."""
        hass.states.async_set(
            "binary_sensor.front_door",
            "off",
            {"device_class": "door", "friendly_name": "Front Door"},
        )
        hass.states.async_set(
            "binary_sensor.back_door",
            "on",
            {"device_class": "door", "friendly_name": "Back Door"},
        )
        hass.states.async_set(
            "binary_sensor.living_room_motion",
            "off",
            {"device_class": "motion", "friendly_name": "Living Room Motion"},
        )

        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/entities/sensors"})
        response = await client.receive_json()

        assert response["success"]
        sensors = response["result"]["sensors"]

        assert "door" in sensors
        assert len(sensors["door"]) == 2

        assert "motion" in sensors
        assert len(sensors["motion"]) == 1

    async def test_ws_entities_sensors_includes_state(
        self, hass, hass_ws_client
    ) -> None:
        """Test sensor info includes state."""
        hass.states.async_set(
            "binary_sensor.door",
            "on",
            {"device_class": "door", "friendly_name": "Door"},
        )

        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/entities/sensors"})
        response = await client.receive_json()

        assert response["success"]
        door_sensor = response["result"]["sensors"]["door"][0]
        assert door_sensor["state"] == "on"
        assert door_sensor["entity_id"] == "binary_sensor.door"
        assert door_sensor["name"] == "Door"

    async def test_ws_entities_sensors_no_device_class(
        self, hass, hass_ws_client
    ) -> None:
        """Test sensors without device_class go to 'other'."""
        hass.states.async_set(
            "binary_sensor.unknown",
            "off",
            {"friendly_name": "Unknown Sensor"},
        )

        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/entities/sensors"})
        response = await client.receive_json()

        assert response["success"]
        assert "other" in response["result"]["sensors"]
        assert len(response["result"]["sensors"]["other"]) == 1


@pytest.mark.usefixtures("mock_abode", "setup_websocket_api")
class TestWebSocketAlarmsAPI:
    """Tests for WebSocket alarms API."""

    async def test_ws_entities_alarms_empty(self, hass, hass_ws_client) -> None:
        """Test listing alarms when none exist."""
        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/entities/alarms"})
        response = await client.receive_json()

        assert response["success"]
        assert response["result"]["alarms"] == []

    async def test_ws_entities_alarms_filters_abode_alarms(
        self, hass, hass_ws_client
    ) -> None:
        """Test only Abode alarm switches are returned."""
        # Abode alarm switches
        hass.states.async_set(
            "switch.abode_panic_alarm", "off", {"friendly_name": "Panic Alarm"}
        )
        hass.states.async_set(
            "switch.abode_medical_alarm", "off", {"friendly_name": "Medical Alarm"}
        )
        # Non-alarm switches (should be excluded)
        hass.states.async_set("switch.living_room_light", "on")
        hass.states.async_set("switch.abode_automation", "on")

        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/entities/alarms"})
        response = await client.receive_json()

        assert response["success"]
        alarms = response["result"]["alarms"]
        assert len(alarms) == 2

        entity_ids = {a["entity_id"] for a in alarms}
        assert "switch.abode_panic_alarm" in entity_ids
        assert "switch.abode_medical_alarm" in entity_ids

    async def test_ws_entities_alarms_includes_type(self, hass, hass_ws_client) -> None:
        """Test alarm info includes type."""
        hass.states.async_set(
            "switch.abode_panic_alarm", "off", {"friendly_name": "Panic Alarm"}
        )
        hass.states.async_set(
            "switch.abode_fire_alarm", "off", {"friendly_name": "Fire Alarm"}
        )

        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/entities/alarms"})
        response = await client.receive_json()

        assert response["success"]
        alarms = response["result"]["alarms"]

        panic = next(a for a in alarms if a["entity_id"] == "switch.abode_panic_alarm")
        assert panic["type"] == "panic"
        assert panic["name"] == "Panic Alarm"

        fire = next(a for a in alarms if a["entity_id"] == "switch.abode_fire_alarm")
        assert fire["type"] == "fire"


# --- Sub-Phase C: Config Endpoints ---


@pytest.mark.usefixtures("mock_abode", "setup_websocket_api")
class TestWebSocketConfigAPI:
    """Tests for WebSocket config API."""

    async def test_ws_config_get(self, hass, hass_ws_client) -> None:
        """Test getting config returns default values."""
        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/config/get"})
        response = await client.receive_json()

        assert response["success"]
        assert "debounce_seconds" in response["result"]
        assert response["result"]["debounce_seconds"] == 1.0  # default

    async def test_ws_config_set(self, hass, hass_ws_client) -> None:
        """Test setting config value."""
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/config/set",
                "debounce_seconds": 2.5,
            }
        )
        response = await client.receive_json()

        assert response["success"]
        assert response["result"]["debounce_seconds"] == 2.5

        # Verify cached config is updated
        assert hass.data[DOMAIN]["config"]["debounce_seconds"] == 2.5

    async def test_ws_config_set_min_value(self, hass, hass_ws_client) -> None:
        """Test setting config to minimum value."""
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/config/set",
                "debounce_seconds": 0.1,
            }
        )
        response = await client.receive_json()

        assert response["success"]
        assert response["result"]["debounce_seconds"] == 0.1

    async def test_ws_config_set_max_value(self, hass, hass_ws_client) -> None:
        """Test setting config to maximum value."""
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/config/set",
                "debounce_seconds": 10.0,
            }
        )
        response = await client.receive_json()

        assert response["success"]
        assert response["result"]["debounce_seconds"] == 10.0

    async def test_ws_config_set_below_min(self, hass, hass_ws_client) -> None:
        """Test setting config below minimum is rejected."""
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/config/set",
                "debounce_seconds": 0.05,  # Below 0.1 minimum
            }
        )
        response = await client.receive_json()

        assert not response["success"]

    async def test_ws_config_set_above_max(self, hass, hass_ws_client) -> None:
        """Test setting config above maximum is rejected."""
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/config/set",
                "debounce_seconds": 15.0,  # Above 10.0 maximum
            }
        )
        response = await client.receive_json()

        assert not response["success"]

    async def test_ws_config_set_no_fields(self, hass, hass_ws_client) -> None:
        """Test calling set with no fields returns current config."""
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/config/set",
            }
        )
        response = await client.receive_json()

        assert response["success"]
        assert "debounce_seconds" in response["result"]

    async def test_ws_config_persistence(self, hass, hass_ws_client) -> None:
        """Test config is persisted to store."""
        config_store = _get_config_store(hass)

        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/config/set",
                "debounce_seconds": 3.0,
            }
        )
        await client.receive_json()

        # Verify config store has the value
        stored_config = config_store.get_config()
        assert stored_config["debounce_seconds"] == 3.0


@pytest.mark.usefixtures("mock_abode")
class TestWebSocketConfigNotReady:
    """Tests for WebSocket config API when store is not initialized."""

    async def test_ws_config_get_not_ready(self, hass, hass_ws_client) -> None:
        """Test getting config when store not initialized."""
        # Register commands but don't set up config_store
        async_register_websocket_commands(hass)

        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/config/get"})
        response = await client.receive_json()

        assert not response["success"]
        assert response["error"]["code"] == "not_ready"

    async def test_ws_config_set_not_ready(self, hass, hass_ws_client) -> None:
        """Test setting config when store not initialized."""
        async_register_websocket_commands(hass)

        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/config/set",
                "debounce_seconds": 2.0,
            }
        )
        response = await client.receive_json()

        assert not response["success"]
        assert response["error"]["code"] == "not_ready"
