"""Action management for Abode Security custom automation rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from homeassistant.helpers.storage import Store

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

STORAGE_KEY = "abode_security_actions"
STORAGE_VERSION = 1


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


class ActionStore:
    """Persistent storage for AbodeAction configurations.

    Uses Home Assistant's Store API for JSON-based persistence.
    Storage file: .storage/abode_security_actions.json
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the action store."""
        self._hass = hass
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._actions: dict[str, AbodeAction] = {}

    async def async_load(self) -> None:
        """Load actions from storage.

        Handles missing file by initializing empty dict.
        """
        data = await self._store.async_load()
        if data is None:
            self._actions = {}
            return

        actions_data = data.get("actions", {})
        self._actions = {
            action_id: AbodeAction.from_dict(action_dict)
            for action_id, action_dict in actions_data.items()
        }

    async def async_save(self) -> None:
        """Save all actions to storage."""
        data = {
            "actions": {
                action_id: action.to_dict()
                for action_id, action in self._actions.items()
            }
        }
        await self._store.async_save(data)

    async def async_add(self, action: AbodeAction) -> None:
        """Add an action to the store and persist."""
        self._actions[action.id] = action
        await self.async_save()

    async def async_remove(self, action_id: str) -> bool:
        """Remove an action from the store.

        Returns True if removed, False if not found.
        """
        if action_id not in self._actions:
            return False
        del self._actions[action_id]
        await self.async_save()
        return True

    def get(self, action_id: str) -> AbodeAction | None:
        """Get an action by ID from cache."""
        return self._actions.get(action_id)

    def get_all(self) -> list[AbodeAction]:
        """Get all actions as a list."""
        return list(self._actions.values())
