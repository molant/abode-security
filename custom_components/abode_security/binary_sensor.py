"""Support for Abode Security System binary sensors."""

from __future__ import annotations

import logging
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

_LOGGER = logging.getLogger(__name__)


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

    # Last known reporting state, so the log below fires on transitions rather
    # than on every state sync. `None` until the first sync, which keeps setup
    # quiet.
    _was_reporting: bool | None = None

    # The value `_resolve_available` last read off the device, so the log and
    # the availability actually applied are the same observation rather than
    # two adjacent reads.
    _reporting = True

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

    def _resolve_available(self) -> bool:
        """Fold the device's own reporting state into entity availability.

        A sensor that has gone `Offline` (or faulted `no_response`) is holding
        a stale status. Reporting it as `unavailable` rather than letting that
        stale status read as `off` is what stops an offline blip on an open
        window from looking like a fresh `off` -> `on` activation (#210).
        """
        self._reporting = cast(bool, self._device.is_reporting)
        return super()._resolve_available() and self._reporting

    def _sync_attrs(self) -> None:
        """Mirror current device state into `_attr_is_on` (plus base attrs)."""
        super()._sync_attrs()  # resolves availability, refreshing `_reporting`
        self._attr_is_on = cast(bool, self._device.is_on)
        self._log_reporting_transition()

    def _log_reporting_transition(self) -> None:
        """Log when the device starts or stops reporting.

        Making offline sensors unavailable trades a false trigger for possible
        `unavailable` noise; this line is what makes the real-world frequency
        of that tradeoff measurable from the HA log. Reads the value
        `_resolve_available` already resolved, so the logged reason and the
        availability actually applied can't disagree.
        """
        reporting = self._reporting
        if self._was_reporting is not None and reporting != self._was_reporting:
            _LOGGER.info(
                "Abode sensor %s %s reporting (status=%s, no_response=%s)",
                self._device.name,
                "resumed" if reporting else "stopped",
                self._device.status,
                self._device.no_response,
            )
        self._was_reporting = reporting
