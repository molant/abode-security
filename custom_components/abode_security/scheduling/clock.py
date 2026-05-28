"""Clock protocol for tz-aware time queries."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol, cast

from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class Clock(Protocol):
    """Protocol for tz-aware time queries."""

    def now(self) -> datetime: ...  # local HA timezone

    def utcnow(self) -> datetime: ...  # UTC


class HAClock:
    """Production Clock backed by HA's dt_util."""

    def __init__(self, hass: HomeAssistant) -> None:
        # Held per the Phase 2 DI contract; dt_util reads HA's global timezone state.
        self._hass = hass

    def now(self) -> datetime:
        return cast(datetime, dt_util.now())

    def utcnow(self) -> datetime:
        return cast(datetime, dt_util.utcnow())
