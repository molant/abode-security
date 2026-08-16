"""Support for the Abode Security System."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

import voluptuous as vol
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .abode.exceptions import Exception as AbodeException
from .const import (
    CONF_DEBUG_LOGGING,
    DOMAIN,
    LOGGER,
    TRIGGERABLE_ALARM_TYPES,
)

if TYPE_CHECKING:
    from .models import AbodeSystem

SERVICE_SETTINGS = "change_setting"
SERVICE_CAPTURE_IMAGE = "capture_image"
SERVICE_TRIGGER_AUTOMATION = "trigger_automation"
SERVICE_TRIGGER_ALARM = "trigger_alarm"
SERVICE_ACKNOWLEDGE_ALARM = "acknowledge_alarm"
SERVICE_DISMISS_ALARM = "dismiss_alarm"
SERVICE_ENABLE_TEST_MODE = "enable_test_mode"
SERVICE_DISABLE_TEST_MODE = "disable_test_mode"
SERVICE_FIRE_TEST_NOTIFICATION = "fire_test_notification"

ATTR_SETTING = "setting"
ATTR_VALUE = "value"
ATTR_ALARM_TYPE = "alarm_type"
ATTR_TIMELINE_ID = "timeline_id"
ATTR_ACTION_ID = "action_id"
ATTR_SENSOR_ENTITY_ID = "sensor_entity_id"
ATTR_MODE = "mode"


CHANGE_SETTING_SCHEMA = vol.Schema(
    {vol.Required(ATTR_SETTING): cv.string, vol.Required(ATTR_VALUE): cv.string}
)

CAPTURE_IMAGE_SCHEMA = vol.Schema({ATTR_ENTITY_ID: cv.entity_ids})

AUTOMATION_SCHEMA = vol.Schema({ATTR_ENTITY_ID: cv.entity_ids})

# Validated here, not just in services.yaml: the `select` selector only shapes
# the UI picker and does nothing for a YAML automation or a REST/WS call.
# Without this, `abode_security.trigger_alarm` with `BURGLAR` still reached the
# API, got a 400, and returned normally — the original silent-failure mode.
TRIGGER_ALARM_SCHEMA = vol.Schema(
    {
        # Strip before Upper: YAML block scalars and templated values routinely
        # carry a trailing newline, and " panic\n" is a legitimate input.
        vol.Required(ATTR_ALARM_TYPE): vol.All(
            cv.string, vol.Strip, vol.Upper, vol.In(sorted(TRIGGERABLE_ALARM_TYPES))
        )
    }
)

ACKNOWLEDGE_ALARM_SCHEMA = vol.Schema({vol.Required(ATTR_TIMELINE_ID): cv.string})

DISMISS_ALARM_SCHEMA = vol.Schema({vol.Required(ATTR_TIMELINE_ID): cv.string})

ENABLE_TEST_MODE_SCHEMA = vol.Schema({})

DISABLE_TEST_MODE_SCHEMA = vol.Schema({})

FIRE_TEST_NOTIFICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ACTION_ID): cv.string,
        vol.Required(ATTR_SENSOR_ENTITY_ID): vol.All(
            cv.entity_id, vol.Match(r"^binary_sensor\.")
        ),
        vol.Optional(ATTR_MODE, default="home"): vol.In(("standby", "home", "away")),
    }
)


def _create_service_handler(
    method_name: str,
    operation_desc: str,
    *arg_extractors: tuple[str, Callable[[ServiceCall], Any]],
    target: str = "abode",
) -> Callable:
    """Factory for creating service handlers with consistent error handling.

    Args:
        method_name: Name of method on target object
        operation_desc: Human-readable description for logging
        arg_extractors: Tuples of (arg_name, extractor_func) for service data
        target: "abode" for abode_system.abode or "system" for abode_system itself

    Returns:
        Service handler function ready to register
    """

    async def handler(call: ServiceCall) -> None:
        abode_system = _get_abode_system(call.hass)
        if not abode_system:
            LOGGER.error("Abode integration not configured")
            return

        try:
            obj = abode_system.abode if target == "abode" else abode_system
            method = getattr(obj, method_name)
            args = [extractor(call) for _, extractor in arg_extractors]
            await method(*args)
            LOGGER.debug(f"Successfully {operation_desc}")
        except AbodeException as ex:
            LOGGER.error(f"Failed to {operation_desc}: %s", ex)

    return handler


def _get_abode_system(hass: HomeAssistant) -> AbodeSystem | None:
    """Get the AbodeSystem from the first available config entry."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.runtime_data:
            return cast("AbodeSystem", entry.runtime_data)
    return None


async def _change_setting(call: ServiceCall) -> None:
    """Change an Abode system setting."""
    setting = call.data[ATTR_SETTING]
    value = call.data[ATTR_VALUE]

    abode_system = _get_abode_system(call.hass)
    if not abode_system:
        LOGGER.error("Abode integration not configured")
        return

    try:
        await abode_system.abode.set_setting(setting, value)
    except AbodeException as ex:
        LOGGER.warning(ex)


async def _capture_image(call: ServiceCall) -> None:
    """Capture a new image.

    This is async so signals are sent from the event loop for thread safety.
    """
    entity_ids = call.data[ATTR_ENTITY_ID]

    abode_system = _get_abode_system(call.hass)
    if not abode_system:
        LOGGER.error("Abode integration not configured")
        return

    target_entities = [
        entity_id for entity_id in abode_system.entity_ids if entity_id in entity_ids
    ]

    for entity_id in target_entities:
        signal = f"abode_camera_capture_{entity_id}"
        async_dispatcher_send(call.hass, signal)


