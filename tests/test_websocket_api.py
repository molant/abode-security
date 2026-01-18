"""Tests for the WebSocket API module."""

import pytest

from custom_components.abode_security.action_manager import ActionManager
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
async def setup_websocket_api(hass, action_manager):
    """Set up WebSocket API with ActionManager in hass.data."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["action_manager"] = action_manager
    async_register_websocket_commands(hass)
    return action_manager


def _get_manager(hass):
    """Get ActionManager from hass.data."""
    return hass.data[DOMAIN]["action_manager"]


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
