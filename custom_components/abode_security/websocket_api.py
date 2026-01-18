"""WebSocket API for Abode Security frontend panel."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api import require_admin
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceNotFound

from .action_manager import VALID_MODES
from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.components.websocket_api import ActiveConnection

_LOGGER = logging.getLogger(__name__)


def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register WebSocket commands for Abode Security."""
    websocket_api.async_register_command(hass, websocket_actions_list)
    websocket_api.async_register_command(hass, websocket_actions_get)
    websocket_api.async_register_command(hass, websocket_actions_create)
    websocket_api.async_register_command(hass, websocket_actions_update)
    websocket_api.async_register_command(hass, websocket_actions_delete)
    websocket_api.async_register_command(hass, websocket_actions_toggle)
    websocket_api.async_register_command(hass, websocket_actions_test)


def _get_action_manager(hass: HomeAssistant):
    """Get the ActionManager from hass.data."""
    return hass.data.get(DOMAIN, {}).get("action_manager")


# --- Action CRUD Endpoints ---


@websocket_api.websocket_command(
    {
        vol.Required("type"): "abode_security/actions/list",
    }
)
@websocket_api.async_response
async def websocket_actions_list(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle listing all actions."""
    action_manager = _get_action_manager(hass)
    if action_manager is None:
        connection.send_error(msg["id"], "not_ready", "Action manager not initialized")
        return

    actions = await action_manager.async_get_all()
    connection.send_result(
        msg["id"],
        {"actions": [action.to_dict() for action in actions]},
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "abode_security/actions/get",
        vol.Required("action_id"): str,
    }
)
@websocket_api.async_response
async def websocket_actions_get(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle getting a single action by ID."""
    action_manager = _get_action_manager(hass)
    if action_manager is None:
        connection.send_error(msg["id"], "not_ready", "Action manager not initialized")
        return

    action = await action_manager.async_get(msg["action_id"])
    if action is None:
        connection.send_error(
            msg["id"], "not_found", f"Action {msg['action_id']} not found"
        )
        return

    connection.send_result(msg["id"], action.to_dict())


@websocket_api.websocket_command(
    {
        vol.Required("type"): "abode_security/actions/create",
        vol.Required("name"): str,
        vol.Required("modes"): vol.All(
            [vol.In(VALID_MODES)],
            vol.Length(min=1),
        ),
        vol.Required("sensor_entity_ids"): vol.All(
            [str],
            vol.Length(min=1),
        ),
        vol.Required("alarm_entity_ids"): vol.All(
            [str],
            vol.Length(min=1),
        ),
        vol.Optional("delay_seconds", default=0): vol.All(
            int, vol.Range(min=0, max=60)
        ),
    }
)
@require_admin
@websocket_api.async_response
async def websocket_actions_create(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle creating a new action."""
    action_manager = _get_action_manager(hass)
    if action_manager is None:
        connection.send_error(msg["id"], "not_ready", "Action manager not initialized")
        return

    try:
        action = await action_manager.async_create(
            name=msg["name"],
            modes=msg["modes"],
            sensor_entity_ids=msg["sensor_entity_ids"],
            alarm_entity_ids=msg["alarm_entity_ids"],
            delay_seconds=msg.get("delay_seconds", 0),
        )
        _LOGGER.info("Action %s created by user %s", action.id, connection.user.id)
        connection.send_result(msg["id"], action.to_dict())
    except ValueError as err:
        connection.send_error(msg["id"], "validation_error", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "abode_security/actions/update",
        vol.Required("action_id"): str,
        vol.Optional("name"): str,
        vol.Optional("modes"): vol.All(
            [vol.In(VALID_MODES)],
            vol.Length(min=1),
        ),
        vol.Optional("sensor_entity_ids"): vol.All(
            [str],
            vol.Length(min=1),
        ),
        vol.Optional("alarm_entity_ids"): vol.All(
            [str],
            vol.Length(min=1),
        ),
        vol.Optional("delay_seconds"): vol.All(int, vol.Range(min=0, max=60)),
        vol.Optional("enabled"): bool,
    }
)
@require_admin
@websocket_api.async_response
async def websocket_actions_update(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle updating an existing action."""
    action_manager = _get_action_manager(hass)
    if action_manager is None:
        connection.send_error(msg["id"], "not_ready", "Action manager not initialized")
        return

    action_id = msg["action_id"]

    # Build update kwargs from optional fields
    update_fields = {}
    for field in [
        "name",
        "modes",
        "sensor_entity_ids",
        "alarm_entity_ids",
        "delay_seconds",
        "enabled",
    ]:
        if field in msg:
            update_fields[field] = msg[field]

    try:
        action = await action_manager.async_update(action_id, **update_fields)
        if action is None:
            connection.send_error(
                msg["id"], "not_found", f"Action {action_id} not found"
            )
            return

        _LOGGER.info("Action %s updated by user %s", action.id, connection.user.id)
        connection.send_result(msg["id"], action.to_dict())
    except ValueError as err:
        connection.send_error(msg["id"], "validation_error", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "abode_security/actions/delete",
        vol.Required("action_id"): str,
    }
)
@require_admin
@websocket_api.async_response
async def websocket_actions_delete(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle deleting an action."""
    action_manager = _get_action_manager(hass)
    if action_manager is None:
        connection.send_error(msg["id"], "not_ready", "Action manager not initialized")
        return

    action_id = msg["action_id"]
    result = await action_manager.async_delete(action_id)

    if not result:
        connection.send_error(msg["id"], "not_found", f"Action {action_id} not found")
        return

    _LOGGER.info("Action %s deleted by user %s", action_id, connection.user.id)
    connection.send_result(msg["id"], {"success": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "abode_security/actions/toggle",
        vol.Required("action_id"): str,
    }
)
@require_admin
@websocket_api.async_response
async def websocket_actions_toggle(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle toggling an action's enabled state."""
    action_manager = _get_action_manager(hass)
    if action_manager is None:
        connection.send_error(msg["id"], "not_ready", "Action manager not initialized")
        return

    action_id = msg["action_id"]
    action = await action_manager.async_toggle(action_id)

    if action is None:
        connection.send_error(msg["id"], "not_found", f"Action {action_id} not found")
        return

    _LOGGER.info(
        "Action %s toggled to %s by user %s",
        action.id,
        action.enabled,
        connection.user.id,
    )
    connection.send_result(msg["id"], action.to_dict())


@websocket_api.websocket_command(
    {
        vol.Required("type"): "abode_security/actions/test",
        vol.Required("action_id"): str,
    }
)
@require_admin
@websocket_api.async_response
async def websocket_actions_test(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle testing an action (manually trigger alarms)."""
    action_manager = _get_action_manager(hass)
    if action_manager is None:
        connection.send_error(msg["id"], "not_ready", "Action manager not initialized")
        return

    action_id = msg["action_id"]
    action = await action_manager.async_get(action_id)

    if action is None:
        connection.send_error(msg["id"], "not_found", f"Action {action_id} not found")
        return

    _LOGGER.info("Action %s tested by user %s", action_id, connection.user.id)

    # Trigger each alarm switch
    alarms_triggered = []
    for alarm_entity_id in action.alarm_entity_ids:
        try:
            await hass.services.async_call(
                "switch",
                "turn_on",
                {"entity_id": alarm_entity_id},
                blocking=True,
            )
            alarms_triggered.append(alarm_entity_id)
        except (HomeAssistantError, ServiceNotFound, ValueError) as err:
            _LOGGER.warning("Failed to trigger alarm %s: %s", alarm_entity_id, err)

    connection.send_result(
        msg["id"],
        {"success": True, "alarms_triggered": alarms_triggered},
    )
