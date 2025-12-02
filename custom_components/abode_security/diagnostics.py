"""Diagnostics support for Abode Security."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .models import AbodeSystem


async def async_get_config_entry_diagnostics(
    _hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    abode_system: AbodeSystem = entry.runtime_data

    # Collect device information
    try:
        devices = await abode_system.abode.get_devices()
        device_count = len(devices) if devices else 0
        device_types: dict[str, int] = {}
        if devices:
            for device in devices:
                device_type = getattr(device, "type", "unknown")
                device_types[device_type] = device_types.get(device_type, 0) + 1
    except (AttributeError, TypeError, ValueError, KeyError):
        device_count = 0
        device_types = {}

    # Collect automation information
    try:
        automations = await abode_system.abode.get_automations()
        automation_count = len(automations) if automations else 0
    except (AttributeError, TypeError, ValueError, KeyError):
        automation_count = 0

    # Collect alarm information
    try:
        alarm = abode_system.abode.get_alarm()
        alarm_status = {
            "status": "available",
            "type": getattr(alarm, "type", "unknown"),
            "battery": getattr(alarm, "battery", "unknown"),
        }
    except (AttributeError, TypeError, ValueError):
        alarm_status = {"status": "unavailable"}

    # Collect connectivity status
    try:
        is_connected = abode_system.abode.events.connected
        connection_status = "connected" if is_connected else "disconnected"
    except (AttributeError, TypeError):
        connection_status = "unknown"

    # Collect event capability information
    has_event_support = False
    has_timeline_support = False
    try:
        has_event_support = hasattr(abode_system.abode.events, "add_event_callback")
        # Check for timeline support
        try:
            from .abode.helpers.timeline import Groups  # noqa: F401

            has_timeline_support = True
        except ImportError:
            has_timeline_support = False
    except AttributeError:
        pass

    return {
        "polling": abode_system.polling,
        "polling_interval": abode_system.polling_interval,
        "enable_events": abode_system.enable_events,
        "retry_count": abode_system.retry_count,
        "connection_status": connection_status,
        "device_count": device_count,
        "device_types": device_types,
        "automation_count": automation_count,
        "alarm": alarm_status,
        "capabilities": {
            "event_callbacks": has_event_support,
            "timeline_support": has_timeline_support,
        },
        "unique_id": entry.unique_id,
    }
