"""Tests for scheduling/models.py."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from custom_components.abode_security.scheduling.models import (
    WEEKDAYS,
    ChangeSource,
    ScheduledPair,
    SkipReason,
    is_overnight,
    weekday_index,
    weekday_name,
)

_NOW = datetime(2026, 5, 26, 21, 59, 0, tzinfo=UTC)


def _make_pair(**overrides) -> dict:
    base = {
        "id": "test-id",
        "name": "Weeknights",
        "weekdays": ["mon", "tue"],
        "arm_time": "22:00",
        "disarm_time": "06:00",
        "enabled": True,
        "created_at": _NOW.isoformat(),
        "last_armed_at": None,
        "last_disarmed_at": None,
        "last_skip_reason": None,
        "last_error": None,
    }
    base.update(overrides)
    return base


class TestScheduledPairRoundTrip:
    def test_round_trip_all_fields(self) -> None:
        """Full round-trip with all nullable fields populated."""
        data = _make_pair(
            last_armed_at="2026-05-26T22:00:01.234567+00:00",
            last_disarmed_at="2026-05-27T06:00:00.123456+00:00",
            last_skip_reason="away_active",
            last_error="timeout",
        )
        pair = ScheduledPair.from_dict(data)
        assert pair.to_dict() == data

    def test_round_trip_nullable_fields_none(self) -> None:
        """Round-trip with all nullable timestamps null."""
        data = _make_pair()
        pair = ScheduledPair.from_dict(data)
        assert pair.to_dict() == data

    def test_round_trip_no_name_key(self) -> None:
        """Missing name key is treated as empty string."""
        data = _make_pair()
        del data["name"]
        pair = ScheduledPair.from_dict(data)
        assert pair.name == ""
        assert pair.to_dict()["name"] == ""

    def test_round_trip_empty_name(self) -> None:
        data = _make_pair(name="")
        pair = ScheduledPair.from_dict(data)
        assert pair.name == ""

    def test_created_at_preserves_timezone(self) -> None:
        data = _make_pair(created_at="2026-05-26T21:59:00.000000+00:00")
        pair = ScheduledPair.from_dict(data)
        assert pair.created_at.tzinfo is not None
        assert pair.to_dict()["created_at"] == "2026-05-26T21:59:00+00:00"

    def test_round_trip_enabled_false(self) -> None:
        data = _make_pair(enabled=False)
        pair = ScheduledPair.from_dict(data)
        assert pair.enabled is False

    def test_round_trip_all_weekdays(self) -> None:
        data = _make_pair(weekdays=list(WEEKDAYS))
        pair = ScheduledPair.from_dict(data)
        assert pair.weekdays == list(WEEKDAYS)


class TestFromDictValidation:
    def test_missing_id(self) -> None:
        data = _make_pair()
        del data["id"]
        with pytest.raises(ValueError, match="id"):
            ScheduledPair.from_dict(data)

    def test_empty_id(self) -> None:
        with pytest.raises(ValueError, match="id"):
            ScheduledPair.from_dict(_make_pair(id=""))

    def test_missing_created_at(self) -> None:
        data = _make_pair()
        del data["created_at"]
        with pytest.raises(ValueError, match="created_at"):
            ScheduledPair.from_dict(data)

    def test_name_too_long(self) -> None:
        with pytest.raises(ValueError, match="100"):
            ScheduledPair.from_dict(_make_pair(name="x" * 101))

    def test_name_not_string(self) -> None:
        with pytest.raises(ValueError, match="name"):
            ScheduledPair.from_dict(_make_pair(name=42))

    def test_weekdays_not_list(self) -> None:
        with pytest.raises(ValueError, match="weekdays"):
            ScheduledPair.from_dict(_make_pair(weekdays="mon"))

    def test_weekdays_empty(self) -> None:
        with pytest.raises(ValueError, match="weekdays"):
            ScheduledPair.from_dict(_make_pair(weekdays=[]))

    def test_weekdays_unknown_name(self) -> None:
        with pytest.raises(ValueError, match="unknown weekday"):
            ScheduledPair.from_dict(_make_pair(weekdays=["mon", "xyz"]))

    def test_weekdays_duplicates(self) -> None:
        with pytest.raises(ValueError, match="duplicate"):
            ScheduledPair.from_dict(_make_pair(weekdays=["mon", "mon"]))

    def test_arm_time_bad_format(self) -> None:
        with pytest.raises(ValueError, match="arm_time"):
            ScheduledPair.from_dict(_make_pair(arm_time="9:00"))

    def test_disarm_time_bad_format(self) -> None:
        with pytest.raises(ValueError, match="disarm_time"):
            ScheduledPair.from_dict(_make_pair(disarm_time="25:00"))

    def test_arm_equals_disarm(self) -> None:
        with pytest.raises(ValueError, match="differ"):
            ScheduledPair.from_dict(_make_pair(arm_time="08:00", disarm_time="08:00"))

    def test_enabled_not_bool(self) -> None:
        with pytest.raises(ValueError, match="enabled"):
            ScheduledPair.from_dict(_make_pair(enabled=1))

    def test_enabled_bool_subclass_rejected(self) -> None:
        # bool is a subclass of int; make sure True passes isinstance(x, bool)
        data = _make_pair()
        data["enabled"] = True
        pair = ScheduledPair.from_dict(data)
        assert pair.enabled is True

        data["enabled"] = 1
        with pytest.raises(ValueError, match="enabled"):
            ScheduledPair.from_dict(data)

    def test_unknown_extra_field(self) -> None:
        data = _make_pair()
        data["extra_field"] = "oops"
        with pytest.raises(ValueError, match="unknown field"):
            ScheduledPair.from_dict(data)

    def test_not_a_dict(self) -> None:
        with pytest.raises(ValueError, match="dict"):
            ScheduledPair.from_dict([1, 2, 3])


class TestIsOvernight:
    def test_overnight_22_to_06(self) -> None:
        pair = ScheduledPair.from_dict(
            _make_pair(arm_time="22:00", disarm_time="06:00")
        )
        assert is_overnight(pair) is True

    def test_same_day_08_to_17(self) -> None:
        pair = ScheduledPair.from_dict(
            _make_pair(arm_time="08:00", disarm_time="17:00")
        )
        assert is_overnight(pair) is False


class TestEnums:
    def test_change_source_str_equality(self) -> None:
        assert ChangeSource.USER_WS == "user_ws"
        assert ChangeSource.SCHEDULE_ARM == "schedule_arm"
        assert ChangeSource.SCHEDULE_DISARM == "schedule_disarm"
        assert ChangeSource.RECONCILE_DISARM == "reconcile_disarm"

    def test_skip_reason_str_equality(self) -> None:
        assert SkipReason.AWAY_ACTIVE == "away_active"
        assert SkipReason.ALREADY_HOME == "already_home"
        assert SkipReason.PANEL_UNAVAILABLE == "panel_unavailable"
        assert SkipReason.MANUAL_OVERRIDE == "manual_override"
        assert SkipReason.RECONCILE_WINDOW_ELAPSED == "reconcile_window_elapsed"
        assert SkipReason.RECONCILE_PANEL_NOT_HOME == "reconcile_panel_not_home"

    def test_change_source_is_str_enum(self) -> None:
        assert isinstance(ChangeSource.USER_WS, str)

    def test_skip_reason_is_str_enum(self) -> None:
        assert isinstance(SkipReason.AWAY_ACTIVE, str)


class TestWeekdayHelpers:
    def test_index_mon(self) -> None:
        assert weekday_index("mon") == 0

    def test_index_sun(self) -> None:
        assert weekday_index("sun") == 6

    def test_name_0(self) -> None:
        assert weekday_name(0) == "mon"

    def test_name_6(self) -> None:
        assert weekday_name(6) == "sun"
