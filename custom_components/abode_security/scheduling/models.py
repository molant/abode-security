"""Domain models for scheduled arming."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

_KNOWN_FIELDS = frozenset(
    {
        "id",
        "name",
        "weekdays",
        "arm_time",
        "disarm_time",
        "enabled",
        "created_at",
        "last_armed_at",
        "last_disarmed_at",
        "last_skip_reason",
        "last_error",
    }
)


class ChangeSource(StrEnum):
    """Source of a mode change."""

    USER_WS = "user_ws"
    SCHEDULE_ARM = "schedule_arm"
    SCHEDULE_DISARM = "schedule_disarm"
    RECONCILE_DISARM = "reconcile_disarm"


class SkipReason(StrEnum):
    """Why a scheduled arm or disarm was skipped."""

    AWAY_ACTIVE = "away_active"
    ALREADY_HOME = "already_home"
    PANEL_UNAVAILABLE = "panel_unavailable"
    MANUAL_OVERRIDE = "manual_override"
    RECONCILE_WINDOW_ELAPSED = "reconcile_window_elapsed"
    RECONCILE_PANEL_NOT_HOME = "reconcile_panel_not_home"


@dataclass
class ScheduledPair:
    """One arm/disarm schedule pair."""

    id: str
    weekdays: list[str]
    arm_time: str
    disarm_time: str
    created_at: datetime
    name: str = ""
    enabled: bool = True
    last_armed_at: datetime | None = None
    last_disarmed_at: datetime | None = None
    last_skip_reason: str | None = None
    last_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "id": self.id,
            "name": self.name,
            "weekdays": self.weekdays,
            "arm_time": self.arm_time,
            "disarm_time": self.disarm_time,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "last_armed_at": self.last_armed_at.isoformat()
            if self.last_armed_at
            else None,
            "last_disarmed_at": self.last_disarmed_at.isoformat()
            if self.last_disarmed_at
            else None,
            "last_skip_reason": self.last_skip_reason,
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, data: Any) -> ScheduledPair:
        """Deserialize and validate a record.

        Raises ``ValueError`` on any structural or semantic problem.
        """
        if not isinstance(data, dict):
            raise ValueError("record must be a dict")

        unknown = set(data.keys()) - _KNOWN_FIELDS
        if unknown:
            raise ValueError(f"unknown field(s): {sorted(unknown)!r}")

        pair_id = data.get("id")
        if not isinstance(pair_id, str) or not pair_id:
            raise ValueError("id must be a non-empty string")

        name = data.get("name", "")
        if not isinstance(name, str):
            raise ValueError("name must be a string")
        if len(name) > 100:
            raise ValueError("name must be at most 100 characters")

        weekdays = data.get("weekdays")
        if not isinstance(weekdays, list):
            raise ValueError("weekdays must be a list")
        if not weekdays:
            raise ValueError("weekdays must be non-empty")
        for day in weekdays:
            if day not in WEEKDAYS:
                raise ValueError(f"unknown weekday {day!r}")
        if len(weekdays) != len(set(weekdays)):
            raise ValueError("weekdays must not contain duplicates")

        arm_time = data.get("arm_time")
        if not isinstance(arm_time, str) or not _TIME_RE.match(arm_time):
            raise ValueError("arm_time must match HH:MM (24-hour)")

        disarm_time = data.get("disarm_time")
        if not isinstance(disarm_time, str) or not _TIME_RE.match(disarm_time):
            raise ValueError("disarm_time must match HH:MM (24-hour)")

        if arm_time == disarm_time:
            raise ValueError("arm_time and disarm_time must differ")

        enabled = data.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be a boolean")

        raw_created_at = data.get("created_at")
        if raw_created_at is None:
            raise ValueError("created_at is required")
        if not isinstance(raw_created_at, str):
            raise ValueError("created_at must be an ISO 8601 string")
        try:
            created_at = datetime.fromisoformat(raw_created_at)
        except ValueError as exc:
            raise ValueError(f"created_at is not valid ISO 8601: {exc}") from exc

        last_armed_at = _parse_optional_dt(data, "last_armed_at")
        last_disarmed_at = _parse_optional_dt(data, "last_disarmed_at")

        last_skip_reason = data.get("last_skip_reason")
        if last_skip_reason is not None and not isinstance(last_skip_reason, str):
            raise ValueError("last_skip_reason must be null or a string")

        last_error = data.get("last_error")
        if last_error is not None and not isinstance(last_error, str):
            raise ValueError("last_error must be null or a string")

        return cls(
            id=pair_id,
            name=name,
            weekdays=weekdays,
            arm_time=arm_time,
            disarm_time=disarm_time,
            enabled=enabled,
            created_at=created_at,
            last_armed_at=last_armed_at,
            last_disarmed_at=last_disarmed_at,
            last_skip_reason=last_skip_reason,
            last_error=last_error,
        )


def _parse_optional_dt(data: dict[str, Any], key: str) -> datetime | None:
    """Parse a nullable ISO datetime field, raising ValueError on bad values."""
    raw = data.get(key)
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValueError(f"{key} must be null or an ISO 8601 string")
    try:
        return datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{key} is not valid ISO 8601: {exc}") from exc


def is_overnight(pair: ScheduledPair) -> bool:
    """Return True when arm_time >= disarm_time (spans midnight)."""
    return pair.arm_time >= pair.disarm_time


def weekday_index(name: str) -> int:
    """Convert weekday name to ISO index (Mon=0)."""
    return WEEKDAYS.index(name)


def weekday_name(idx: int) -> str:
    """Convert ISO weekday index to name (Mon=0)."""
    return WEEKDAYS[idx]
