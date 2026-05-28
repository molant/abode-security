"""ScheduleClock protocol wrapping async_track_time_change."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TYPE_CHECKING, Protocol, cast

from homeassistant.helpers.event import async_track_time_change

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

CancelHandle = Callable[[], None]


class ScheduleClock(Protocol):
    """Protocol for registering daily time-change callbacks with weekday filtering."""

    def async_track_daily(
        self,
        callback: Callable[[], Awaitable[None]],
        *,
        hour: int,
        minute: int,
        weekdays: frozenset[int],  # ISO: Monday=0 … Sunday=6
    ) -> CancelHandle: ...


class HAScheduleClock:
    """Production ScheduleClock backed by HA's async_track_time_change.

    async_track_time_change fires in the HA local timezone (it uses
    dt_util.now() internally), so arm/disarm times are wall-clock local —
    exactly the semantics required by the spec.

    weekdays is a hint: async_track_time_change has no weekday parameter, so
    filtering is done inside the wrapper callback.

    DST behaviour (documented, not fought):
      - Spring forward: if the local clock skips from 01:59 to 03:00, a
        callback registered for 02:30 is not fired that day — HA sees no
        02:30 tick. Acceptable per spec.
      - Fall back: HA fires the callback once at the first occurrence of the
        duplicated local time. Acceptable per spec.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    def async_track_daily(
        self,
        callback: Callable[[], Awaitable[None]],
        *,
        hour: int,
        minute: int,
        weekdays: frozenset[int],
    ) -> CancelHandle:
        async def _wrapper(fire_time: datetime) -> None:
            # datetime.weekday(): Monday=0 … Sunday=6 (matches ISO / spec WEEKDAYS ordering)
            if fire_time.weekday() in weekdays:
                await callback()

        return cast(
            CancelHandle,
            async_track_time_change(
                self._hass, _wrapper, hour=hour, minute=minute, second=0
            ),
        )
