"""CRUD manager for scheduled arming pairs."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from homeassistant.util import dt as dt_util

from ..const import MAX_SCHEDULE_NAME_LENGTH
from .models import _TIME_RE, WEEKDAYS, ScheduledPair
from .store import SchedulesStore

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

# Runtime methods added in Phase 3:
#   async_arm(pair_id)
#   async_disarm(pair_id)
#   async_reconcile_on_startup()
#   async_handle_manual_change(new_state)


class ScheduleManager:
    """CRUD over SchedulesStore with field validation.

    The constructor signature anticipates Phase 3 widening to accept ``clock``,
    ``scheduler_clock``, and ``mode_changer`` — do not construct dependencies
    inside ``__init__``.
    """

    def __init__(self, hass: HomeAssistant, store: SchedulesStore) -> None:
        """Initialize the manager with injected dependencies."""
        self._hass = hass
        self._store = store

    async def async_setup(self) -> None:
        """Load persistent state.  Timer registration arrives in Phase 3."""
        await self._store.async_load()

    async def async_shutdown(self) -> None:
        """Clean up.  Timer cancellation arrives in Phase 3."""

    async def async_create(
        self,
        *,
        name: str = "",
        weekdays: list[str],
        arm_time: str,
        disarm_time: str,
        enabled: bool = True,
    ) -> ScheduledPair:
        """Create and persist a new schedule pair.

        Raises:
            ValueError: if validation fails or the schedule cap is reached.
        """
        pair = ScheduledPair(
            id=str(uuid.uuid4()),
            name=name,
            weekdays=weekdays,
            arm_time=arm_time,
            disarm_time=disarm_time,
            enabled=enabled,
            created_at=dt_util.utcnow(),
        )
        self._validate(pair)
        await self._store.async_add(pair)
        return pair

    async def async_update(self, pair_id: str, **kwargs: Any) -> ScheduledPair | None:
        """Apply a partial update to a pair.

        Only the writable fields (name, weekdays, arm_time, disarm_time, enabled)
        are accepted.  Raises ``ValueError`` on validation failure; returns
        ``None`` if the pair doesn't exist.
        """
        pair = self._store.get(pair_id)
        if pair is None:
            return None

        writable = {"name", "weekdays", "arm_time", "disarm_time", "enabled"}
        unknown = set(kwargs) - writable
        if unknown:
            raise ValueError(f"non-writable field(s): {sorted(unknown)!r}")

        updated = ScheduledPair(
            id=pair.id,
            name=kwargs.get("name", pair.name),
            weekdays=kwargs.get("weekdays", pair.weekdays),
            arm_time=kwargs.get("arm_time", pair.arm_time),
            disarm_time=kwargs.get("disarm_time", pair.disarm_time),
            enabled=kwargs.get("enabled", pair.enabled),
            created_at=pair.created_at,
            last_armed_at=pair.last_armed_at,
            last_disarmed_at=pair.last_disarmed_at,
            last_skip_reason=pair.last_skip_reason,
            last_error=pair.last_error,
        )
        self._validate(updated)
        await self._store.async_update(updated)
        return updated

    async def async_delete(self, pair_id: str) -> bool:
        """Delete a pair; return True if found, False otherwise."""
        return await self._store.async_remove(pair_id)

    async def async_get(self, pair_id: str) -> ScheduledPair | None:
        """Return a pair by id."""
        return self._store.get(pair_id)

    async def async_get_all(self) -> list[ScheduledPair]:
        """Return all pairs."""
        return self._store.get_all()

    def _validate(self, pair: ScheduledPair) -> None:
        """Validate all user-settable fields.  Raises ``ValueError`` if invalid."""
        if len(pair.name) > MAX_SCHEDULE_NAME_LENGTH:
            raise ValueError(
                f"name must be at most {MAX_SCHEDULE_NAME_LENGTH} characters"
            )

        if not pair.weekdays:
            raise ValueError("weekdays must be non-empty")
        unknown_days = [d for d in pair.weekdays if d not in WEEKDAYS]
        if unknown_days:
            raise ValueError(f"unknown weekday(s): {unknown_days!r}")
        if len(pair.weekdays) != len(set(pair.weekdays)):
            raise ValueError("weekdays must not contain duplicates")

        if not _TIME_RE.match(pair.arm_time):
            raise ValueError("arm_time must match HH:MM (24-hour)")
        if not _TIME_RE.match(pair.disarm_time):
            raise ValueError("disarm_time must match HH:MM (24-hour)")
        if pair.arm_time == pair.disarm_time:
            raise ValueError("arm_time and disarm_time must differ")
