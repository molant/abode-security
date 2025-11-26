"""Support for the Abode Security System locks."""

from __future__ import annotations

from typing import Any

from abode.devices.lock import Lock
from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import _vendor  # noqa: F401
from .entity import AbodeDevice
from .models import AbodeSystem

PARALLEL_UPDATES = 1


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Abode lock devices."""
    data: AbodeSystem = entry.runtime_data

    async_add_entities(
        AbodeLock(data, device)
        for device in await data.abode.get_devices(generic_type="lock")
    )


class AbodeLock(AbodeDevice, LockEntity):
    """Representation of an Abode lock."""

    _device: Lock
    _attr_name = None

    async def async_lock(self, **_kwargs: Any) -> None:
        """Lock the device."""
        await self._device.lock()

    async def async_unlock(self, **_kwargs: Any) -> None:
        """Unlock the device."""
        await self._device.unlock()

    @property
    def is_locked(self) -> bool:
        """Return true if device is on."""
        return bool(self._device.is_locked)
