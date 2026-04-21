"""WebSocket API for Abode Security frontend panel."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api import require_admin
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceNotFound
from homeassistant.helpers import config_validation as cv

from .action_manager import VALID_MODES
from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.components.websocket_api import ActiveConnection

_LOGGER = logging.getLogger(__name__)


def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register WebSocket commands for Abode Security."""
    # Action CRUD endpoints
    websocket_api.async_register_command(hass, websocket_actions_list)
    websocket_api.async_register_command(hass, websocket_actions_get)
    websocket_api.async_register_command(hass, websocket_actions_create)
    websocket_api.async_register_command(hass, websocket_actions_update)
    websocket_api.async_register_command(hass, websocket_actions_delete)
    websocket_api.async_register_command(hass, websocket_actions_toggle)
    websocket_api.async_register_command(hass, websocket_actions_test)
    # Entity query endpoints
    websocket_api.async_register_command(hass, websocket_modes_list)
    websocket_api.async_register_command(hass, websocket_entities_sensors)
    websocket_api.async_register_command(hass, websocket_entities_alarms)
    # Config endpoints
    websocket_api.async_register_command(hass, websocket_config_get)
    websocket_api.async_register_command(hass, websocket_config_set)


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
            [cv.entity_id],
            vol.Length(min=1),
        ),
        vol.Required("alarm_entity_ids"): vol.All(
            [cv.entity_id],
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
            [cv.entity_id],
            vol.Length(min=1),
        ),
        vol.Optional("alarm_entity_ids"): vol.All(
            [cv.entity_id],
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


# --- Entity Query Endpoints ---

# Mode metadata for display
MODE_METADATA = {
    "standby": {"name": "Standby", "icon": "mdi:lock-open"},
    "home": {"name": "Home", "icon": "mdi:home"},
    "away": {"name": "Away", "icon": "mdi:shield-check"},
}

# Mapping from alarm_control_panel states to mode IDs
STATE_TO_MODE = {
    "disarmed": "standby",
    "armed_home": "home",
    "armed_away": "away",
}


@websocket_api.websocket_command(
    {
        vol.Required("type"): "abode_security/modes/list",
    }
)
@websocket_api.async_response
async def websocket_modes_list(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle listing available modes with metadata."""
    action_manager = _get_action_manager(hass)

    # Find the active mode from alarm_control_panel entity
    active_mode = None
    for state in hass.states.async_all("alarm_control_panel"):
        if state.entity_id.startswith("alarm_control_panel.abode"):
            active_mode = STATE_TO_MODE.get(state.state)
            break

    # Build mode list with action counts
    modes = []
    for mode_id in VALID_MODES:
        metadata = MODE_METADATA.get(
            mode_id, {"name": mode_id.title(), "icon": "mdi:help"}
        )

        # Count actions for this mode
        action_count = 0
        if action_manager:
            actions = await action_manager.async_get_by_mode(mode_id)
            action_count = len(actions)

        modes.append(
            {
                "id": mode_id,
                "name": metadata["name"],
                "icon": metadata["icon"],
                "action_count": action_count,
                "active": mode_id == active_mode,
            }
        )

    connection.send_result(msg["id"], {"modes": modes})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "abode_security/entities/sensors",
    }
)
@websocket_api.async_response
async def websocket_entities_sensors(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle listing all binary sensors grouped by device_class."""
    sensors_by_class: dict[str, list[dict[str, Any]]] = {}

    for state in hass.states.async_all("binary_sensor"):
        device_class = state.attributes.get("device_class", "other") or "other"
        friendly_name = state.attributes.get("friendly_name", state.entity_id)

        sensor_info = {
            "entity_id": state.entity_id,
            "name": friendly_name,
            "state": state.state,
        }

        if device_class not in sensors_by_class:
            sensors_by_class[device_class] = []
        sensors_by_class[device_class].append(sensor_info)

    connection.send_result(msg["id"], {"sensors": sensors_by_class})


# Alarm types based on entity_id patterns
ALARM_TYPES = {
    "panic": "Panic",
    "fire": "Fire",
    "medical": "Medical",
}


@websocket_api.websocket_command(
    {
        vol.Required("type"): "abode_security/entities/alarms",
    }
)
@websocket_api.async_response
async def websocket_entities_alarms(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle listing Abode alarm switches."""
    alarms = []

    for state in hass.states.async_all("switch"):
        entity_id = state.entity_id

        # Match Abode alarm switches: switch.abode_*_alarm
        if not entity_id.startswith("switch.abode_") or not entity_id.endswith(
            "_alarm"
        ):
            continue

        # Extract alarm type from entity_id
        # e.g., switch.abode_panic_alarm -> panic
        alarm_type = "unknown"
        for type_key in ALARM_TYPES:
            if type_key in entity_id:
                alarm_type = type_key
                break

        friendly_name = state.attributes.get("friendly_name", entity_id)

        alarms.append(
            {
                "entity_id": entity_id,
                "name": friendly_name,
                "type": alarm_type,
            }
        )

    connection.send_result(msg["id"], {"alarms": alarms})


# --- Config Endpoints ---


def _get_config_store(hass: HomeAssistant):
    """Get the ConfigStore from hass.data."""
    return hass.data.get(DOMAIN, {}).get("config_store")


@websocket_api.websocket_command(
    {
        vol.Required("type"): "abode_security/config/get",
    }
)
@websocket_api.async_response
async def websocket_config_get(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle getting the current configuration."""
    config_store = _get_config_store(hass)
    if config_store is None:
        connection.send_error(msg["id"], "not_ready", "Config store not initialized")
        return

    connection.send_result(msg["id"], config_store.get_config())


@websocket_api.websocket_command(
    {
        vol.Required("type"): "abode_security/config/set",
        vol.Optional("debounce_seconds"): vol.All(
            vol.Coerce(float), vol.Range(min=0.1, max=10.0)
        ),
    }
)
@require_admin
@websocket_api.async_response
async def websocket_config_set(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle updating configuration settings."""
    config_store = _get_config_store(hass)
    if config_store is None:
        connection.send_error(msg["id"], "not_ready", "Config store not initialized")
        return

    # Build update kwargs from optional fields
    update_fields = {}
    if "debounce_seconds" in msg:
        update_fields["debounce_seconds"] = msg["debounce_seconds"]

    if not update_fields:
        # No fields to update, just return current config
        connection.send_result(msg["id"], config_store.get_config())
        return

    try:
        config = await config_store.async_update(**update_fields)
        # Update the cached config in hass.data
        hass.data[DOMAIN]["config"] = config
        _LOGGER.info("Config updated by user %s: %s", connection.user.id, update_fields)
        connection.send_result(msg["id"], config)
    except ValueError as err:
        connection.send_error(msg["id"], "validation_error", str(err))
