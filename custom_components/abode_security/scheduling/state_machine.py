"""Derived state machine for scheduled-arming pairs.

`derive_state` collapses PENDING_ARM / PENDING_DISARM (conceptual from the
README) into IDLE / ARMED.  The runtime tracks pending timers separately via
``dict[(pair_id, "arm"|"disarm")] -> CancelHandle`` in the manager.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, tzinfo
from enum import Enum, auto

from .models import ScheduledPair


class PairState(Enum):
    """Derived run-state for a single schedule pair."""

    IDLE = auto()
    ARMED = auto()  # we armed it; disarm pending


def derive_state(pair: ScheduledPair, *, now: datetime, tz: tzinfo) -> PairState:
    """Return ARMED iff last_armed_at > last_disarmed_at AND still within window.

    ``tz`` MUST be passed explicitly — typically ``dt_util.DEFAULT_TIME_ZONE``
    (set by HA to ``hass.config.time_zone``).  Do NOT rely on the system local
    timezone: inside Docker containers the system tz is UTC, which would
    silently produce wrong wall-clock comparisons.
    """
    if pair.last_armed_at is None:
        return PairState.IDLE
    if (
        pair.last_disarmed_at is not None
        and pair.last_disarmed_at >= pair.last_armed_at
    ):
        return PairState.IDLE
    expected_disarm = expected_disarm_at(pair, last_armed_at=pair.last_armed_at, tz=tz)
    if now > expected_disarm:
        return PairState.IDLE  # window has elapsed
    return PairState.ARMED


def expected_disarm_at(
    pair: ScheduledPair, *, last_armed_at: datetime, tz: tzinfo
) -> datetime:
    """Next occurrence of pair.disarm_time at or after last_armed_at, in HA tz.

    ``tz`` MUST be passed explicitly — typically ``dt_util.DEFAULT_TIME_ZONE``.
    Never use bare ``.astimezone()`` with no argument: that defaults to the
    system local tz, which is UTC in Docker and will silently produce wrong
    wall-clock times.
    """
    local = last_armed_at.astimezone(tz)
    disarm_t = parse_hhmm(pair.disarm_time)
    candidate = local.replace(
        hour=disarm_t.hour, minute=disarm_t.minute, second=0, microsecond=0
    )
    if candidate <= local:
        candidate += timedelta(days=1)
    return candidate


def parse_hhmm(s: str) -> time:
    """Parse a ``"HH:MM"`` string into a :class:`datetime.time`."""
    hour, minute = s.split(":")
    return time(int(hour), int(minute))
