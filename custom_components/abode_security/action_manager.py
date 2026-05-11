"""Action management for Abode Security custom automation rules."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.storage import Store

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .action_trigger import ActionTriggerCoordinator

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY = "abode_security_actions"
STORAGE_VERSION = 1
VALID_MODES = {"standby", "home", "away"}

REPAIR_ISSUE_CORRUPT_ACTIONS = "corrupt_action_records"
MAX_DELAY_SECONDS = 60
MAX_NAME_LENGTH = 100


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
    def from_dict(cls, data: Any) -> AbodeAction:
        """Deserialize and validate an action from a raw dict.

        Raises ``ValueError`` with a field-specific message if the record is
        structurally invalid (missing key, wrong type, out-of-range value, or
        unparseable ``last_triggered``). Callers in load paths should treat a
        ``ValueError`` as "skip this record, keep loading the rest"; see
        ``ActionStore.async_load``.
        """
        if not isinstance(data, dict):
            raise ValueError("record must be a dict")

        action_id = data.get("id")
        if not isinstance(action_id, str) or not action_id:
            raise ValueError("id must be a non-empty string")

        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")

        modes = data.get("modes")
        if (
            not isinstance(modes, list)
            or not modes
            or not all(isinstance(m, str) for m in modes)
        ):
            raise ValueError("modes must be a non-empty list of strings")
        invalid_modes = [m for m in modes if m not in VALID_MODES]
        if invalid_modes:
            raise ValueError(
                f"modes contains invalid value(s) {invalid_modes!r}; "
                f"valid modes are {sorted(VALID_MODES)!r}"
            )

        sensors = data.get("sensor_entity_ids")
        if (
            not isinstance(sensors, list)
            or not sensors
            or not all(isinstance(s, str) for s in sensors)
        ):
            raise ValueError("sensor_entity_ids must be a non-empty list of strings")

        alarms = data.get("alarm_entity_ids")
        if (
            not isinstance(alarms, list)
            or not alarms
            or not all(isinstance(a, str) for a in alarms)
        ):
            raise ValueError("alarm_entity_ids must be a non-empty list of strings")

        enabled = data.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be a boolean")

        delay_seconds = data.get("delay_seconds", 0)
        # ``bool`` is a subclass of ``int``; exclude it explicitly so a stored
        # ``True``/``False`` does not pass the range check.
        if (
            not isinstance(delay_seconds, int)
            or isinstance(delay_seconds, bool)
            or delay_seconds < 0
            or delay_seconds > MAX_DELAY_SECONDS
        ):
            raise ValueError(
                f"delay_seconds must be an int in [0, {MAX_DELAY_SECONDS}]"
            )

        trigger_count = data.get("trigger_count", 0)
        if (
            not isinstance(trigger_count, int)
            or isinstance(trigger_count, bool)
            or trigger_count < 0
        ):
            raise ValueError("trigger_count must be a non-negative int")

        raw_last_triggered = data.get("last_triggered")
        last_triggered: datetime | None
        if raw_last_triggered is None:
            last_triggered = None
        elif isinstance(raw_last_triggered, str):
            try:
                last_triggered = datetime.fromisoformat(raw_last_triggered)
            except ValueError as exc:
                raise ValueError(
                    f"last_triggered is not a valid ISO 8601 string: {exc}"
                ) from exc
        else:
            raise ValueError("last_triggered must be null or an ISO 8601 string")

        return cls(
            id=action_id,
            name=name,
            modes=modes,
            sensor_entity_ids=sensors,
            alarm_entity_ids=alarms,
            enabled=enabled,
            delay_seconds=delay_seconds,
            last_triggered=last_triggered,
            trigger_count=trigger_count,
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
        """Load actions from storage, skipping individually corrupt records.

        A single bad record (missing key, wrong type, duplicate id, hand-edit,
        partial write) must not lose the rest of the user's actions or crash
        integration setup. Each record is validated independently via
        :meth:`AbodeAction.from_dict`. Bad records are logged at WARNING and
        skipped. If anything was dropped, a Home Assistant repair issue is
        raised so the user can see and resolve it; a subsequent clean load
        clears the issue automatically.
        """
        # Always start from a clean slate — any prior in-memory state is
        # superseded by what's on disk now.
        self._actions = {}

        whole_file_corrupt = False
        dropped = 0
        loaded: dict[str, AbodeAction] = {}

        data = await self._store.async_load()
        if data is not None and not isinstance(data, dict):
            _LOGGER.warning(
                "Action storage root is not a dict (%s); ignoring all records",
                type(data).__name__,
            )
            whole_file_corrupt = True
        elif data is not None:
            actions_data = data.get("actions", {})
            if not isinstance(actions_data, dict):
                _LOGGER.warning(
                    "Action storage 'actions' is not a dict (%s); ignoring all records",
                    type(actions_data).__name__,
                )
                whole_file_corrupt = True
            else:
                for key, raw in actions_data.items():
                    try:
                        action = AbodeAction.from_dict(raw)
                    except (ValueError, TypeError) as exc:
                        record_id = raw.get("id") if isinstance(raw, dict) else None
                        # First arg is the record's own id when present, else
                        # the storage map key — both refer to the same record.
                        _LOGGER.warning(
                            "Dropping corrupt action record %s: %s",
                            record_id or key,
                            exc,
                        )
                        dropped += 1
                        continue

                    if action.id in loaded:
                        _LOGGER.warning(
                            "Dropping duplicate action id %s (record key %s); "
                            "keeping first",
                            action.id,
                            key,
                        )
                        dropped += 1
                        continue

                    loaded[action.id] = action

        self._actions = loaded
        if whole_file_corrupt:
            self._raise_corrupt_issue(count=None)
        elif dropped:
            self._raise_corrupt_issue(count=dropped)
        else:
            # Only clear the prior repair issue once we know the current load
            # is clean — avoids momentarily exposing a "cleared" state if a
            # future caller awaits inside this method between the two writes.
            ir.async_delete_issue(self._hass, DOMAIN, REPAIR_ISSUE_CORRUPT_ACTIONS)

    def _raise_corrupt_issue(self, count: int | None) -> None:
        """Create the repair issue.

        ``count`` is the number of per-record drops, or ``None`` if the whole
        file was unreadable (root not a dict, ``actions`` not a dict) and a
        count can't be derived — surfaced to the user as ``"unknown"``.
        """
        ir.async_create_issue(
            self._hass,
            DOMAIN,
            REPAIR_ISSUE_CORRUPT_ACTIONS,
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key=REPAIR_ISSUE_CORRUPT_ACTIONS,
            translation_placeholders={
                "count": str(count) if count is not None else "unknown"
            },
        )

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
        self._trigger_coordinator: ActionTriggerCoordinator | None = None

    async def async_setup(self) -> None:
        """Set up the action manager by loading the store."""
        await self._store.async_load()

    def set_trigger_coordinator(
        self, coordinator: ActionTriggerCoordinator | None
    ) -> None:
        """Set the trigger coordinator for cancellation callbacks.

        Args:
            coordinator: The ActionTriggerCoordinator instance, or None to clear
        """
        self._trigger_coordinator = coordinator

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
        if len(name) > MAX_NAME_LENGTH:
            raise ValueError(f"Action name cannot exceed {MAX_NAME_LENGTH} characters")

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
        if delay_seconds < 0 or delay_seconds > MAX_DELAY_SECONDS:
            raise ValueError(f"delay_seconds must be between 0 and {MAX_DELAY_SECONDS}")

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
        enabled: bool = True,
    ) -> AbodeAction:
        """Create a new action with validation.

        Args:
            name: User-friendly name for the action
            modes: List of modes when action should be active
            sensor_entity_ids: List of sensor entity IDs to monitor
            alarm_entity_ids: List of alarm entity IDs to trigger
            delay_seconds: Delay before triggering (0-60)
            enabled: Whether the action starts enabled (default True).
                Symmetric with ``async_update`` and the ``AbodeAction``
                dataclass; restored here in #103 after a prior refactor
                dropped it from the signature.

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
            enabled=enabled,
        )
        await self._store.async_add(action)
        return action

    async def async_get(self, action_id: str) -> AbodeAction | None:
        """Get an action by ID."""
        return self._store.get(action_id)

    async def async_get_all(self) -> list[AbodeAction]:
        """Get all actions."""
        return self._store.get_all()

    async def async_update(self, action_id: str, **kwargs: Any) -> AbodeAction | None:
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

        # Cancel pending delays if action was disabled
        if self._trigger_coordinator and not enabled and action.enabled:
            self._trigger_coordinator.cancel_pending_for_action(action_id)

        return updated_action

    async def async_delete(self, action_id: str) -> bool:
        """Delete an action.

        Returns True if deleted, False if not found.
        """
        # Cancel any pending delays for this action
        if self._trigger_coordinator:
            self._trigger_coordinator.cancel_pending_for_action(action_id)

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
