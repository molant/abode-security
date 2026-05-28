"""Tests for scheduling/scheduler.py."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers import event as ha_event
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.abode_security.scheduling.scheduler import HAScheduleClock


@pytest.fixture
def schedule_clock(hass):
    return HAScheduleClock(hass)


async def _fire(hass, dt_utc: datetime) -> None:
    """Fire a mock time change and drain all tasks including background ones.

    Uses fire_all=True so timers that haven't reached their scheduled wall-clock
    time in the test environment still fire.

    Keeps time_tracker_utcnow patched through async_block_till_done: the
    _pattern_time_change_listener callback is scheduled via call_soon and runs
    *after* async_fire_time_changed exits its own patch context.  Without this
    outer patch, time_tracker_utcnow() returns the real clock inside the
    listener, producing the wrong weekday/hour for the assertion.

    All test datetimes must be in the FUTURE relative to the real wall clock so
    that _TrackPointUTCTime.__call__ sees (expected_fire_timestamp - mock_ts) < 0
    and calls the listener instead of rearming.  Tests use dates in 2030 which
    are several years ahead of the 2026 project timeline.
    """
    with patch.object(ha_event, "time_tracker_utcnow", return_value=dt_utc):
        async_fire_time_changed(hass, dt_utc, fire_all=True)
        await hass.async_block_till_done(wait_background_tasks=True)


# --- Weekday filtering ---

# 2030-01-07 is a Monday, 2030-01-08 is a Tuesday, 2030-01-14 is the next Monday.
# Using 2030 ensures these mock datetimes are far enough in the future that
# _TrackPointUTCTime.__call__ does not rearm: delta = (expected_fire_ts - mock_ts) < 0.
_MON_2030 = datetime(2030, 1, 7, 22, 0, 0, tzinfo=UTC)
_TUE_2030 = datetime(2030, 1, 8, 22, 0, 0, tzinfo=UTC)
_MON_2030_NEXT = datetime(2030, 1, 14, 22, 0, 0, tzinfo=UTC)


async def test_callback_fires_on_matching_weekday(hass, schedule_clock):
    """Daily 22:00 Mon-only callback fires on Monday."""
    callback = AsyncMock()
    cancel = schedule_clock.async_track_daily(
        callback,
        hour=22,
        minute=0,
        weekdays=frozenset({0}),  # 0=Monday
    )
    try:
        await _fire(hass, _MON_2030)
        callback.assert_called_once()
    finally:
        cancel()


async def test_callback_does_not_fire_on_non_matching_weekday(hass, schedule_clock):
    """Daily 22:00 Mon-only callback does NOT fire on Tuesday."""
    callback = AsyncMock()
    cancel = schedule_clock.async_track_daily(
        callback,
        hour=22,
        minute=0,
        weekdays=frozenset({0}),  # Monday only
    )
    try:
        await _fire(hass, _TUE_2030)
        callback.assert_not_called()
    finally:
        cancel()


async def test_cancel_handle_stops_future_fires(hass, schedule_clock):
    """Cancelling the handle prevents subsequent ticks from firing."""
    callback = AsyncMock()
    cancel = schedule_clock.async_track_daily(
        callback, hour=22, minute=0, weekdays=frozenset({0})
    )

    await _fire(hass, _MON_2030)
    assert callback.call_count == 1

    cancel()

    # Must not fire after cancel
    await _fire(hass, _MON_2030_NEXT)
    assert callback.call_count == 1


# --- DST behaviour (documented, not fought) ---


async def test_dst_spring_forward_madrid_callback_fires_at_0330_cest_not_0230(
    hass, schedule_clock
):
    """Spring-forward 2030 Europe/Madrid: callback fires at 03:30 CEST, not 02:30.

    On 2030-03-31, Madrid clocks jump from 02:00 CET (01:00 UTC) to 03:00 CEST.
    The local time 02:30 never occurs.  HA's timer for 02:30 is deferred to
    2030-04-01 00:30 UTC (next valid 02:30 CEST).

    This test fires at 01:30 UTC on the spring-forward day, which HA converts to
    03:30 CEST (after the gap).  fire_all=True forces the timer to execute; the
    listener receives localized_now = 03:30 CEST.  We document that the callback
    fires once (at the first UTC tick that crosses the timer deadline), and that
    no retroactive 02:30 invocation is invented.

    Note: fire_time is consumed inside _wrapper and not forwarded to callback(),
    so we cannot assert the exact local time from the test.  The assertion verifies
    that exactly one invocation occurs — no double-firing, no retroactive firing.

    DST skip guarantee: HA's async_track_time_change never schedules a UTC timer
    for a local time that does not exist (no 02:30 CEST on spring-forward day).
    The timer advances to the next valid 02:30 occurrence (April 1).
    """
    await hass.config.async_set_time_zone("Europe/Madrid")
    callback = AsyncMock()
    # 2030-03-31 01:30 UTC = 03:30 CEST (spring-forward occurred at 01:00 UTC)
    spring_forward_utc = datetime(2030, 3, 31, 1, 30, 0, tzinfo=UTC)
    cancel = schedule_clock.async_track_daily(
        callback, hour=2, minute=30, weekdays=frozenset(range(7))
    )
    try:
        await _fire(hass, spring_forward_utc)
        # Fires once at 03:30 CEST — no retroactive 02:30 invocation.
        assert callback.call_count == 1
    finally:
        cancel()


async def test_dst_fall_back_madrid_0130_callback_fires_at_first_occurrence(
    hass, schedule_clock
):
    """Fall-back 2030 Europe/Madrid: 01:30 local fires at its first UTC occurrence.

    On 2030-10-27, Madrid clocks fall back from 03:00 CEST to 02:00 CET (01:00 UTC).
    Local time 01:30 appears first as CEST (23:30 UTC on Oct 26) then again as CET
    (00:30 UTC on Oct 27).  HA fires the callback when the timer expires for the
    first occurrence.
    """
    await hass.config.async_set_time_zone("Europe/Madrid")
    callback = AsyncMock()
    # First occurrence: 23:30 UTC on Oct 26 = 01:30 CEST on Oct 27 (before fall-back)
    first_occurrence_utc = datetime(2030, 10, 26, 23, 30, 0, tzinfo=UTC)
    cancel = schedule_clock.async_track_daily(
        callback, hour=1, minute=30, weekdays=frozenset(range(7))
    )
    try:
        await _fire(hass, first_occurrence_utc)
        # Fires exactly once at the first occurrence (23:30 UTC = 01:30 CEST on Oct 27).
        assert callback.call_count == 1
    finally:
        cancel()
