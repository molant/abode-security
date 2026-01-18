"""Tests for the action manager module."""

from datetime import UTC, datetime

from custom_components.abode_security.action_manager import AbodeAction


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
