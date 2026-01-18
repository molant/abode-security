"""Action management for Abode Security custom automation rules."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from homeassistant.helpers.storage import Store

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY = "abode_security_actions"
STORAGE_VERSION = 1
VALID_MODES = {"standby", "home", "away"}


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


class ActionManager:
    """Manager for CRUD operations on AbodeAction configurations.

    Provides validation, entity existence warnings, and persistence.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the action manager."""
        self._hass = hass
        self._store = ActionStore(hass)

    async def async_setup(self) -> None:
        """Set up the action manager by loading the store."""
        await self._store.async_load()

    def _validate_action(
        self,
        name: str,
        modes: list[str],
        sensor_entity_ids: list[str],
        alarm_entity_ids: list[str],
        delay_seconds: int,
    ) -> None:
        """Validate action fields. Raises ValueError if invalid."""
        # Validate name
        if not name or not name.strip():
            raise ValueError("Action name cannot be empty")
        if len(name) > 100:
            raise ValueError("Action name cannot exceed 100 characters")

        # Validate modes
        if not modes:
            raise ValueError("At least one mode must be specified")
        for mode in modes:
            if mode not in VALID_MODES:
                raise ValueError(
                    f"Invalid mode '{mode}'. Valid modes: {', '.join(VALID_MODES)}"
                )

        # Validate entity IDs
        if not sensor_entity_ids:
            raise ValueError("At least one sensor entity ID must be specified")
        if not alarm_entity_ids:
            raise ValueError("At least one alarm entity ID must be specified")

        # Validate delay
        if delay_seconds < 0 or delay_seconds > 60:
            raise ValueError("delay_seconds must be between 0 and 60")

    def _warn_missing_entities(
        self,
        sensor_entity_ids: list[str],
        alarm_entity_ids: list[str],
    ) -> None:
        """Log warnings for entities that don't exist in hass.states."""
        for entity_id in sensor_entity_ids:
            if self._hass.states.get(entity_id) is None:
                _LOGGER.warning(
                    "Entity %s not found, action may not trigger correctly", entity_id
                )
        for entity_id in alarm_entity_ids:
            if self._hass.states.get(entity_id) is None:
                _LOGGER.warning(
                    "Entity %s not found, action may not trigger correctly", entity_id
                )

    async def async_create(
        self,
        name: str,
        modes: list[str],
        sensor_entity_ids: list[str],
        alarm_entity_ids: list[str],
        delay_seconds: int = 0,
    ) -> AbodeAction:
        """Create a new action with validation.

        Args:
            name: User-friendly name for the action
            modes: List of modes when action should be active
            sensor_entity_ids: List of sensor entity IDs to monitor
            alarm_entity_ids: List of alarm entity IDs to trigger
            delay_seconds: Delay before triggering (0-60)

        Returns:
            The created AbodeAction

        Raises:
            ValueError: If validation fails
        """
        self._validate_action(
            name, modes, sensor_entity_ids, alarm_entity_ids, delay_seconds
        )
        self._warn_missing_entities(sensor_entity_ids, alarm_entity_ids)

        action = AbodeAction(
            id=str(uuid.uuid4()),
            name=name,
            modes=modes,
            sensor_entity_ids=sensor_entity_ids,
            alarm_entity_ids=alarm_entity_ids,
            delay_seconds=delay_seconds,
        )
        await self._store.async_add(action)
        return action

    async def async_get(self, action_id: str) -> AbodeAction | None:
        """Get an action by ID."""
        return self._store.get(action_id)

    async def async_get_all(self) -> list[AbodeAction]:
        """Get all actions."""
        return self._store.get_all()

    async def async_update(self, action_id: str, **kwargs) -> AbodeAction | None:
        """Update an action with the provided fields.

        Args:
            action_id: ID of the action to update
            **kwargs: Fields to update (name, modes, sensor_entity_ids,
                      alarm_entity_ids, delay_seconds, enabled)

        Returns:
            The updated AbodeAction, or None if not found

        Raises:
            ValueError: If validation fails after applying changes
        """
        action = self._store.get(action_id)
        if action is None:
            return None

        # Build updated values
        name = kwargs.get("name", action.name)
        modes = kwargs.get("modes", action.modes)
        sensor_entity_ids = kwargs.get("sensor_entity_ids", action.sensor_entity_ids)
        alarm_entity_ids = kwargs.get("alarm_entity_ids", action.alarm_entity_ids)
        delay_seconds = kwargs.get("delay_seconds", action.delay_seconds)
        enabled = kwargs.get("enabled", action.enabled)

        # Validate the updated values
        self._validate_action(
            name, modes, sensor_entity_ids, alarm_entity_ids, delay_seconds
        )
        self._warn_missing_entities(sensor_entity_ids, alarm_entity_ids)

        # Create updated action
        updated_action = AbodeAction(
            id=action.id,
            name=name,
            modes=modes,
            sensor_entity_ids=sensor_entity_ids,
            alarm_entity_ids=alarm_entity_ids,
            enabled=enabled,
            delay_seconds=delay_seconds,
            last_triggered=action.last_triggered,
            trigger_count=action.trigger_count,
        )
        await self._store.async_add(updated_action)
        return updated_action

    async def async_delete(self, action_id: str) -> bool:
        """Delete an action.

        Returns True if deleted, False if not found.
        """
        return await self._store.async_remove(action_id)

    async def async_get_by_mode(self, mode: str) -> list[AbodeAction]:
        """Get enabled actions that include the given mode.

        Args:
            mode: The mode to filter by (standby, home, or away)

        Returns:
            List of enabled actions that include the mode
        """
        return [
            action
            for action in self._store.get_all()
            if action.enabled and mode in action.modes
        ]

    async def async_get_enabled(self) -> list[AbodeAction]:
        """Get all enabled actions."""
        return [action for action in self._store.get_all() if action.enabled]

    async def async_toggle(self, action_id: str) -> AbodeAction | None:
        """Toggle an action's enabled state.

        Returns the updated action, or None if not found.
        """
        action = self._store.get(action_id)
        if action is None:
            return None

        return await self.async_update(action_id, enabled=not action.enabled)

    async def async_record_trigger(self, action_id: str) -> None:
        """Record that an action was triggered.

        Updates last_triggered to current UTC time and increments trigger_count.
        """
        action = self._store.get(action_id)
        if action is None:
            return

        updated_action = AbodeAction(
            id=action.id,
            name=action.name,
            modes=action.modes,
            sensor_entity_ids=action.sensor_entity_ids,
            alarm_entity_ids=action.alarm_entity_ids,
            enabled=action.enabled,
            delay_seconds=action.delay_seconds,
            last_triggered=datetime.now(UTC),
            trigger_count=action.trigger_count + 1,
        )
        await self._store.async_add(updated_action)
