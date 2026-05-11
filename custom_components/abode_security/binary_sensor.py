"""Support for Abode Security System binary sensors."""

from __future__ import annotations

from typing import cast

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.enum import try_parse_enum

from .abode.devices.binary_sensor import BinarySensor
from .entity import AbodeDevice
from .models import AbodeSystem

PARALLEL_UPDATES = 1


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Abode binary sensor devices."""
    data: AbodeSystem = entry.runtime_data

    device_types = [
        "connectivity",
        "moisture",
        "motion",
        "occupancy",
        "door",
    ]

    async_add_entities(
        AbodeBinarySensor(data, device)
        for device in await data.abode.get_devices(generic_type=device_types)
    )


class AbodeBinarySensor(AbodeDevice, BinarySensorEntity):
    """A binary sensor implementation for Abode device."""

    _attr_name = None
    _device: BinarySensor

    def __init__(self, data: AbodeSystem, device: BinarySensor) -> None:
        """Initialize a binary sensor for an Abode device."""
        # `is_window` / `generic_type` are device-shape signals that don't
        # change post-discovery, so device_class is fixed at construction.
        if device.get_value("is_window") == "1":
            self._attr_device_class = BinarySensorDeviceClass.WINDOW
        else:
            self._attr_device_class = try_parse_enum(
                BinarySensorDeviceClass, device.generic_type
            )
        super().__init__(data, device)

    def _sync_attrs(self) -> None:
        """Mirror current device state into `_attr_is_on` (plus base attrs)."""
        super()._sync_attrs()
        self._attr_is_on = cast(bool, self._device.is_on)
