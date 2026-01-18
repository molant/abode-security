"""Tests for the action manager module."""

from datetime import UTC, datetime

import pytest

from custom_components.abode_security.action_manager import (
    AbodeAction,
    ActionManager,
    ActionStore,
)


class TestAbodeAction:
    """Tests for AbodeAction dataclass."""

    def test_action_creation_defaults(self) -> None:
        """Test AbodeAction creation with default values."""
        action = AbodeAction(
            id="uuid-1",
            name="Test Action",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        assert action.enabled is True
        assert action.delay_seconds == 0
        assert action.last_triggered is None
        assert action.trigger_count == 0

    def test_action_creation_all_fields(self) -> None:
        """Test AbodeAction creation with all fields specified."""
        now = datetime.now(UTC)
        action = AbodeAction(
            id="uuid-2",
            name="Full Action",
            modes=["home", "away"],
            sensor_entity_ids=["binary_sensor.door", "binary_sensor.window"],
            alarm_entity_ids=["switch.panic_alarm", "switch.fire_alarm"],
            enabled=False,
            delay_seconds=30,
            last_triggered=now,
            trigger_count=5,
        )
        assert action.id == "uuid-2"
        assert action.name == "Full Action"
        assert action.modes == ["home", "away"]
        assert action.sensor_entity_ids == [
            "binary_sensor.door",
            "binary_sensor.window",
        ]
        assert action.alarm_entity_ids == ["switch.panic_alarm", "switch.fire_alarm"]
        assert action.enabled is False
        assert action.delay_seconds == 30
        assert action.last_triggered == now
        assert action.trigger_count == 5

    def test_action_to_dict(self) -> None:
        """Test AbodeAction serialization to dict."""
        action = AbodeAction(
            id="uuid-1",
            name="Test Action",
            modes=["home", "away"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        d = action.to_dict()
        assert d["id"] == "uuid-1"
        assert d["name"] == "Test Action"
        assert isinstance(d["modes"], list)
        assert d["modes"] == ["home", "away"]
        assert d["sensor_entity_ids"] == ["binary_sensor.door"]
        assert d["alarm_entity_ids"] == ["switch.panic_alarm"]
        assert d["enabled"] is True
        assert d["delay_seconds"] == 0
        assert d["last_triggered"] is None
        assert d["trigger_count"] == 0

    def test_action_to_dict_with_datetime(self) -> None:
        """Test AbodeAction serialization with datetime converts to ISO format."""
        now = datetime.now(UTC)
        action = AbodeAction(
            id="uuid-1",
            name="Test Action",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
            last_triggered=now,
        )
        d = action.to_dict()
        assert isinstance(d["last_triggered"], str)
        assert d["last_triggered"] == now.isoformat()

    def test_action_from_dict(self) -> None:
        """Test AbodeAction deserialization from dict."""
        d = {
            "id": "uuid-1",
            "name": "Test Action",
            "modes": ["home", "away"],
            "sensor_entity_ids": ["binary_sensor.door"],
            "alarm_entity_ids": ["switch.panic_alarm"],
            "enabled": True,
            "delay_seconds": 10,
            "last_triggered": None,
            "trigger_count": 3,
        }
        action = AbodeAction.from_dict(d)
        assert action.id == "uuid-1"
        assert action.name == "Test Action"
        assert action.modes == ["home", "away"]
        assert action.sensor_entity_ids == ["binary_sensor.door"]
        assert action.alarm_entity_ids == ["switch.panic_alarm"]
        assert action.enabled is True
        assert action.delay_seconds == 10
        assert action.last_triggered is None
        assert action.trigger_count == 3

    def test_action_from_dict_with_datetime_string(self) -> None:
        """Test AbodeAction deserialization parses ISO datetime string."""
        now = datetime.now(UTC)
        d = {
            "id": "uuid-1",
            "name": "Test Action",
            "modes": ["home"],
            "sensor_entity_ids": ["binary_sensor.door"],
            "alarm_entity_ids": ["switch.panic_alarm"],
            "enabled": True,
            "delay_seconds": 0,
            "last_triggered": now.isoformat(),
            "trigger_count": 0,
        }
        action = AbodeAction.from_dict(d)
        assert action.last_triggered is not None
        assert isinstance(action.last_triggered, datetime)
        # Compare timestamps (allowing for microsecond precision differences)
        assert abs((action.last_triggered - now).total_seconds()) < 0.001

    def test_action_round_trip(self) -> None:
        """Test AbodeAction serialization round-trip (to_dict then from_dict)."""
        now = datetime.now(UTC)
        original = AbodeAction(
            id="uuid-roundtrip",
            name="Roundtrip Test",
            modes=["standby", "home", "away"],
            sensor_entity_ids=["binary_sensor.door", "binary_sensor.motion"],
            alarm_entity_ids=["switch.panic_alarm"],
            enabled=False,
            delay_seconds=45,
            last_triggered=now,
            trigger_count=10,
        )
        restored = AbodeAction.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.modes == original.modes
        assert restored.sensor_entity_ids == original.sensor_entity_ids
        assert restored.alarm_entity_ids == original.alarm_entity_ids
        assert restored.enabled == original.enabled
        assert restored.delay_seconds == original.delay_seconds
        assert restored.trigger_count == original.trigger_count
        # Compare timestamps
        assert original.last_triggered is not None
        assert restored.last_triggered is not None
        assert (
            abs((restored.last_triggered - original.last_triggered).total_seconds())
            < 0.001
        )


@pytest.mark.usefixtures("mock_abode")
class TestActionStore:
    """Tests for ActionStore class."""

    async def test_store_init(self, hass) -> None:
        """Test ActionStore initialization and loading empty store."""
        store = ActionStore(hass)
        await store.async_load()
        assert store.get_all() == []

    async def test_store_add_and_get(self, hass) -> None:
        """Test adding an action and retrieving it."""
        store = ActionStore(hass)
        await store.async_load()

        action = AbodeAction(
            id="test-1",
            name="Test Action",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        await store.async_add(action)

        retrieved = store.get("test-1")
        assert retrieved is not None
        assert retrieved.id == "test-1"
        assert retrieved.name == "Test Action"

    async def test_store_persistence(self, hass) -> None:
        """Test that actions persist across store instances."""
        # First store instance - add an action
        store1 = ActionStore(hass)
        await store1.async_load()

        action = AbodeAction(
            id="persist-1",
            name="Persistent Action",
            modes=["away"],
            sensor_entity_ids=["binary_sensor.motion"],
            alarm_entity_ids=["switch.fire_alarm"],
        )
        await store1.async_add(action)

        # Second store instance - should load the same action
        store2 = ActionStore(hass)
        await store2.async_load()

        retrieved = store2.get("persist-1")
        assert retrieved is not None
        assert retrieved.name == "Persistent Action"

    async def test_store_remove(self, hass) -> None:
        """Test removing an action."""
        store = ActionStore(hass)
        await store.async_load()

        action = AbodeAction(
            id="remove-1",
            name="To Remove",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        await store.async_add(action)
        assert store.get("remove-1") is not None

        result = await store.async_remove("remove-1")
        assert result is True
        assert store.get("remove-1") is None

    async def test_store_remove_not_found(self, hass) -> None:
        """Test removing a non-existent action returns False."""
        store = ActionStore(hass)
        await store.async_load()

        result = await store.async_remove("non-existent")
        assert result is False

    async def test_store_get_all(self, hass) -> None:
        """Test getting all actions as a list."""
        store = ActionStore(hass)
        await store.async_load()

        action1 = AbodeAction(
            id="list-1",
            name="Action 1",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        action2 = AbodeAction(
            id="list-2",
            name="Action 2",
            modes=["away"],
            sensor_entity_ids=["binary_sensor.motion"],
            alarm_entity_ids=["switch.fire_alarm"],
        )
        await store.async_add(action1)
        await store.async_add(action2)

        all_actions = store.get_all()
        assert len(all_actions) == 2
        assert isinstance(all_actions, list)
        action_ids = [a.id for a in all_actions]
        assert "list-1" in action_ids
        assert "list-2" in action_ids


@pytest.mark.usefixtures("mock_abode")
class TestActionManager:
    """Tests for ActionManager class."""

    # --- Sub-Phase A: Core CRUD ---

    async def test_manager_create_valid(self, hass) -> None:
        """Test creating an action with valid data."""
        manager = ActionManager(hass)
        await manager.async_setup()

        action = await manager.async_create(
            name="Motion Alert",
            modes=["away"],
            sensor_entity_ids=["binary_sensor.motion"],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        assert action.id is not None
        assert action.name == "Motion Alert"
        assert action.modes == ["away"]
        assert action.enabled is True

    async def test_manager_create_empty_name(self, hass) -> None:
        """Test creating action with empty name raises ValueError."""
        manager = ActionManager(hass)
        await manager.async_setup()

        with pytest.raises(ValueError, match="name"):
            await manager.async_create(
                name="",
                modes=["home"],
                sensor_entity_ids=["binary_sensor.door"],
                alarm_entity_ids=["switch.panic_alarm"],
            )

    async def test_manager_create_whitespace_name(self, hass) -> None:
        """Test creating action with whitespace-only name raises ValueError."""
        manager = ActionManager(hass)
        await manager.async_setup()

        with pytest.raises(ValueError, match="name"):
            await manager.async_create(
                name="   ",
                modes=["home"],
                sensor_entity_ids=["binary_sensor.door"],
                alarm_entity_ids=["switch.panic_alarm"],
            )

    async def test_manager_create_name_too_long(self, hass) -> None:
        """Test creating action with name over 100 chars raises ValueError."""
        manager = ActionManager(hass)
        await manager.async_setup()

        with pytest.raises(ValueError, match="name"):
            await manager.async_create(
                name="x" * 101,
                modes=["home"],
                sensor_entity_ids=["binary_sensor.door"],
                alarm_entity_ids=["switch.panic_alarm"],
            )

    async def test_manager_create_empty_modes(self, hass) -> None:
        """Test creating action with empty modes raises ValueError."""
        manager = ActionManager(hass)
        await manager.async_setup()

        with pytest.raises(ValueError, match="mode"):
            await manager.async_create(
                name="Test",
                modes=[],
                sensor_entity_ids=["binary_sensor.door"],
                alarm_entity_ids=["switch.panic_alarm"],
            )

    async def test_manager_create_invalid_mode(self, hass) -> None:
        """Test creating action with invalid mode raises ValueError."""
        manager = ActionManager(hass)
        await manager.async_setup()

        with pytest.raises(ValueError, match="mode"):
            await manager.async_create(
                name="Test",
                modes=["invalid"],
                sensor_entity_ids=["binary_sensor.door"],
                alarm_entity_ids=["switch.panic_alarm"],
            )

    async def test_manager_create_empty_sensors(self, hass) -> None:
        """Test creating action with empty sensors raises ValueError."""
        manager = ActionManager(hass)
        await manager.async_setup()

        with pytest.raises(ValueError, match="sensor"):
            await manager.async_create(
                name="Test",
                modes=["home"],
                sensor_entity_ids=[],
                alarm_entity_ids=["switch.panic_alarm"],
            )

    async def test_manager_create_empty_alarms(self, hass) -> None:
        """Test creating action with empty alarms raises ValueError."""
        manager = ActionManager(hass)
        await manager.async_setup()

        with pytest.raises(ValueError, match="alarm"):
            await manager.async_create(
                name="Test",
                modes=["home"],
                sensor_entity_ids=["binary_sensor.door"],
                alarm_entity_ids=[],
            )

    async def test_manager_create_invalid_delay(self, hass) -> None:
        """Test creating action with delay > 60 raises ValueError."""
        manager = ActionManager(hass)
        await manager.async_setup()

        with pytest.raises(ValueError, match="delay"):
            await manager.async_create(
                name="Test",
                modes=["home"],
                sensor_entity_ids=["binary_sensor.door"],
                alarm_entity_ids=["switch.panic_alarm"],
                delay_seconds=100,
            )

    async def test_manager_create_negative_delay(self, hass) -> None:
        """Test creating action with negative delay raises ValueError."""
        manager = ActionManager(hass)
        await manager.async_setup()

        with pytest.raises(ValueError, match="delay"):
            await manager.async_create(
                name="Test",
                modes=["home"],
                sensor_entity_ids=["binary_sensor.door"],
                alarm_entity_ids=["switch.panic_alarm"],
                delay_seconds=-1,
            )

    async def test_manager_create_missing_entity_warning(self, hass, caplog) -> None:
        """Test creating action with non-existent entity logs warning."""
        manager = ActionManager(hass)
        await manager.async_setup()

        # Entity doesn't exist in hass.states
        action = await manager.async_create(
            name="Test",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.nonexistent"],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        # Should succeed but log warning
        assert action is not None
        assert "not found" in caplog.text

    async def test_manager_get(self, hass) -> None:
        """Test getting an action by ID."""
        manager = ActionManager(hass)
        await manager.async_setup()

        created = await manager.async_create(
            name="Test",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        retrieved = await manager.async_get(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name

    async def test_manager_get_not_found(self, hass) -> None:
        """Test getting a non-existent action returns None."""
        manager = ActionManager(hass)
        await manager.async_setup()

        result = await manager.async_get("non-existent")
        assert result is None

    async def test_manager_get_all(self, hass) -> None:
        """Test getting all actions."""
        manager = ActionManager(hass)
        await manager.async_setup()

        await manager.async_create(
            name="Action 1",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        await manager.async_create(
            name="Action 2",
            modes=["away"],
            sensor_entity_ids=["binary_sensor.motion"],
            alarm_entity_ids=["switch.fire_alarm"],
        )

        all_actions = await manager.async_get_all()
        assert len(all_actions) == 2

    async def test_manager_update(self, hass) -> None:
        """Test updating an action."""
        manager = ActionManager(hass)
        await manager.async_setup()

        action = await manager.async_create(
            name="Original",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        updated = await manager.async_update(action.id, name="Updated")
        assert updated is not None
        assert updated.name == "Updated"
        assert updated.id == action.id

    async def test_manager_update_partial(self, hass) -> None:
        """Test updating only some fields of an action."""
        manager = ActionManager(hass)
        await manager.async_setup()

        action = await manager.async_create(
            name="Test",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        updated = await manager.async_update(action.id, modes=["home", "away"])
        assert updated is not None
        assert updated.name == "Test"  # unchanged
        assert updated.modes == ["home", "away"]

    async def test_manager_update_not_found(self, hass) -> None:
        """Test updating a non-existent action returns None."""
        manager = ActionManager(hass)
        await manager.async_setup()

        result = await manager.async_update("non-existent", name="New")
        assert result is None

    async def test_manager_update_validation_error(self, hass) -> None:
        """Test updating an action with invalid data raises ValueError."""
        manager = ActionManager(hass)
        await manager.async_setup()

        action = await manager.async_create(
            name="Test",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        with pytest.raises(ValueError):
            await manager.async_update(action.id, name="")

    async def test_manager_delete(self, hass) -> None:
        """Test deleting an action."""
        manager = ActionManager(hass)
        await manager.async_setup()

        action = await manager.async_create(
            name="To Delete",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        result = await manager.async_delete(action.id)
        assert result is True
        assert await manager.async_get(action.id) is None

    async def test_manager_delete_not_found(self, hass) -> None:
        """Test deleting a non-existent action returns False."""
        manager = ActionManager(hass)
        await manager.async_setup()

        result = await manager.async_delete("non-existent")
        assert result is False

    # --- Sub-Phase B: Helper Methods ---

    async def test_manager_get_by_mode(self, hass) -> None:
        """Test getting actions by mode."""
        manager = ActionManager(hass)
        await manager.async_setup()

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
        await manager.async_create(
            name="Both Action",
            modes=["home", "away"],
            sensor_entity_ids=["binary_sensor.window"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        home_actions = await manager.async_get_by_mode("home")
        assert len(home_actions) == 2

        away_actions = await manager.async_get_by_mode("away")
        assert len(away_actions) == 2

    async def test_manager_get_by_mode_excludes_disabled(self, hass) -> None:
        """Test get_by_mode excludes disabled actions."""
        manager = ActionManager(hass)
        await manager.async_setup()

        action = await manager.async_create(
            name="Test",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        await manager.async_update(action.id, enabled=False)

        home_actions = await manager.async_get_by_mode("home")
        assert len(home_actions) == 0

    async def test_manager_get_enabled(self, hass) -> None:
        """Test getting only enabled actions."""
        manager = ActionManager(hass)
        await manager.async_setup()

        await manager.async_create(
            name="Enabled",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        action2 = await manager.async_create(
            name="To Disable",
            modes=["away"],
            sensor_entity_ids=["binary_sensor.motion"],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        await manager.async_update(action2.id, enabled=False)

        enabled = await manager.async_get_enabled()
        assert len(enabled) == 1
        assert enabled[0].name == "Enabled"

    async def test_manager_toggle(self, hass) -> None:
        """Test toggling an action's enabled state."""
        manager = ActionManager(hass)
        await manager.async_setup()

        action = await manager.async_create(
            name="Test",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        assert action.enabled is True

        toggled = await manager.async_toggle(action.id)
        assert toggled is not None
        assert toggled.enabled is False

        toggled_again = await manager.async_toggle(action.id)
        assert toggled_again is not None
        assert toggled_again.enabled is True

    async def test_manager_toggle_not_found(self, hass) -> None:
        """Test toggling a non-existent action returns None."""
        manager = ActionManager(hass)
        await manager.async_setup()

        result = await manager.async_toggle("non-existent")
        assert result is None

    async def test_manager_record_trigger(self, hass) -> None:
        """Test recording a trigger updates timestamp and count."""
        manager = ActionManager(hass)
        await manager.async_setup()

        action = await manager.async_create(
            name="Test",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )
        assert action.last_triggered is None
        assert action.trigger_count == 0

        await manager.async_record_trigger(action.id)

        updated = await manager.async_get(action.id)
        assert updated is not None
        assert updated.last_triggered is not None
        assert updated.trigger_count == 1

    async def test_manager_record_trigger_increments(self, hass) -> None:
        """Test recording multiple triggers increments count."""
        manager = ActionManager(hass)
        await manager.async_setup()

        action = await manager.async_create(
            name="Test",
            modes=["home"],
            sensor_entity_ids=["binary_sensor.door"],
            alarm_entity_ids=["switch.panic_alarm"],
        )

        await manager.async_record_trigger(action.id)
        await manager.async_record_trigger(action.id)
        await manager.async_record_trigger(action.id)

        updated = await manager.async_get(action.id)
        assert updated is not None
        assert updated.trigger_count == 3

    async def test_manager_record_trigger_not_found(self, hass) -> None:
        """Test recording trigger for non-existent action does nothing."""
        manager = ActionManager(hass)
        await manager.async_setup()

        # Should not raise, just silently return
        await manager.async_record_trigger("non-existent")
