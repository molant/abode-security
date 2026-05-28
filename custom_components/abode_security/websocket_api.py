"""WebSocket API for Abode Security frontend panel."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any, cast

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api.decorators import (
    async_response,
    require_admin,
    websocket_command,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceNotFound
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .action_manager import (
    MAX_DELAY_SECONDS,
    MAX_NAME_LENGTH,
    VALID_MODES,
)
from .const import CONF_DEBUG_LOGGING, DOMAIN
from .helpers import find_abode_alarm_panel
from .websocket_schedules import (
    websocket_schedules_create,
    websocket_schedules_delete,
    websocket_schedules_get,
    websocket_schedules_list,
    websocket_schedules_update,
)

# Defense-in-depth upper bounds for websocket action payloads. The frontend is
# trusted but not assumed correct — these caps stop a buggy or hostile client
# from submitting payloads that pass schema and then blow up JSON serialization
# or HA storage. Sized for a generous residential install (a typical Abode
# deployment has well under 20 binary sensors and a handful of alarm switches);
# raise them if a real user genuinely hits the ceiling.
_MAX_SENSOR_ENTITY_IDS = 64
_MAX_ALARM_ENTITY_IDS = 16

# Curated mapping from camera-style `translation_key`s (UniFi Protect, Reolink,
# and similar) to a stable "semantic category" used by the picker. Entities in
# HA with NO `device_class` would otherwise all collapse into the generic
# "other" bucket; this gives person/vehicle/smoke-alarm/etc. their own group
# so users can pick them as action triggers (#135).
#
# Keys are matched case-insensitively against `entity_registry.translation_key`.
# When two integrations use different conventions for the same concept (e.g.
# UniFi's `person_detected` vs Reolink's `person`), both map to the same
# semantic key (`person`).
_TRANSLATION_KEY_TO_CATEGORY: dict[str, str] = {
    # Person
    "person": "person",
    "person_detected": "person",
    "crossline_person": "person",
    "intrusion_person": "person",
    "linger_person": "person",
    # Vehicle
    "vehicle": "vehicle",
    "vehicle_detected": "vehicle",
    "non-motor_vehicle": "vehicle",
    "crossline_vehicle": "vehicle",
    "intrusion_vehicle": "vehicle",
    "linger_vehicle": "vehicle",
    # Animal / pet
    "animal": "animal",
    "animal_detected": "animal",
    "pet": "animal",
    # Object (generic camera smart-detect)
    "object_detected": "object",
    "audio_object_detected": "object",
    # Package
    "package": "package",
    "package_detected": "package",
    # Smoke / CO
    "smoke_alarm_detected": "smoke_alarm",
    "co_alarm_detected": "co_alarm",
    # Audio
    "speaking_detected": "speaking",
    "barking_detected": "barking",
    "baby_cry_detected": "baby_cry",
    "cry": "baby_cry",
    "glass_break_detected": "glass_break",
    "siren_detected": "siren",
    # Misc
    "face": "face",
    "visitor": "visitor",
}

# Fallback token match against the entity_id's object portion (e.g.
# `binary_sensor.front_yard_person_detected` → object portion
# `front_yard_person_detected`). Only consulted when `translation_key` produced
# no hit, so integrations that DO use translation_key always win.
#
# Matching is *token-aware*: each entry matches when the token appears at a
# `_` / start-of-string / end-of-string boundary, so `pet` lands `pet_detected`
# and `front_yard_pet` but NOT `carpet` or `puppet`. This is the boundary fix
# from PR #143 review — a previous bare-substring version both over-matched
# (carpet → animal) and under-matched (pet_detected → other).
#
# Order matters: the first token that matches decides the category, so list
# multi-word tokens (e.g. `smoke_alarm`) before single-word tokens that share
# a prefix.
_ENTITY_ID_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("smoke_alarm", "smoke_alarm"),
    ("co_alarm", "co_alarm"),
    ("glass_break", "glass_break"),
    ("baby_cry", "baby_cry"),
    ("siren_detected", "siren"),
    ("face_detected", "face"),
    ("speaking", "speaking"),
    ("barking", "barking"),
    ("visitor", "visitor"),
    ("package", "package"),
    ("person", "person"),
    ("vehicle", "vehicle"),
    ("animal", "animal"),
    ("pet", "animal"),
    ("object", "object"),
)

# Compiled once at module load — each entry matches the token at a `_` or
# string boundary. The token itself is `re.escape`d so any future hyphen /
# regex-meta token (e.g. `non-motor`) stays literal.
_ENTITY_ID_KEYWORD_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(rf"(?:^|_){re.escape(token)}(?:$|_)"), category)
    for token, category in _ENTITY_ID_KEYWORDS
)


def _categorize_sensor(
    entity_id: str,
    device_class: str | None,
    translation_key: str | None,
) -> str:
    """Pick a picker-category for a binary_sensor.

    Priority:
      1. A real `device_class` (door, motion, smoke, …) — never overridden.
      2. `translation_key` (UniFi Protect / Reolink and similar HA-native
         naming) mapped via `_TRANSLATION_KEY_TO_CATEGORY`.
      3. A keyword in the entity_id's object portion (Frigate, templates that
         don't bother with translation_key).
      4. "other" — the existing catch-all.
    """
    if device_class:
        return device_class

    if translation_key:
        category = _TRANSLATION_KEY_TO_CATEGORY.get(translation_key.lower())
        if category is not None:
            return category

    # entity_id format is `<domain>.<object_id>` — match only against the
    # object_id so a domain rename can't accidentally trigger a keyword.
    object_id = (
        entity_id.split(".", 1)[1].lower() if "." in entity_id else entity_id.lower()
    )
    for pattern, category in _ENTITY_ID_KEYWORD_PATTERNS:
        if pattern.search(object_id):
            return category

    return "other"


def _non_bool_int(value: object) -> int:
    """Voluptuous validator: accept ints, reject bools.

    ``bool`` is a subclass of ``int``, so a plain ``int`` schema would accept
    ``True``/``False`` and silently coerce them to 1/0 on persistence. That
    diverges from ``ActionStore.from_dict``, which explicitly rejects bools
    for ``delay_seconds`` and would later drop the record as corrupt. Reject
    here so the three layers (schema / manager validate / load) agree.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise vol.Invalid("expected int (not bool)")
    return value


