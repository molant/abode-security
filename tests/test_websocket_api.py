"""Tests for the WebSocket API module."""

import pytest
from homeassistant.helpers import entity_registry as er

from custom_components.abode_security.action_manager import (
    MAX_NAME_LENGTH,
    ActionManager,
)
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

    async def test_ws_actions_create_with_enabled_false(
        self, hass, hass_ws_client
    ) -> None:
        """`actions/create` honours an explicit `enabled: False` payload.

        Mirrors the `async_update` contract; without this, the only way
        to create a disabled action was to create-then-toggle, which races
        the `ActionTriggerCoordinator` on entity transitions during the
        gap (#103).
        """
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/create",
                "name": "Disabled at create",
                "modes": ["home"],
                "sensor_entity_ids": ["binary_sensor.door"],
                "alarm_entity_ids": ["switch.panic_alarm"],
                "enabled": False,
            }
        )
        response = await client.receive_json()

        assert response["success"]
        assert response["result"]["enabled"] is False

    async def test_ws_actions_create_validation_error(
        self, hass, hass_ws_client
    ) -> None:
        """An empty `name` is a business-rule violation, not a shape error.

        The voluptuous schema only enforces *shape* bounds (type and the
        upper-length cap). The `"name must not be empty"` rule lives in
        `ActionManager._validate_action` so the error message is richer
        than voluptuous's generic `expected str with length >= 1`. We
        check both whitespace-only and empty-string here to lock down
        the runtime-validation boundary against accidental schema
        tightening (#102).
        """
        client = await hass_ws_client(hass)
        for msg_id, bad_name in ((1, ""), (2, "   ")):
            await client.send_json(
                {
                    "id": msg_id,
                    "type": "abode_security/actions/create",
                    "name": bad_name,
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

    # --- Oversize payload guards (defense in depth, see issue #55) ---

    async def test_ws_actions_create_name_too_long(self, hass, hass_ws_client) -> None:
        """Schema rejects names longer than MAX_NAME_LENGTH."""
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/create",
                "name": "x" * (MAX_NAME_LENGTH + 1),
                "modes": ["home"],
                "sensor_entity_ids": ["binary_sensor.door"],
                "alarm_entity_ids": ["switch.panic_alarm"],
            }
        )
        response = await client.receive_json()

        assert not response["success"]
        assert response["error"]["code"] == "invalid_format"

    async def test_ws_actions_create_too_many_modes(self, hass, hass_ws_client) -> None:
        """Schema rejects mode lists larger than VALID_MODES.

        VALID_MODES has 3 entries and the element validator already rejects
        unknown modes, so the only way to exceed the length cap is to include
        a duplicate — which is exactly what this case tests.
        """
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/create",
                "name": "Test",
                "modes": ["home", "away", "standby", "home"],
                "sensor_entity_ids": ["binary_sensor.door"],
                "alarm_entity_ids": ["switch.panic_alarm"],
            }
        )
        response = await client.receive_json()

        assert not response["success"]
        assert response["error"]["code"] == "invalid_format"

    async def test_ws_actions_create_too_many_sensors(
        self, hass, hass_ws_client
    ) -> None:
        """Schema rejects sensor_entity_ids lists longer than 64."""
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/create",
                "name": "Test",
                "modes": ["home"],
                "sensor_entity_ids": [f"binary_sensor.door_{i}" for i in range(65)],
                "alarm_entity_ids": ["switch.panic_alarm"],
            }
        )
        response = await client.receive_json()

        assert not response["success"]
        assert response["error"]["code"] == "invalid_format"

    async def test_ws_actions_create_rejects_bool_delay(
        self, hass, hass_ws_client
    ) -> None:
        """Schema rejects ``delay_seconds=True``/``False`` (bool is an int).

        ActionStore.from_dict rejects bools for delay_seconds and would drop
        the record as corrupt on next load — the schema must reject them too
        to keep all three layers consistent.
        """
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/create",
                "name": "Test",
                "modes": ["home"],
                "sensor_entity_ids": ["binary_sensor.door"],
                "alarm_entity_ids": ["switch.panic_alarm"],
                "delay_seconds": True,
            }
        )
        response = await client.receive_json()

        assert not response["success"]
        assert response["error"]["code"] == "invalid_format"

    async def test_ws_actions_create_too_many_alarms(
        self, hass, hass_ws_client
    ) -> None:
        """Schema rejects alarm_entity_ids lists longer than 16."""
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/actions/create",
                "name": "Test",
                "modes": ["home"],
                "sensor_entity_ids": ["binary_sensor.door"],
                "alarm_entity_ids": [f"switch.alarm_{i}" for i in range(17)],
            }
        )
        response = await client.receive_json()

        assert not response["success"]
        assert response["error"]["code"] == "invalid_format"

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
        """Empty / whitespace `name` on update is a business-rule violation.

        Mirrors the create-path contract (#102): the schema only enforces
        shape and the upper-length cap; emptiness is rejected by
        `_validate_action` so the error code is `validation_error`, not
        `invalid_format`.
        """
        manager = _get_manager(hass)
        action = await manager.async_create(
            name="Original",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        client = await hass_ws_client(hass)
        for msg_id, bad_name in ((1, ""), (2, "   ")):
            await client.send_json(
                {
                    "id": msg_id,
                    "type": "abode_security/actions/update",
                    "action_id": action.id,
                    "name": bad_name,
                }
            )
            response = await client.receive_json()

            assert not response["success"]
            assert response["error"]["code"] == "validation_error"

    async def test_ws_actions_update_name_too_long(self, hass, hass_ws_client) -> None:
        """Update schema applies the same oversize guards as create."""
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
                "name": "x" * (MAX_NAME_LENGTH + 1),
            }
        )
        response = await client.receive_json()

        assert not response["success"]
        assert response["error"]["code"] == "invalid_format"

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
class TestWebSocketAdminGating:
    """Verify admin-gating on WebSocket commands matches the policy in
    websocket_api.py's `async_register_websocket_commands` docstring.

    Non-admin users (HA "read-only" group) must be rejected with
    `unauthorized` for:
      - All mutating commands.
      - Topology-exposing read-only commands: actions/{list,get},
        entities/{sensors,alarms}.

    Non-admin users must be allowed for the two non-sensitive read-only
    commands: modes/list, config/get.
    """

    @pytest.mark.parametrize(
        ("command_type", "extra_payload"),
        [
            # Topology-exposing read-only commands.
            ("abode_security/actions/list", {}),
            ("abode_security/actions/get", {"action_id": "any"}),
            ("abode_security/entities/sensors", {}),
            ("abode_security/entities/alarms", {}),
            # Mutating commands. Payloads are schema-valid so the request
            # reaches the @require_admin check rather than failing
            # earlier in @websocket_command's schema validator.
            (
                "abode_security/actions/create",
                {
                    "name": "x",
                    "modes": ["home"],
                    "sensor_entity_ids": ["binary_sensor.door"],
                    "alarm_entity_ids": ["switch.panic_alarm"],
                },
            ),
            ("abode_security/actions/update", {"action_id": "any"}),
            ("abode_security/actions/delete", {"action_id": "any"}),
            ("abode_security/actions/toggle", {"action_id": "any"}),
            ("abode_security/actions/test", {"action_id": "any"}),
            ("abode_security/modes/set", {"mode_id": "home"}),
            ("abode_security/config/set", {}),
        ],
        ids=[
            "actions/list",
            "actions/get",
            "entities/sensors",
            "entities/alarms",
            "actions/create",
            "actions/update",
            "actions/delete",
            "actions/toggle",
            "actions/test",
            "modes/set",
            "config/set",
        ],
    )
    async def test_admin_gated_commands_reject_non_admin(
        self,
        hass,
        hass_ws_client,
        hass_read_only_access_token,
        command_type,
        extra_payload,
    ) -> None:
        """Non-admin users get `unauthorized` from admin-gated commands."""
        client = await hass_ws_client(hass, hass_read_only_access_token)
        await client.send_json({"id": 1, "type": command_type, **extra_payload})
        response = await client.receive_json()

        assert not response["success"]
        assert response["error"]["code"] == "unauthorized"

    async def test_modes_list_allowed_for_non_admin(
        self, hass, hass_ws_client, hass_read_only_access_token
    ) -> None:
        """`modes/list` returns mode metadata and current active state,
        which HA's state APIs already expose; non-admin users may call it."""
        client = await hass_ws_client(hass, hass_read_only_access_token)
        await client.send_json({"id": 1, "type": "abode_security/modes/list"})
        response = await client.receive_json()

        assert response["success"]

    async def test_config_get_allowed_for_non_admin(
        self, hass, hass_ws_client, hass_read_only_access_token
    ) -> None:
        """`config/get` exposes only non-sensitive settings; non-admin OK."""
        client = await hass_ws_client(hass, hass_read_only_access_token)
        await client.send_json({"id": 1, "type": "abode_security/config/get"})
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
        modes = response["result"]["modes"]
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
        modes = response["result"]["modes"]

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
        standby_mode = next(
            m for m in response["result"]["modes"] if m["id"] == "standby"
        )
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
        modes = response["result"]["modes"]
        home_mode = next(m for m in modes if m["id"] == "home")
        assert home_mode["action_count"] == 1

        away_mode = next(m for m in modes if m["id"] == "away")
        assert away_mode["action_count"] == 1

        standby_mode = next(m for m in modes if m["id"] == "standby")
        assert standby_mode["action_count"] == 0

    async def test_ws_modes_list_has_metadata(self, hass, hass_ws_client) -> None:
        """Test modes include name and icon metadata."""
        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/modes/list"})
        response = await client.receive_json()

        assert response["success"]
        for mode in response["result"]["modes"]:
            assert "name" in mode
            assert "icon" in mode
            assert mode["icon"].startswith("mdi:")

    # --- Set mode (#1) ---

    async def test_ws_modes_set_home(self, hass, hass_ws_client) -> None:
        """Setting mode=home calls alarm_arm_home on the abode panel."""
        hass.states.async_set("alarm_control_panel.abode_alarm", "disarmed")

        calls = []

        async def mock_service(call):
            calls.append(call)

        hass.services.async_register(
            "alarm_control_panel", "alarm_arm_home", mock_service
        )

        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/modes/set",
                "mode_id": "home",
            }
        )
        response = await client.receive_json()

        assert response["success"]
        assert response["result"]["mode_id"] == "home"
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "alarm_control_panel.abode_alarm"

    async def test_ws_modes_set_away(self, hass, hass_ws_client) -> None:
        """Setting mode=away calls alarm_arm_away on the abode panel."""
        hass.states.async_set("alarm_control_panel.abode_alarm", "disarmed")

        calls = []

        async def mock_service(call):
            calls.append(call)

        hass.services.async_register(
            "alarm_control_panel", "alarm_arm_away", mock_service
        )

        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/modes/set",
                "mode_id": "away",
            }
        )
        response = await client.receive_json()

        assert response["success"]
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "alarm_control_panel.abode_alarm"

    async def test_ws_modes_set_standby(self, hass, hass_ws_client) -> None:
        """Setting mode=standby calls alarm_disarm on the abode panel."""
        hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")

        calls = []

        async def mock_service(call):
            calls.append(call)

        hass.services.async_register(
            "alarm_control_panel", "alarm_disarm", mock_service
        )

        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/modes/set",
                "mode_id": "standby",
            }
        )
        response = await client.receive_json()

        assert response["success"]
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "alarm_control_panel.abode_alarm"

    async def test_ws_modes_set_invalid_mode(self, hass, hass_ws_client) -> None:
        """Schema validation rejects unknown mode_id."""
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/modes/set",
                "mode_id": "intruder",
            }
        )
        response = await client.receive_json()

        assert not response["success"]
        # voluptuous schema validation surfaces as invalid_format
        assert response["error"]["code"] == "invalid_format"

    async def test_ws_modes_set_no_panel(self, hass, hass_ws_client) -> None:
        """No abode alarm_control_panel registered → not_found error."""
        # Intentionally no alarm_control_panel.abode_* state set.
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/modes/set",
                "mode_id": "home",
            }
        )
        response = await client.receive_json()

        assert not response["success"]
        assert response["error"]["code"] == "not_found"

    async def test_ws_modes_set_finds_renamed_entity_via_registry(
        self, hass, hass_ws_client
    ) -> None:
        """Renamed entity_id (e.g. alarm_control_panel.house) still resolves
        via entity registry lookup by platform=abode_security (#44).

        The pre-fix prefix heuristic (`startswith("alarm_control_panel.abode")`)
        misses any user-renamed entity. Registering with a non-standard entity_id
        in the entity registry simulates a rename: the registry entry retains
        platform=abode_security regardless of what the user renames it to.
        """
        registry = er.async_get(hass)
        # Register an Abode alarm panel under a non-prefix entity_id.
        registry.async_get_or_create(
            domain="alarm_control_panel",
            platform=DOMAIN,
            unique_id="abode-test-uid",
            suggested_object_id="house",  # → alarm_control_panel.house
        )
        hass.states.async_set("alarm_control_panel.house", "disarmed")

        calls = []

        async def mock_service(call):
            calls.append(call)

        hass.services.async_register(
            "alarm_control_panel", "alarm_arm_home", mock_service
        )

        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/modes/set",
                "mode_id": "home",
            }
        )
        response = await client.receive_json()

        assert response["success"]
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "alarm_control_panel.house"

    async def test_ws_modes_list_finds_renamed_entity_via_registry(
        self, hass, hass_ws_client
    ) -> None:
        """Active-mode flag must resolve correctly even after entity rename (#44)."""
        registry = er.async_get(hass)
        registry.async_get_or_create(
            domain="alarm_control_panel",
            platform=DOMAIN,
            unique_id="abode-test-uid-list",
            suggested_object_id="my_security_system",
        )
        hass.states.async_set("alarm_control_panel.my_security_system", "armed_home")

        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/modes/list"})
        response = await client.receive_json()

        assert response["success"]
        home_mode = next(m for m in response["result"]["modes"] if m["id"] == "home")
        assert home_mode["active"] is True


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

    async def test_ws_entities_sensors_includes_area_from_entity(
        self, hass, hass_ws_client
    ) -> None:
        """Sensor payload exposes the entity's area name (#120).

        The user couldn't tell from "Intrusion" alone which room/device a
        sensor came from. Surfacing the HA area gives the panel UI a hint
        to render next to the sensor name.
        """
        from homeassistant.helpers import area_registry as ar
        from homeassistant.helpers import entity_registry as er

        area_reg = ar.async_get(hass)
        area = area_reg.async_create("Living Room")

        entity_reg = er.async_get(hass)
        entity_reg.async_get_or_create(
            "binary_sensor",
            "abode",
            "front_door_sensor_unique",
            suggested_object_id="front_door",
        )
        entity_reg.async_update_entity("binary_sensor.front_door", area_id=area.id)

        hass.states.async_set(
            "binary_sensor.front_door",
            "off",
            {"device_class": "door", "friendly_name": "Front Door"},
        )

        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/entities/sensors"})
        response = await client.receive_json()

        assert response["success"]
        door = response["result"]["sensors"]["door"][0]
        assert door["area"] == "Living Room"

    async def test_ws_entities_sensors_falls_back_to_device_area(
        self, hass, hass_ws_client
    ) -> None:
        """When the entity has no area, fall back to its device's area (#120)."""
        from homeassistant.helpers import area_registry as ar
        from homeassistant.helpers import device_registry as dr
        from homeassistant.helpers import entity_registry as er

        area_reg = ar.async_get(hass)
        area = area_reg.async_create("Garage")

        # Register a config entry so device_registry has something to attach
        # the device to (HA requires it for async_get_or_create).
        from pytest_homeassistant_custom_component.common import MockConfigEntry

        mock_entry = MockConfigEntry(domain="abode_security", data={})
        mock_entry.add_to_hass(hass)

        device_reg = dr.async_get(hass)
        device = device_reg.async_get_or_create(
            config_entry_id=mock_entry.entry_id,
            identifiers={("abode_security", "garage-door-device")},
            name="Garage Door",
        )
        device_reg.async_update_device(device.id, area_id=area.id)

        entity_reg = er.async_get(hass)
        entity_reg.async_get_or_create(
            "binary_sensor",
            "abode",
            "garage_sensor_unique",
            suggested_object_id="garage",
            device_id=device.id,
        )

        hass.states.async_set(
            "binary_sensor.garage",
            "off",
            {"device_class": "door", "friendly_name": "Garage"},
        )

        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/entities/sensors"})
        response = await client.receive_json()

        assert response["success"]
        garage = response["result"]["sensors"]["door"][0]
        assert garage["area"] == "Garage"

    async def test_ws_entities_sensors_area_is_null_when_unassigned(
        self, hass, hass_ws_client
    ) -> None:
        """Sensors without entity- or device-level area report `area: None` (#120)."""
        hass.states.async_set(
            "binary_sensor.unregistered_door",
            "off",
            {"device_class": "door", "friendly_name": "Unregistered"},
        )

        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/entities/sensors"})
        response = await client.receive_json()

        assert response["success"]
        door = response["result"]["sensors"]["door"][0]
        assert door["area"] is None

    @pytest.mark.parametrize(
        "hider",
        [
            er.RegistryEntryHider.USER,
            er.RegistryEntryHider.INTEGRATION,
        ],
    )
    async def test_ws_entities_sensors_omits_hidden_entities(
        self, hass, hass_ws_client, hider
    ) -> None:
        """Sensors hidden in the entity registry must not surface in the picker.

        The picker is the only place users discover sensors to wire
        into actions; surfacing a hidden one re-introduces the same
        trap as the original "Home Test" bug — a sensor that looks
        pickable but won't fire reliably (the user hid it for a
        reason). Disabled entities are already excluded since they
        don't get a state at all; this test covers the hidden case.

        Parametrized across `RegistryEntryHider` variants so a future
        refactor that narrows the predicate to e.g. `hidden_by ==
        USER` (instead of the documented `is not None`) breaks the
        INTEGRATION arm loudly.
        """
        entity_reg = er.async_get(hass)

        # Visible sensor — should appear in the response.
        entity_reg.async_get_or_create(
            "binary_sensor",
            "abode",
            "visible_unique",
            suggested_object_id="visible",
        )
        hass.states.async_set(
            "binary_sensor.visible",
            "off",
            {"device_class": "door", "friendly_name": "Visible"},
        )

        # Hidden sensor — should be filtered out regardless of which
        # actor hid it (user via entity-settings, or an integration
        # marking the entity diagnostic). Source code checks
        # `hidden_by is not None`, so every non-None hider hits the
        # same skip branch.
        entity_reg.async_get_or_create(
            "binary_sensor",
            "abode",
            "hidden_unique",
            suggested_object_id="hidden",
        )
        entity_reg.async_update_entity(
            "binary_sensor.hidden",
            hidden_by=hider,
        )
        hass.states.async_set(
            "binary_sensor.hidden",
            "off",
            {"device_class": "door", "friendly_name": "Hidden"},
        )

        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/entities/sensors"})
        response = await client.receive_json()

        assert response["success"]
        door_entity_ids = [
            s["entity_id"] for s in response["result"]["sensors"]["door"]
        ]
        assert "binary_sensor.visible" in door_entity_ids
        assert "binary_sensor.hidden" not in door_entity_ids


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
