"""Persistent storage for scheduled arming pairs."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.storage import Store

from ..const import (
    MAX_SCHEDULES,
    STORAGE_KEY_SCHEDULES,
    STORAGE_VERSION_SCHEDULES,
)
from .models import ScheduledPair
from .repair import async_clear_corrupt_issue, async_raise_corrupt_issue

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class SchedulesStore:
    """Persistent JSON storage for ScheduledPair records.

    Mirrors ActionStore behaviour: immediate non-debounced saves, per-record
    corruption handling with HA repair issues.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the store."""
        self._hass = hass
        self._store: Store[Any] = Store(
            hass, STORAGE_VERSION_SCHEDULES, STORAGE_KEY_SCHEDULES
        )
        self._schedules: dict[str, ScheduledPair] = {}

    async def async_load(self) -> None:
        """Load schedules from storage, skipping individually corrupt records."""
        self._schedules = {}

        whole_file_corrupt = False
        dropped = 0
        loaded: dict[str, ScheduledPair] = {}

        data = await self._store.async_load()
        if data is not None and not isinstance(data, dict):
            _LOGGER.warning(
                "Schedule storage root is not a dict (%s); ignoring all records",
                type(data).__name__,
            )
            whole_file_corrupt = True
        elif data is not None:
            schedules_data = data.get("schedules", {})
            if not isinstance(schedules_data, dict):
                _LOGGER.warning(
                    "Schedule storage 'schedules' is not a dict (%s); ignoring all records",
                    type(schedules_data).__name__,
                )
                whole_file_corrupt = True
            else:
                for key, raw in schedules_data.items():
                    try:
                        pair = ScheduledPair.from_dict(raw)
                    except (ValueError, TypeError) as exc:
                        record_id = raw.get("id") if isinstance(raw, dict) else None
                        _LOGGER.warning(
                            "Dropping corrupt schedule record %s: %s",
                            record_id or key,
                            exc,
                        )
                        dropped += 1
                        continue

                    if pair.id in loaded:
                        _LOGGER.warning(
                            "Dropping duplicate schedule id %s (record key %s); keeping first",
                            pair.id,
                            key,
                        )
                        dropped += 1
                        continue

                    loaded[pair.id] = pair

        self._schedules = loaded
        if whole_file_corrupt:
            async_raise_corrupt_issue(self._hass, count=None)
        elif dropped:
            async_raise_corrupt_issue(self._hass, count=dropped)
        else:
            async_clear_corrupt_issue(self._hass)

    async def async_save(self) -> None:
        """Persist all schedules immediately (non-debounced, mirrors ActionStore)."""
        data: dict[str, Any] = {
            "schedules": {
                pair_id: pair.to_dict() for pair_id, pair in self._schedules.items()
            }
        }
        await self._store.async_save(data)

    async def async_add(self, pair: ScheduledPair) -> None:
        """Add a pair and persist."""
        if pair.id not in self._schedules and len(self._schedules) >= MAX_SCHEDULES:
            raise ValueError(
                f"Cannot add schedule: limit of {MAX_SCHEDULES} schedules reached"
            )
        self._schedules[pair.id] = pair
        await self.async_save()

    async def async_update(self, pair: ScheduledPair) -> None:
        """Update an existing pair and persist."""
        self._schedules[pair.id] = pair
        await self.async_save()

    async def async_remove(self, pair_id: str) -> bool:
        """Remove a pair; return True if found, False if not."""
        if pair_id not in self._schedules:
            return False
        del self._schedules[pair_id]
        await self.async_save()
        return True

    def get(self, pair_id: str) -> ScheduledPair | None:
        """Return a pair by id from the in-memory cache."""
        return self._schedules.get(pair_id)

    def get_all(self) -> list[ScheduledPair]:
        """Return all pairs as a list."""
        return list(self._schedules.values())