if TYPE_CHECKING:
    from homeassistant.components.websocket_api.connection import ActiveConnection

    from .action_manager import ActionManager
    from .config_store import ConfigStore

_LOGGER = logging.getLogger(__name__)


def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register WebSocket commands for Abode Security.

    Admin-gating policy (per #52 audit):

    - All mutating commands require admin: `actions/{create,update,delete,
      toggle,test}`, `modes/set`, `config/set`.
    - Read-only commands that expose alarm-system topology (which sensors
      trigger which alarms in which modes) also require admin:
      `actions/{list,get}`, `entities/{sensors,alarms}`. Non-admin users
      should not be able to enumerate the alarm wiring even read-only.
    - Read-only commands that expose only non-sensitive metadata are
      open to any authenticated HA user:
      - `modes/list` returns `{id, name, icon, action_count,
        disabled_action_count, active}` per mode. `active` discloses the
        current armed state, which HA's standard state APIs already
        expose for the Abode `alarm_control_panel` entity (resolved
        dynamically by `find_abode_alarm_panel`), so gating here would
        be security theater. The two counts are counts only, not the
        actions themselves (those go through the gated `actions/*`).
      - `config/get` (currently just `debounce_seconds`). If you add a
        sensitive field to `ConfigStore`, either gate `config/get` or
        split the schema — don't quietly widen what non-admins can
        read.

    If you add a new command, check `@require_admin` matches one of the
    three buckets above. New mutating commands or topology-exposing reads
    MUST add `@require_admin`.
    """
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
    websocket_api.async_register_command(hass, websocket_modes_set)
    websocket_api.async_register_command(hass, websocket_entities_sensors)
    websocket_api.async_register_command(hass, websocket_entities_alarms)
    websocket_api.async_register_command(hass, websocket_entities_cameras)
    # Config endpoints
    websocket_api.async_register_command(hass, websocket_config_get)
    websocket_api.async_register_command(hass, websocket_config_set)
    # Schedule CRUD endpoints
    websocket_api.async_register_command(hass, websocket_schedules_list)
    websocket_api.async_register_command(hass, websocket_schedules_get)
    websocket_api.async_register_command(hass, websocket_schedules_create)
    websocket_api.async_register_command(hass, websocket_schedules_update)
    websocket_api.async_register_command(hass, websocket_schedules_delete)


def _get_action_manager(hass: HomeAssistant) -> ActionManager | None:
    """Get the ActionManager from hass.data."""
    return cast("ActionManager | None", hass.data.get(DOMAIN, {}).get("action_manager"))


# --- Action CRUD Endpoints ---


@websocket_command(
    {
        vol.Required("type"): "abode_security/actions/list",
    }
)
@require_admin
@async_response
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


@websocket_command(
    {
        vol.Required("type"): "abode_security/actions/get",
        vol.Required("action_id"): str,
    }
)
@require_admin
@async_response
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


@websocket_command(
    {
        vol.Required("type"): "abode_security/actions/create",
        # Voluptuous validates shape and the upper-length cap; the
        # "name must not be empty" business rule lives in
        # ActionManager._validate_action so the WS error code stays
        # `validation_error` rather than `invalid_format` (#102).
        vol.Required("name"): vol.All(str, vol.Length(max=MAX_NAME_LENGTH)),
        vol.Required("modes"): vol.All(
            [vol.In(VALID_MODES)],
            vol.Length(min=1, max=len(VALID_MODES)),
        ),
        vol.Required("sensor_entity_ids"): vol.All(
            [cv.entity_id],
            vol.Length(min=1, max=_MAX_SENSOR_ENTITY_IDS),
        ),
        # Empty alarm_entity_ids is allowed: notification-only actions fire the
        # event without arming any switch.
        vol.Required("alarm_entity_ids"): vol.All(
            [cv.entity_id],
            vol.Length(min=0, max=_MAX_ALARM_ENTITY_IDS),
        ),
        vol.Optional("delay_seconds", default=0): vol.All(
            _non_bool_int, vol.Range(min=0, max=MAX_DELAY_SECONDS)
        ),
        vol.Optional("enabled", default=True): bool,
    }
)
@require_admin
@async_response
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
            enabled=msg.get("enabled", True),
        )
        _LOGGER.info("Action %s created by user %s", action.id, connection.user.id)
        connection.send_result(msg["id"], action.to_dict())
    except ValueError as err:
        connection.send_error(msg["id"], "validation_error", str(err))


@websocket_command(
    {
        vol.Required("type"): "abode_security/actions/update",
        vol.Required("action_id"): str,
        # Same shape-vs-business-rule split as the create schema: emptiness
        # is checked at the manager level so the error code is
        # `validation_error` (#102).
        vol.Optional("name"): vol.All(str, vol.Length(max=MAX_NAME_LENGTH)),
        vol.Optional("modes"): vol.All(
            [vol.In(VALID_MODES)],
            vol.Length(min=1, max=len(VALID_MODES)),
        ),
        vol.Optional("sensor_entity_ids"): vol.All(
            [cv.entity_id],
            vol.Length(min=1, max=_MAX_SENSOR_ENTITY_IDS),
        ),
        vol.Optional("alarm_entity_ids"): vol.All(
            [cv.entity_id],
            vol.Length(min=0, max=_MAX_ALARM_ENTITY_IDS),
        ),
        vol.Optional("delay_seconds"): vol.All(
            _non_bool_int, vol.Range(min=0, max=MAX_DELAY_SECONDS)
        ),
        vol.Optional("enabled"): bool,
    }
)
@require_admin
@async_response
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


@websocket_command(
    {
        vol.Required("type"): "abode_security/actions/delete",
        vol.Required("action_id"): str,
    }
)
@require_admin
@async_response
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


@websocket_command(
    {
        vol.Required("type"): "abode_security/actions/toggle",
        vol.Required("action_id"): str,
    }
)
@require_admin
@async_response
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


@websocket_command(
    {
        vol.Required("type"): "abode_security/actions/test",
        vol.Required("action_id"): str,
    }
)
@require_admin
@async_response
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

# Inverse: mode ID → alarm_control_panel service to invoke. The frontend
# panel calls these via websocket_modes_set, which delegates to the standard
# alarm_control_panel domain so we don't duplicate the underlying SDK calls.
MODE_TO_SERVICE = {
    "standby": "alarm_disarm",
    "home": "alarm_arm_home",
    "away": "alarm_arm_away",
}

# Defense-in-depth against drift: voluptuous already gates `mode_id` on
# VALID_MODES, but if VALID_MODES grows and MODE_TO_SERVICE doesn't, the
# `MODE_TO_SERVICE[mode_id]` lookup below would KeyError under a request
# that passed schema validation. Fail at import time instead.
assert set(MODE_TO_SERVICE) == VALID_MODES, (
    "MODE_TO_SERVICE keys must match VALID_MODES exactly"
)


# `find_abode_alarm_panel` (resolves the panel via entity registry, falling
# back to entity_id prefix) lives in `helpers` so `action_trigger` can share
# the same lookup. See helpers.py for the rationale.


@websocket_command(
    {
        vol.Required("type"): "abode_security/modes/list",
    }
)
@async_response
async def websocket_modes_list(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle listing available modes with metadata."""
    action_manager = _get_action_manager(hass)

    # Find the active mode from the abode alarm_control_panel entity, if any.
    panel_state = find_abode_alarm_panel(hass)
    active_mode = STATE_TO_MODE.get(panel_state.state) if panel_state else None

    # Fetch the full action list once, then bucket per mode below.
    # `action_count` stays enabled-only so existing consumers (and trigger
    # semantics) are unchanged; the UI uses `disabled_action_count` to
    # surface disabled actions per #123, which were previously invisible
    # in the mode card badge.
    all_actions = await action_manager.async_get_all() if action_manager else []

    modes = []
    for mode_id in VALID_MODES:
        metadata = MODE_METADATA.get(
            mode_id, {"name": mode_id.title(), "icon": "mdi:help"}
        )

        action_count = sum(
            1 for action in all_actions if action.enabled and mode_id in action.modes
        )
        disabled_action_count = sum(
            1
            for action in all_actions
            if not action.enabled and mode_id in action.modes
        )

        modes.append(
            {
                "id": mode_id,
                "name": metadata["name"],
                "icon": metadata["icon"],
                "action_count": action_count,
                "disabled_action_count": disabled_action_count,
                "active": mode_id == active_mode,
            }
        )

    # Surface the panel entity_id so the frontend can derive the active
    # mode from `hass.states[panel].state` at render time instead of the
    # cached `active` flag (#124). The cached flag is read once at fetch
    # time; SocketIO-driven panel transitions during the 30–60s entry/exit
    # delay arrive later and never propagate to the snapshot.
    connection.send_result(
        msg["id"],
        {
            "modes": modes,
            "panel_entity_id": panel_state.entity_id if panel_state else None,
        },
    )


@websocket_command(
    {
        vol.Required("type"): "abode_security/modes/set",
        vol.Required("mode_id"): vol.In(VALID_MODES),
    }
)
@require_admin
@async_response
async def websocket_modes_set(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Set the active Abode mode by delegating to alarm_control_panel.

    Maps mode_id → alarm_control_panel service:
      standby → alarm_disarm
      home    → alarm_arm_home
      away    → alarm_arm_away

    The frontend Modes tab calls this after a confirm dialog. We don't go
    straight to the Abode SDK because alarm_control_panel already wraps it
    and handles entity-state updates uniformly.
    """
    mode_id = msg["mode_id"]

    panel_state = find_abode_alarm_panel(hass)
    if panel_state is None:
        connection.send_error(
            msg["id"],
            "not_found",
            "No Abode alarm_control_panel entity registered",
        )
        return

    service = MODE_TO_SERVICE[mode_id]

    try:
        await hass.services.async_call(
            "alarm_control_panel",
            service,
            {"entity_id": panel_state.entity_id},
            blocking=True,
        )
    except (HomeAssistantError, ServiceNotFound, ValueError) as err:
        _LOGGER.warning("Failed to set mode %s: %s", mode_id, err)
        connection.send_error(msg["id"], "set_mode_failed", str(err))
        return

    _LOGGER.info("Mode set to %s by user %s", mode_id, connection.user.id)
    connection.send_result(msg["id"], {"success": True, "mode_id": mode_id})


@websocket_command(
    {
        vol.Required("type"): "abode_security/entities/sensors",
    }
)
@require_admin
@async_response
async def websocket_entities_sensors(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle listing all binary sensors grouped by picker category.

    The grouping key is a derived "picker category" rather than a raw HA
    `device_class`: when an entity has a real `device_class`, that wins;
    otherwise the entity is classified by `translation_key` (UniFi Protect /
    Reolink smart-detect entities, see `_TRANSLATION_KEY_TO_CATEGORY`) or by
    a boundary-aware entity_id keyword (see `_ENTITY_ID_KEYWORDS`), falling
    back to `"other"`. See `_categorize_sensor` for the priority order.
    """
    sensors_by_class: dict[str, list[dict[str, Any]]] = {}

    # The area hint surfaced next to each sensor in the panel (#120) prefers
    # the entity-level area; if unset, fall back to the entity's device area.
    # Registries are looked up once up-front (cheap accessors) instead of per
    # sensor.
    entity_reg = er.async_get(hass)
    device_reg = dr.async_get(hass)
    area_reg = ar.async_get(hass)

    for state in hass.states.async_all("binary_sensor"):
        raw_device_class = state.attributes.get("device_class") or None
        friendly_name = state.attributes.get("friendly_name", state.entity_id)

        area_name: str | None = None
        translation_key: str | None = None
        entry = entity_reg.async_get(state.entity_id)
        if entry is not None:
            # Respect entity-registry visibility: skip anything the user
            # (or an integration) has hidden. Disabled entities are
            # already excluded — they don't get a state, so async_all
            # skips them. Sensors without a registry entry (e.g. legacy
            # templates set directly via hass.states.async_set) have no
            # hidden_by signal and stay visible. ARCHITECTURE.md
            # documents the intentional asymmetry with action_trigger,
            # which does NOT filter hidden so existing automations keep
            # firing.
            if entry.hidden_by is not None:
                continue
            translation_key = entry.translation_key
            area_id = entry.area_id
            if area_id is None and entry.device_id is not None:
                device = device_reg.async_get(entry.device_id)
                if device is not None:
                    area_id = device.area_id
            if area_id is not None:
                area = area_reg.async_get_area(area_id)
                if area is not None:
                    area_name = area.name

        # Camera smart-detect entities (UniFi Protect, Reolink, …) have no
        # device_class — they identify themselves via translation_key. Bucket
        # those into semantic categories instead of collapsing into "other"
        # (#135).
        category = _categorize_sensor(
            state.entity_id, raw_device_class, translation_key
        )

        sensor_info = {
            "entity_id": state.entity_id,
            "name": friendly_name,
            "state": state.state,
            "area": area_name,
        }

        if category not in sensors_by_class:
            sensors_by_class[category] = []
        sensors_by_class[category].append(sensor_info)

    # Stable alphabetical order by friendly_name within each picker category.
    # `hass.states.async_all()` returns entities in registration order — fine
    # while the integration is loaded once, but the order shifts on restart
    # or after a new entity registers. Sorting here gives the picker a
    # deterministic layout across reloads, and lets the frontend partition
    # (live before unavailable) preserve a predictable in-half order. Sort
    # case-insensitively so "0x..." Zigbee identifiers don't all clump
    # before "Backyard" — they still come first as a natural consequence of
    # ASCII order, but mixed-case friendly_names interleave correctly.
    for sensors in sensors_by_class.values():
        sensors.sort(key=lambda s: (s["name"] or "").lower())

    connection.send_result(msg["id"], {"sensors": sensors_by_class})


# Alarm types based on entity_id patterns
ALARM_TYPES = {
    "panic": "Panic",
    "fire": "Fire",
    "medical": "Medical",
}


@websocket_command(
    {
        vol.Required("type"): "abode_security/entities/alarms",
    }
)
@require_admin
@async_response
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


@websocket_command(
    {
        vol.Required("type"): "abode_security/entities/cameras",
    }
)
@require_admin
@async_response
async def websocket_entities_cameras(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """List every camera entity in HA for the deep-link Cameras panel.

    The integration is camera-source-agnostic — any HA camera is a valid
    notification deep-link target. The tab renders each camera with HA's
    native <ha-camera-stream> element and opens the standard more-info
    dialog on tap (the same flow as picture-entity card with
    `camera_view: auto` and `tap_action: more-info`), so the response
    only needs identity + display metadata.
    """
    entity_reg = er.async_get(hass)
    device_reg = dr.async_get(hass)
    area_reg = ar.async_get(hass)

    cameras = []
    for entry in entity_reg.entities.values():
        if entry.domain != "camera":
            continue
        if entry.hidden_by is not None:
            continue
        if entry.disabled_by is not None:
            continue

        # Resolve friendly name from state, fall back to entity_id.
        state = hass.states.get(entry.entity_id)
        name: str = entry.entity_id
        if state is not None:
            name = state.attributes.get("friendly_name", entry.entity_id)

        # Area: prefer entity-level, fall back to device-level.
        area_name: str | None = None
        area_id = entry.area_id
        if area_id is None and entry.device_id is not None:
            device = device_reg.async_get(entry.device_id)
            if device is not None:
                area_id = device.area_id
        if area_id is not None:
            area = area_reg.async_get_area(area_id)
            if area is not None:
                area_name = area.name

        cameras.append(
            {
                "entity_id": entry.entity_id,
                "name": name,
                "area": area_name,
            }
        )

    cameras.sort(key=lambda c: (c["name"] or "").lower())
    connection.send_result(msg["id"], {"cameras": cameras})


# --- Config Endpoints ---


def _get_config_store(hass: HomeAssistant) -> ConfigStore | None:
    """Get the ConfigStore from hass.data."""
    return cast("ConfigStore | None", hass.data.get(DOMAIN, {}).get("config_store"))


@websocket_command(
    {
        vol.Required("type"): "abode_security/config/get",
    }
)
@async_response
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

    # Merge in `debug_logging` from the HA ConfigEntry options. It lives there
    # (set via the integration's options flow) rather than in config_store, but
    # the frontend benefits from one fetch — used to gate UI affordances like
    # the "copy action ID" button. Read-only over WS: changes go through HA's
    # options flow, not config/set.
    debug_logging = any(
        entry.options.get(CONF_DEBUG_LOGGING, False)
        for entry in hass.config_entries.async_entries(DOMAIN)
    )
    config = config_store.get_config()
    config["debug_logging"] = debug_logging
    connection.send_result(msg["id"], config)


@websocket_command(
    {
        vol.Required("type"): "abode_security/config/set",
        vol.Optional("debounce_seconds"): vol.All(
            vol.Coerce(float), vol.Range(min=0.1, max=10.0)
        ),
    }
)
@require_admin
@async_response
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