async def _trigger_automation(call: ServiceCall) -> None:
    """Trigger an Abode automation.

    This is async so signals are sent from the event loop for thread safety.
    """
    entity_ids = call.data[ATTR_ENTITY_ID]

    abode_system = _get_abode_system(call.hass)
    if not abode_system:
        LOGGER.error("Abode integration not configured")
        return

    target_entities = [
        entity_id for entity_id in abode_system.entity_ids if entity_id in entity_ids
    ]

    for entity_id in target_entities:
        signal = f"abode_trigger_automation_{entity_id}"
        async_dispatcher_send(call.hass, signal)


def _debug_logging_enabled(hass: HomeAssistant) -> bool:
    """Return True when any Abode config entry has debug_logging enabled."""
    return any(
        entry.options.get(CONF_DEBUG_LOGGING, False)
        for entry in hass.config_entries.async_entries(DOMAIN)
    )


async def _fire_test_notification(call: ServiceCall) -> None:
    """Fire abode_security.action_triggered without arming — debug helper.

    Refuses to run unless the config entry has debug_logging enabled, so the
    service is opt-in even though HA registers it globally at setup time.
    """
    if not _debug_logging_enabled(call.hass):
        LOGGER.warning(
            "fire_test_notification: refused — enable 'debug_logging' in the "
            "integration options to use this service"
        )
        return

    coordinator = call.hass.data.get(DOMAIN, {}).get("action_trigger")
    if coordinator is None:
        LOGGER.error("fire_test_notification: action trigger coordinator not ready")
        return

    action_id = call.data[ATTR_ACTION_ID]
    sensor_entity_id = call.data[ATTR_SENSOR_ENTITY_ID]
    mode = call.data[ATTR_MODE]

    fired = await coordinator.async_fire_test_notification(
        action_id, sensor_entity_id, mode=mode
    )
    if not fired:
        LOGGER.warning(
            "fire_test_notification: did not fire for action=%s sensor=%s",
            action_id,
            sensor_entity_id,
        )


async def _trigger_alarm_handler(call: ServiceCall) -> None:
    """Trigger a manual alarm (special handler for multi-step operation)."""
    alarm_type = call.data[ATTR_ALARM_TYPE]

    # Every failure below raises rather than logging and returning. This
    # service raises a real alarm and contacts a monitoring service; a caller
    # that gets no error is entitled to believe it worked, and an automation
    # built on that assumption fails silently at the worst possible moment.
    # ServiceValidationError for the two "your system isn't set up for this"
    # cases (no stack trace in the log, matches AbodeManualAlarmSwitch), and
    # HomeAssistantError below for a genuine runtime failure. Both subclass
    # HomeAssistantError, so callers can catch either.
    abode_system = _get_abode_system(call.hass)
    if not abode_system:
        raise ServiceValidationError("Abode integration is not configured")

    alarm = abode_system.abode.get_alarm()
    if alarm is None:
        # Reachable during transient pre-load state (panel still initializing,
        # devices not yet fetched) or on accounts without an alarm device.
        raise ServiceValidationError(
            "No Abode alarm device available; cannot trigger a manual alarm"
        )

    try:
        await alarm.trigger_manual_alarm(alarm_type)
    except AbodeException as ex:
        LOGGER.error("Failed to trigger manual alarm: %s", ex)
        raise HomeAssistantError(
            f"Abode refused to trigger a {alarm_type} alarm: {ex}"
        ) from ex

    LOGGER.info("Triggered manual alarm of type: %s", alarm_type)


def setup_services(hass: HomeAssistant) -> None:
    """Set up Home Assistant services.

    Note: This function is synchronous because hass.services.async_register()
    can be called from both sync and async contexts. When called from a sync
    context, it schedules the registrations on the event loop immediately.
    """
    hass.services.async_register(
        DOMAIN, SERVICE_SETTINGS, _change_setting, schema=CHANGE_SETTING_SCHEMA
    )

    hass.services.async_register(
        DOMAIN, SERVICE_CAPTURE_IMAGE, _capture_image, schema=CAPTURE_IMAGE_SCHEMA
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_TRIGGER_AUTOMATION,
        _trigger_automation,
        schema=AUTOMATION_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_TRIGGER_ALARM,
        _trigger_alarm_handler,
        schema=TRIGGER_ALARM_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_ACKNOWLEDGE_ALARM,
        _create_service_handler(
            "acknowledge_timeline_event",
            "acknowledge timeline event",
            ("timeline_id", lambda call: call.data[ATTR_TIMELINE_ID]),
        ),
        schema=ACKNOWLEDGE_ALARM_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_DISMISS_ALARM,
        _create_service_handler(
            "dismiss_timeline_event",
            "dismiss timeline event",
            ("timeline_id", lambda call: call.data[ATTR_TIMELINE_ID]),
        ),
        schema=DISMISS_ALARM_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_ENABLE_TEST_MODE,
        _create_service_handler(
            "set_test_mode",
            "enable test mode",
            ("enabled", lambda _call: True),
            target="system",
        ),
        schema=ENABLE_TEST_MODE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_DISABLE_TEST_MODE,
        _create_service_handler(
            "set_test_mode",
            "disable test mode",
            ("enabled", lambda _call: False),
            target="system",
        ),
        schema=DISABLE_TEST_MODE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_FIRE_TEST_NOTIFICATION,
        _fire_test_notification,
        schema=FIRE_TEST_NOTIFICATION_SCHEMA,
    )
