"""Diagnostics support for Abode Security."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .models import AbodeSystem
from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    abode_system: AbodeSystem = entry.runtime_data

    try:
        devices = abode_system.abode.get_devices()
        device_count = len(devices) if devices else 0
    except (AttributeError, Exception):
        device_count = 0

    return {
        "polling": abode_system.polling,
        "device_count": device_count,
        "unique_id": entry.unique_id,
    }
