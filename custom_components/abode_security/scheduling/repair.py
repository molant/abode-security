"""Repair-issue helpers for the scheduling subsystem."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers import issue_registry as ir

from ..const import DOMAIN, REPAIR_ISSUE_CORRUPT_SCHEDULES

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def async_raise_corrupt_issue(hass: HomeAssistant, count: int | None) -> None:
    """Create the corrupt-schedule repair issue.

    ``count`` is the number of dropped records, or ``None`` when the whole
    file was unreadable (root not a dict / schedules not a dict).
    """
    ir.async_create_issue(
        hass,
        DOMAIN,
        REPAIR_ISSUE_CORRUPT_SCHEDULES,
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key=REPAIR_ISSUE_CORRUPT_SCHEDULES,
        translation_placeholders={
            "count": str(count) if count is not None else "unknown"
        },
    )


def async_clear_corrupt_issue(hass: HomeAssistant) -> None:
    """Delete the corrupt-schedule repair issue (called on clean load)."""
    ir.async_delete_issue(hass, DOMAIN, REPAIR_ISSUE_CORRUPT_SCHEDULES)
