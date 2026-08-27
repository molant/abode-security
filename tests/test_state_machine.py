"""Tests for scheduling/state_machine.py."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from custom_components.abode_security.scheduling.models import ScheduledPair
from custom_components.abode_security.scheduling.state_machine import (
    DISARM_WINDOW_GRACE,
    PairState,
    derive_state,
    expected_disarm_at,
    in_arm_window,
    parse_hhmm,
)

_UTC = UTC
_EASTERN = ZoneInfo("America/New_York")
_BERLIN = ZoneInfo("Europe/Berlin")
_MADRID = ZoneInfo("Europe/Madrid")
_PACIFIC = ZoneInfo("America/Los_Angeles")


def _pacific(hour: int, minute: int = 0, *, day: int = 7) -> datetime:
    """A UTC instant for a January 2030 US/Pacific wall-clock time.

    2030-01-07 is a Monday, so `day=8` is Tuesday.  Winter, so no DST edge is
    in play — the fall-back and spring-forward cases are pinned separately
    against Europe/Madrid below.
    """
    return datetime(2030, 1, day, hour, minute, tzinfo=_PACIFIC).astimezone(_UTC)


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


class TestInArmWindow:
    """`in_arm_window` — is *this instant* inside one of a pair's windows?

    The adoption path added for #212 leans on this to decide whether a panel
    that just entered `armed_home` is one a schedule should take ownership of.
    """

    @pytest.mark.parametrize(
        ("now", "expected"),
        [
            # A `mon`-only pair, so anything before Monday's own arm edge walks
            # the anchor back to Sunday and is rejected on the weekday branch —
            # noted because the times read like disarm-boundary cases and are
            # not.  The exclusive *end* of the window is pinned by the two
            # `day=8` cases straddling 06:00, which reach `expected_disarm_at`.
            (_pacific(22, 59), False),  # Mon, a minute early (weekday branch)
            (_pacific(23, 0), True),  # Mon, exactly the arm edge — inclusive
            (_pacific(23, 37), True),  # Mon night
            (_pacific(2, 0, day=8), True),  # Tue 02:00 — still Monday's window
            (_pacific(5, 59, day=8), True),  # Tue, a minute before the boundary
            (_pacific(6, 0, day=8), False),  # Tue, the disarm edge — exclusive
            (_pacific(12, 0, day=8), False),  # Tue midday
            (_pacific(23, 37, day=8), False),  # Tue night — not a Monday window
        ],
    )
    def test_overnight_window_boundaries(self, now: datetime, expected: bool) -> None:
        pair = _pair(arm_time="23:00", disarm_time="06:00")
        assert in_arm_window(pair, now=now, tz=_PACIFIC) is expected

    @pytest.mark.parametrize(
        ("now", "expected"),
        [
            # Same caveat as above: the two `False`s before 08:00 are weekday
            # rejections, and 17:00 is the one that pins the exclusive end.
            (_pacific(7, 59), False),  # weekday branch
            (_pacific(8, 0), True),  # arm edge — inclusive
            (_pacific(12, 0), True),
            (_pacific(16, 59), True),
            (_pacific(17, 0), False),  # disarm edge — exclusive
            (_pacific(2, 0), False),  # before the day's own arm edge
        ],
    )
    def test_same_day_window_boundaries(self, now: datetime, expected: bool) -> None:
        pair = _pair(arm_time="08:00", disarm_time="17:00")
        assert in_arm_window(pair, now=now, tz=_PACIFIC) is expected

    def test_every_weekday_pair_still_closes_its_window(self) -> None:
        """With all seven days enabled the weekday test can never reject.

        The `expected_disarm_at` comparison is then the only thing separating
        "inside tonight's window" from "after last night's closed".
        """
        pair = _pair(arm_time="23:00", disarm_time="06:00")
        pair.weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        assert in_arm_window(pair, now=_pacific(23, 30), tz=_PACIFIC) is True
        assert in_arm_window(pair, now=_pacific(3, 0, day=8), tz=_PACIFIC) is True
        assert in_arm_window(pair, now=_pacific(21, 0, day=8), tz=_PACIFIC) is False

    # -- DST ----------------------------------------------------------------
    #
    # Europe/Madrid, 2030-10-27: 03:00 CEST falls back to 02:00 CET, so 02:00 ->
    # 03:00 local happens twice.  A pair whose `arm_time` sits inside that
    # repeated hour is the case that breaks if the anchor inherits `fold` from
    # `now` instead of pinning `fold=0`.

    @pytest.mark.parametrize(
        ("utc_hour", "utc_minute"),
        [
            (0, 40),  # 02:40 CEST — first pass through the repeated hour
            (1, 0),  # 02:00 CET  — second pass, fold=1
            (1, 20),  # 02:20 CET  — second pass, fold=1
            (1, 50),  # 02:50 CET  — second pass, fold=1
            (5, 0),  # 06:00 CET  — well clear of the fold, still in window
        ],
    )
    def test_fall_back_repeated_hour_stays_in_window(
        self, utc_hour: int, utc_minute: int
    ) -> None:
        """Every instant between the arm edge and 08:00 reads as in-window.

        Inheriting `fold=1` resolved the anchor to the later of the two 02:30s,
        which lands *after* `now`, rolls the anchor back a full day, and reports
        a window the panel is squarely inside as closed.
        """
        pair = _pair(arm_time="02:30", disarm_time="08:00")
        pair.weekdays = ["sun"]
        now = datetime(2030, 10, 27, utc_hour, utc_minute, tzinfo=_UTC)
        assert in_arm_window(pair, now=now, tz=_MADRID) is True

    def test_fall_back_night_still_closes_its_window(self) -> None:
        """The fold fix must not wedge the window permanently open."""
        pair = _pair(arm_time="02:30", disarm_time="08:00")
        pair.weekdays = ["sun"]
        # 08:00 CET on the 27th — the disarm edge, exclusive.
        assert (
            in_arm_window(
                pair, now=datetime(2030, 10, 27, 7, 0, tzinfo=_UTC), tz=_MADRID
            )
            is False
        )
        # 00:00 CEST on the 27th — before that day's own arm edge, and the
        # previous day is not a Sunday.
        assert (
            in_arm_window(
                pair, now=datetime(2030, 10, 26, 22, 0, tzinfo=_UTC), tz=_MADRID
            )
            is False
        )

    def test_spring_forward_skipped_arm_hour_reads_as_in_window(self) -> None:
        """Documents a deliberate divergence from the arm timer, not a bug.

        On 2030-03-31 Madrid jumps 02:00 CET -> 03:00 CEST, so an `arm_time` of
        02:30 never occurs and HA's `async_track_time_change` does not fire the
        arm that day (see `test_scheduler.py`).  `in_arm_window` still reports
        the window open, because `replace()` on a non-existent local time
        resolves rather than raising.  The consequence is benign — adoption can
        only ever *schedule a disarm*, and only for a panel already in Home — so
        it is pinned here rather than papered over.
        """
        pair = _pair(arm_time="02:30", disarm_time="08:00")
        pair.weekdays = ["sun"]
        now = datetime(2030, 3, 31, 2, 0, tzinfo=_UTC)  # 04:00 CEST
        assert in_arm_window(pair, now=now, tz=_MADRID) is True
