"""Tests for scheduling/state_machine.py."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from custom_components.abode_security.scheduling.models import ScheduledPair
from custom_components.abode_security.scheduling.state_machine import (
    DISARM_WINDOW_GRACE,
    PairState,
    derive_state,
    expected_disarm_at,
    parse_hhmm,
)

_UTC = UTC
_EASTERN = ZoneInfo("America/New_York")
_BERLIN = ZoneInfo("Europe/Berlin")


def _pair(
    arm_time: str = "22:00",
    disarm_time: str = "06:00",
    last_armed_at: datetime | None = None,
    last_disarmed_at: datetime | None = None,
) -> ScheduledPair:
    return ScheduledPair(
        id="test-id",
        weekdays=["mon"],
        arm_time=arm_time,
        disarm_time=disarm_time,
        created_at=datetime(2024, 1, 1, tzinfo=_UTC),
        last_armed_at=last_armed_at,
        last_disarmed_at=last_disarmed_at,
    )


class TestDerivState:
    def test_no_arm_is_idle(self) -> None:
        pair = _pair(last_armed_at=None)
        now = datetime(2024, 6, 1, 23, 0, tzinfo=_UTC)
        assert derive_state(pair, now=now, tz=_UTC) == PairState.IDLE

    def test_disarmed_after_armed_is_idle(self) -> None:
        armed = datetime(2024, 6, 1, 22, 0, tzinfo=_UTC)
        disarmed = datetime(2024, 6, 2, 6, 0, tzinfo=_UTC)
        pair = _pair(last_armed_at=armed, last_disarmed_at=disarmed)
        now = datetime(2024, 6, 2, 7, 0, tzinfo=_UTC)
        assert derive_state(pair, now=now, tz=_UTC) == PairState.IDLE

    def test_armed_within_window(self) -> None:
        armed = datetime(2024, 6, 1, 22, 0, tzinfo=_UTC)
        pair = _pair(last_armed_at=armed)
        now = datetime(2024, 6, 1, 23, 30, tzinfo=_UTC)
        assert derive_state(pair, now=now, tz=_UTC) == PairState.ARMED

    def test_past_expected_disarm_is_idle(self) -> None:
        armed = datetime(2024, 6, 1, 22, 0, tzinfo=_UTC)
        pair = _pair(last_armed_at=armed)
        now = datetime(2024, 6, 2, 7, 0, tzinfo=_UTC)  # well past 06:00 + grace
        assert derive_state(pair, now=now, tz=_UTC) == PairState.IDLE

    def test_at_expected_disarm_time_is_armed(self) -> None:
        # Pair is still ARMED at exactly the disarm time so the timer callback works.
        armed = datetime(2024, 6, 1, 22, 0, tzinfo=_UTC)
        pair = _pair(last_armed_at=armed)
        now = datetime(2024, 6, 2, 6, 0, tzinfo=_UTC)  # exactly 06:00
        assert derive_state(pair, now=now, tz=_UTC) == PairState.ARMED

    def test_slightly_past_disarm_within_grace_is_armed(self) -> None:
        # The one-shot disarm timer fires at-or-after 06:00, so derive_state is
        # always re-checked a hair late.  Within DISARM_WINDOW_GRACE it must stay
        # ARMED, otherwise the on-time disarm is silently skipped.
        armed = datetime(2024, 6, 1, 22, 0, tzinfo=_UTC)
        pair = _pair(last_armed_at=armed)
        expected = datetime(2024, 6, 2, 6, 0, tzinfo=_UTC)
        now = expected + DISARM_WINDOW_GRACE - timedelta(seconds=1)
        assert derive_state(pair, now=now, tz=_UTC) == PairState.ARMED

    def test_at_grace_boundary_is_armed(self) -> None:
        # The elapsed check is strict (`now > expected + grace`), so exactly at
        # the boundary the pair is still ARMED.
        armed = datetime(2024, 6, 1, 22, 0, tzinfo=_UTC)
        pair = _pair(last_armed_at=armed)
        expected = datetime(2024, 6, 2, 6, 0, tzinfo=_UTC)
        now = expected + DISARM_WINDOW_GRACE
        assert derive_state(pair, now=now, tz=_UTC) == PairState.ARMED

    def test_just_past_grace_is_idle(self) -> None:
        armed = datetime(2024, 6, 1, 22, 0, tzinfo=_UTC)
        pair = _pair(last_armed_at=armed)
        expected = datetime(2024, 6, 2, 6, 0, tzinfo=_UTC)
        now = expected + DISARM_WINDOW_GRACE + timedelta(seconds=1)
        assert derive_state(pair, now=now, tz=_UTC) == PairState.IDLE

    def test_overnight_within_window(self) -> None:
        # arm Sat 22:00 UTC, disarm 06:00 next day; now = Sat 23:30 UTC
        armed = datetime(2024, 6, 1, 22, 0, tzinfo=_UTC)  # Saturday
        pair = _pair(arm_time="22:00", disarm_time="06:00", last_armed_at=armed)
        now = datetime(2024, 6, 1, 23, 30, tzinfo=_UTC)
        assert derive_state(pair, now=now, tz=_UTC) == PairState.ARMED

    def test_overnight_past_disarm_is_idle(self) -> None:
        # arm Sat 22:00 UTC, disarm 06:00 next day; now = Sun 06:10 UTC (past grace)
        armed = datetime(2024, 6, 1, 22, 0, tzinfo=_UTC)
        pair = _pair(arm_time="22:00", disarm_time="06:00", last_armed_at=armed)
        now = datetime(2024, 6, 2, 6, 10, tzinfo=_UTC)
        assert derive_state(pair, now=now, tz=_UTC) == PairState.IDLE

    def test_same_day_within_window(self) -> None:
        # arm 13:00, disarm 17:00; now = 14:00
        armed = datetime(2024, 6, 1, 13, 0, tzinfo=_UTC)
        pair = _pair(arm_time="13:00", disarm_time="17:00", last_armed_at=armed)
        now = datetime(2024, 6, 1, 14, 0, tzinfo=_UTC)
        assert derive_state(pair, now=now, tz=_UTC) == PairState.ARMED

    def test_same_day_past_disarm_is_idle(self) -> None:
        armed = datetime(2024, 6, 1, 13, 0, tzinfo=_UTC)
        pair = _pair(arm_time="13:00", disarm_time="17:00", last_armed_at=armed)
        now = datetime(2024, 6, 1, 17, 10, tzinfo=_UTC)  # past 17:00 + grace
        assert derive_state(pair, now=now, tz=_UTC) == PairState.IDLE

    def test_dst_forward_unaffected(self) -> None:
        # DST spring-forward in US Eastern: 2024-03-10 02:00 -> 03:00
        # arm at 22:00 ET on March 9; disarm at 06:00 ET on March 10.
        # derive_state works on the actual last_armed_at timestamp, not wall-clock.
        armed = datetime(2024, 3, 10, 3, 0, tzinfo=_UTC)  # ~22:00 ET
        pair = _pair(arm_time="22:00", disarm_time="06:00", last_armed_at=armed)
        now = datetime(2024, 3, 10, 4, 0, tzinfo=_UTC)  # ~23:00 ET
        assert derive_state(pair, now=now, tz=_EASTERN) == PairState.ARMED

    def test_disarmed_at_same_as_armed_is_idle(self) -> None:
        ts = datetime(2024, 6, 1, 22, 0, tzinfo=_UTC)
        pair = _pair(last_armed_at=ts, last_disarmed_at=ts)
        now = datetime(2024, 6, 1, 23, 0, tzinfo=_UTC)
        assert derive_state(pair, now=now, tz=_UTC) == PairState.IDLE


class TestExpectedDisarmAt:
    def test_same_day_disarm_after_arm(self) -> None:
        # arm 13:00 UTC, disarm 17:00 same day
        pair = _pair(arm_time="13:00", disarm_time="17:00")
        armed = datetime(2024, 6, 1, 13, 0, tzinfo=_UTC)
        result = expected_disarm_at(pair, last_armed_at=armed, tz=_UTC)
        assert result == datetime(2024, 6, 1, 17, 0, tzinfo=_UTC)

    def test_overnight_disarm_next_day(self) -> None:
        pair = _pair(arm_time="22:00", disarm_time="06:00")
        armed = datetime(2024, 6, 1, 22, 0, tzinfo=_UTC)
        result = expected_disarm_at(pair, last_armed_at=armed, tz=_UTC)
        assert result == datetime(2024, 6, 2, 6, 0, tzinfo=_UTC)

    def test_arm_at_midnight_disarm_later_same_day(self) -> None:
        pair = _pair(arm_time="00:00", disarm_time="08:00")
        armed = datetime(2024, 6, 1, 0, 0, tzinfo=_UTC)
        result = expected_disarm_at(pair, last_armed_at=armed, tz=_UTC)
        assert result == datetime(2024, 6, 1, 8, 0, tzinfo=_UTC)

    def test_disarm_time_just_before_arm_wraps_to_next_day(self) -> None:
        # arm 23:00, disarm 22:00 — overnight, so disarm is next day 22:00
        pair = _pair(arm_time="23:00", disarm_time="22:00")
        armed = datetime(2024, 6, 1, 23, 0, tzinfo=_UTC)
        result = expected_disarm_at(pair, last_armed_at=armed, tz=_UTC)
        assert result == datetime(2024, 6, 2, 22, 0, tzinfo=_UTC)

    def test_non_utc_timezone(self) -> None:
        # arm at 21:00 UTC = 22:00 Berlin (UTC+1 in winter / +2 summer)
        # Use a date in winter (UTC+1) so 22:00 Berlin = 21:00 UTC
        tz = _BERLIN
        armed = datetime(2024, 1, 15, 21, 0, tzinfo=_UTC)  # 22:00 Berlin
        pair = _pair(arm_time="22:00", disarm_time="06:00")
        result = expected_disarm_at(pair, last_armed_at=armed, tz=tz)
        # Expected: 06:00 Berlin next day = 05:00 UTC
        assert result.hour == 6
        assert result.tzinfo is not None


class TestParseHhmm:
    def test_midnight(self) -> None:
        t = parse_hhmm("00:00")
        assert t.hour == 0
        assert t.minute == 0

    def test_noon(self) -> None:
        t = parse_hhmm("12:00")
        assert t.hour == 12
        assert t.minute == 0

    def test_22_30(self) -> None:
        t = parse_hhmm("22:30")
        assert t.hour == 22
        assert t.minute == 30

    def test_23_59(self) -> None:
        t = parse_hhmm("23:59")
        assert t.hour == 23
        assert t.minute == 59
