"""Repair-issue helpers for the actions subsystem.

Mirrors `scheduling/repair.py`. These exist because a security action that
fails is only visible in the log otherwise — the notification, the event, and
the Actions panel all used to render a total failure identically to a success.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers import issue_registry as ir

from .const import (
    DOMAIN,
    REPAIR_ISSUE_ACTION_ALARM_FAILED,
    REPAIR_ISSUE_UNTRIGGERABLE_ALARM,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def _alarm_failed_issue_id(action_id: str) -> str:
    """Scope the issue to one action so several can be surfaced at once."""
    return f"{REPAIR_ISSUE_ACTION_ALARM_FAILED}_{action_id}"


def async_raise_alarm_failed_issue(
    hass: HomeAssistant,
    *,
    action_id: str,
    action_name: str,
    entity_ids: list[str],
    reason: str,
) -> None:
    """Create the "an action's alarm did not fire" repair issue.

    Raised whenever `alarms_failed` is non-empty. Severity is ERROR rather
    than WARNING: the user believes an alarm was raised and it was not.
    """
    ir.async_create_issue(
        hass,
        DOMAIN,
        _alarm_failed_issue_id(action_id),
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key=REPAIR_ISSUE_ACTION_ALARM_FAILED,
        translation_placeholders={
            "action_name": action_name,
            "entities": ", ".join(entity_ids),
            "reason": reason,
        },
    )


def async_clear_alarm_failed_issue(hass: HomeAssistant, action_id: str) -> None:
    """Delete the issue once the same action fires its alarms successfully."""
    ir.async_delete_issue(hass, DOMAIN, _alarm_failed_issue_id(action_id))


def async_raise_untriggerable_alarm_issue(
    hass: HomeAssistant, offenders: dict[str, list[str]]
) -> None:
    """Flag stored actions pointing at an alarm Abode will not let us trigger.

    ``offenders`` maps a display label (name plus an id prefix, since names
    aren't unique) to the offending entity_ids. Raised at
    startup so the problem surfaces before the sensor does, rather than
    during the incident it was supposed to escalate.
    """
    summary = "; ".join(
        f"{name} → {', '.join(entities)}"
        for name, entities in sorted(offenders.items())
    )
    ir.async_create_issue(
        hass,
        DOMAIN,
        REPAIR_ISSUE_UNTRIGGERABLE_ALARM,
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key=REPAIR_ISSUE_UNTRIGGERABLE_ALARM,
        translation_placeholders={"actions": summary},
    )


def async_clear_untriggerable_alarm_issue(hass: HomeAssistant) -> None:
    """Delete the untriggerable-alarm issue when no action is affected."""
    ir.async_delete_issue(hass, DOMAIN, REPAIR_ISSUE_UNTRIGGERABLE_ALARM)
