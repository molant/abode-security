"""Derived state machine for scheduled-arming pairs.

`derive_state` collapses PENDING_ARM / PENDING_DISARM (conceptual from the
README) into IDLE / ARMED.  The runtime tracks pending timers separately via
``dict[(pair_id, "arm"|"disarm")] -> CancelHandle`` in the manager.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta, tzinfo
from enum import Enum, auto

from .models import ScheduledPair, weekday_name

# Grace tolerance applied to the "window elapsed" check.  The one-shot disarm
# timer (async_call_later) fires at-or-slightly-after expected_disarm_at, so the
# utcnow() read inside async_disarm is always a hair past the boundary.  Without
# this grace, a strict `now > expected_disarm` would treat an on-time disarm as
# a missed window and silently skip it.  Kept small: it must exceed worst-case
# event-loop latency between the timer firing and the utcnow() read (sub-second
# to seconds) while staying far below a genuinely-missed window (e.g. HA down for
# hours), which is left to the conservative startup-reconcile path.
DISARM_WINDOW_GRACE = timedelta(minutes=5)


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
    if now > expected_disarm + DISARM_WINDOW_GRACE:
        return PairState.IDLE  # window has elapsed (past the grace tolerance)
    return PairState.ARMED


def expected_disarm_at(
    pair: ScheduledPair, *, last_armed_at: datetime, tz: tzinfo
) -> datetime:
    """Next occurrence of pair.disarm_time at or after last_armed_at, in HA tz.

    ``tz`` MUST be passed explicitly — typically ``dt_util.DEFAULT_TIME_ZONE``.
    Never use bare ``.astimezone()`` with no argument: that defaults to the
    system local tz, which is UTC in Docker and will silently produce wrong
    wall-clock times.

    ``fold`` is inherited from ``last_armed_at`` rather than pinned, and that is
    the right call for the anchors this actually gets: every caller derives one
    from a UTC instant, which ``.astimezone(tz)`` resolves to the correct side of
    a fall-back hour on its own.  It is a *wall-clock*-derived anchor that would
    be ambiguous, which is why :func:`in_arm_window` pins ``fold=0`` on the one
    it builds by ``replace()`` before handing it over.

    One pre-existing gap the above does not close, recorded so the next reader
    does not take the fold story for complete: the ``candidate <= local`` test is
    a naive same-``tzinfo`` comparison (PEP 495), so a ``disarm_time`` that falls
    inside a repeated hour can roll the boundary forward by a whole day on a
    fall-back night.  Reaching it needs both a fall-back and a ``disarm_time``
    inside that one hour; it is not something #212 introduced or touches.
    """
    local = last_armed_at.astimezone(tz)
    disarm_t = parse_hhmm(pair.disarm_time)
    candidate = local.replace(
        hour=disarm_t.hour, minute=disarm_t.minute, second=0, microsecond=0
    )
    if candidate <= local:
        candidate += timedelta(days=1)
    return candidate


def in_arm_window(pair: ScheduledPair, *, now: datetime, tz: tzinfo) -> bool:
    """Return True when ``now`` falls inside one of ``pair``'s arm→disarm windows.

    The window is anchored on the most recent occurrence of ``arm_time`` at or
    before ``now``, and it is *that* occurrence's weekday which is matched
    against ``pair.weekdays`` — not ``now``'s own.  The two differ every morning
    of an overnight pair (arm 23:00 / disarm 06:00): Tuesday 02:00 is squarely
    inside the Monday window, and checking ``now.weekday()`` would call it
    outside.

    Anchoring on the arm edge is also what makes the every-weekday case behave.
    With all seven days enabled the weekday test can never reject, so the
    ``expected_disarm_at`` comparison is the only thing separating "inside the
    window" from "after last night's window closed": at 21:00 the anchor is
    *yesterday* 23:00, whose disarm boundary (today 06:00) is already past.

    ``tz`` MUST be passed explicitly — same reason as :func:`expected_disarm_at`.

    Both comparisons below are made between *absolute instants*, and the anchor
    pins ``fold=0`` rather than inheriting it from ``now``.  A fall-back night is
    what forces both.  When the clocks go back, the arm hour repeats: 02:30 CEST
    happens, an hour passes, and the wall clock reads 02:00 CET again.  Left
    naive this reported a window the panel was squarely inside as closed, by two
    separate routes — inheriting ``fold=1`` resolved the anchor to the *later* of
    the two 02:30s (the daily arm timer fires on the first, so that is the one
    the anchor has to name), and PEP 495 makes ``<``/``>`` between two datetimes
    sharing a ``tzinfo`` a naive wall-clock comparison that ignores ``fold``
    entirely, so the already-past 02:30 still compared as "later" than 02:00.
    """
    local = now.astimezone(tz)
    now_utc = now.astimezone(UTC)
    arm_t = parse_hhmm(pair.arm_time)
    anchor = local.replace(
        hour=arm_t.hour, minute=arm_t.minute, second=0, microsecond=0, fold=0
    )
    if anchor.astimezone(UTC) > now_utc:
        anchor -= timedelta(days=1)
    if weekday_name(anchor.weekday()) not in pair.weekdays:
        return False
    expected = expected_disarm_at(pair, last_armed_at=anchor, tz=tz)
    return now_utc < expected.astimezone(UTC)


def parse_hhmm(s: str) -> time:
    """Parse a ``"HH:MM"`` string into a :class:`datetime.time`."""
    hour, minute = s.split(":")
    return time(int(hour), int(minute))
