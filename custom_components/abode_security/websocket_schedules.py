"""WebSocket handlers for schedules CRUD."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

import voluptuous as vol
from homeassistant.components.websocket_api.decorators import (
    async_response,
    require_admin,
    websocket_command,
)
from homeassistant.core import HomeAssistant

from .const import DOMAIN, MAX_SCHEDULE_NAME_LENGTH
from .scheduling.models import WEEKDAYS

if TYPE_CHECKING:
    from homeassistant.components.websocket_api.connection import ActiveConnection

    from .scheduling.manager import ScheduleManager

_LOGGER = logging.getLogger(__name__)

_TIME_PATTERN = vol.Match(r"^([01]\d|2[0-3]):[0-5]\d$")


def _non_bool_bool(value: object) -> bool:
    """Voluptuous validator: accept only actual bools, reject int 0/1.

    Mirrors ``_non_bool_int`` in websocket_api.py — prevents Python's
    bool-as-int subclass from silently coercing stored ``1``/``0`` through
    the schema as if they were booleans.
    """
    if not isinstance(value, bool):
        raise vol.Invalid("expected bool (not int)")
    return value


def _get_schedule_manager(hass: HomeAssistant) -> ScheduleManager | None:
    """Return the ScheduleManager from hass.data, or None if not ready."""
    return cast(
        "ScheduleManager | None",
        hass.data.get(DOMAIN, {}).get("schedule_manager"),
    )


# --- schedules/list ---


# schedules/list and schedules/get are intentionally open to any authenticated user
# (no @require_admin). Schedule metadata (arm/disarm times, enabled state) is
# needed by the frontend for all users who can view the Modes tab. This mirrors
# the modes/list and config/get policy — read-only, non-actionable data.
# Mutations (create/update/delete) still require admin; see websocket_api.py
# policy block for the full rationale.
@websocket_command(
    {
        vol.Required("type"): "abode_security/schedules/list",
    }
)
@async_response
async def websocket_schedules_list(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """List all schedules, sorted ascending by created_at."""
    manager = _get_schedule_manager(hass)
    if manager is None:
        connection.send_error(
            msg["id"], "not_ready", "Schedule manager not initialized"
        )
        return

    pairs = await manager.async_get_all()
    pairs.sort(key=lambda p: p.created_at)
    connection.send_result(
        msg["id"],
        {"schedules": [p.to_dict() for p in pairs]},
    )


# --- schedules/get ---


@websocket_command(
    {
        vol.Required("type"): "abode_security/schedules/get",
        vol.Required("schedule_id"): str,
    }
)
@async_response
async def websocket_schedules_get(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get a single schedule by id."""
    manager = _get_schedule_manager(hass)
    if manager is None:
        connection.send_error(
            msg["id"], "not_ready", "Schedule manager not initialized"
        )
        return

    schedule_id = msg["schedule_id"]
    pair = await manager.async_get(schedule_id)
    if pair is None:
        connection.send_error(
            msg["id"], "not_found", f"Schedule {schedule_id} not found"
        )
        return

    connection.send_result(msg["id"], pair.to_dict())


# --- schedules/create ---


@websocket_command(
    {
        vol.Required("type"): "abode_security/schedules/create",
        vol.Optional("name", default=""): vol.All(
            str, vol.Length(max=MAX_SCHEDULE_NAME_LENGTH)
        ),
        vol.Required("weekdays"): vol.All(
            [vol.In(WEEKDAYS)],
            vol.Length(min=1, max=len(WEEKDAYS)),
        ),
        vol.Required("arm_time"): _TIME_PATTERN,
        vol.Required("disarm_time"): _TIME_PATTERN,
        vol.Optional("enabled", default=True): _non_bool_bool,
    }
)
@require_admin
@async_response
async def websocket_schedules_create(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Create a new schedule."""
    manager = _get_schedule_manager(hass)
    if manager is None:
        connection.send_error(
            msg["id"], "not_ready", "Schedule manager not initialized"
        )
        return

    try:
        pair = await manager.async_create(
            name=msg.get("name", ""),
            weekdays=msg["weekdays"],
            arm_time=msg["arm_time"],
            disarm_time=msg["disarm_time"],
            enabled=msg.get("enabled", True),
        )
        _LOGGER.info("Schedule %s created by user %s", pair.id, connection.user.id)
        connection.send_result(msg["id"], pair.to_dict())
    except ValueError as err:
        connection.send_error(msg["id"], "validation_error", str(err))


# --- schedules/update ---

_MUTABLE_FIELDS = frozenset({"name", "weekdays", "arm_time", "disarm_time", "enabled"})


@websocket_command(
    {
        vol.Required("type"): "abode_security/schedules/update",
        vol.Required("schedule_id"): str,
        vol.Optional("name"): vol.All(str, vol.Length(max=MAX_SCHEDULE_NAME_LENGTH)),
        vol.Optional("weekdays"): vol.All(
            [vol.In(WEEKDAYS)],
            vol.Length(min=1, max=len(WEEKDAYS)),
        ),
        vol.Optional("arm_time"): _TIME_PATTERN,
        vol.Optional("disarm_time"): _TIME_PATTERN,
        vol.Optional("enabled"): _non_bool_bool,
    }
)
@require_admin
@async_response
async def websocket_schedules_update(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Update a schedule (partial update)."""
    manager = _get_schedule_manager(hass)
    if manager is None:
        connection.send_error(
            msg["id"], "not_ready", "Schedule manager not initialized"
        )
        return

    update_fields = {k: v for k, v in msg.items() if k in _MUTABLE_FIELDS}
    if not update_fields:
        connection.send_error(
            msg["id"],
            "validation_error",
            "At least one mutable field must be provided",
        )
        return

    pair_id = msg["schedule_id"]
    try:
        pair = await manager.async_update(pair_id, **update_fields)
        if pair is None:
            connection.send_error(
                msg["id"], "not_found", f"Schedule {pair_id} not found"
            )
            return
        _LOGGER.info("Schedule %s updated by user %s", pair.id, connection.user.id)
        connection.send_result(msg["id"], pair.to_dict())
    except ValueError as err:
        connection.send_error(msg["id"], "validation_error", str(err))


# --- schedules/delete ---


@websocket_command(
    {
        vol.Required("type"): "abode_security/schedules/delete",
        vol.Required("schedule_id"): str,
    }
)
@require_admin
@async_response
async def websocket_schedules_delete(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete a schedule."""
    manager = _get_schedule_manager(hass)
    if manager is None:
        connection.send_error(
            msg["id"], "not_ready", "Schedule manager not initialized"
        )
        return

    pair_id = msg["schedule_id"]
    result = await manager.async_delete(pair_id)

    if not result:
        connection.send_error(msg["id"], "not_found", f"Schedule {pair_id} not found")
        return

    _LOGGER.info("Schedule %s deleted by user %s", pair_id, connection.user.id)
    connection.send_result(msg["id"], {"success": True, "id": pair_id})
