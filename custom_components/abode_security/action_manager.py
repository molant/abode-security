"""Action management for Abode Security custom automation rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class AbodeAction:
    """Represents a custom automation action for Abode Security.

    Actions define rules for triggering alarm switches when specific sensors
    activate while in specific alarm modes (standby, home, away).
    """

    id: str
    name: str
    modes: list[str]
    sensor_entity_ids: list[str]
    alarm_entity_ids: list[str]
    enabled: bool = True
    delay_seconds: int = 0
    last_triggered: datetime | None = None
    trigger_count: int = 0

    def to_dict(self) -> dict:
        """Serialize action to dictionary for JSON storage.

        Converts datetime to ISO format string.
        """
        return {
            "id": self.id,
            "name": self.name,
            "modes": self.modes,
            "sensor_entity_ids": self.sensor_entity_ids,
            "alarm_entity_ids": self.alarm_entity_ids,
            "enabled": self.enabled,
            "delay_seconds": self.delay_seconds,
            "last_triggered": self.last_triggered.isoformat()
            if self.last_triggered
            else None,
            "trigger_count": self.trigger_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AbodeAction:
        """Deserialize action from dictionary.

        Parses ISO format string back to datetime.
        """
        last_triggered = data.get("last_triggered")
        if last_triggered is not None and isinstance(last_triggered, str):
            last_triggered = datetime.fromisoformat(last_triggered)

        return cls(
            id=data["id"],
            name=data["name"],
            modes=data["modes"],
            sensor_entity_ids=data["sensor_entity_ids"],
            alarm_entity_ids=data["alarm_entity_ids"],
            enabled=data.get("enabled", True),
            delay_seconds=data.get("delay_seconds", 0),
            last_triggered=last_triggered,
            trigger_count=data.get("trigger_count", 0),
        )
