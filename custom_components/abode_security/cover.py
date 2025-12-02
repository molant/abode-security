"""Support for Abode Security System covers."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import CoverEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .abode.devices.cover import Cover
from .entity import AbodeDevice
from .models import AbodeSystem

PARALLEL_UPDATES = 1


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Abode cover devices."""
    data: AbodeSystem = entry.runtime_data

    async_add_entities(
        AbodeCover(data, device)
        for device in await data.abode.get_devices(generic_type="cover")
    )


class AbodeCover(AbodeDevice, CoverEntity):
    """Representation of an Abode cover."""

    _device: Cover
    _attr_name = None

    @property
    def is_closed(self) -> bool:
        """Return true if cover is closed, else False."""
        return not self._device.is_open

    async def async_close_cover(self, **_kwargs: Any) -> None:
        """Issue close command to cover."""
        await self._device.close_cover()

    async def async_open_cover(self, **_kwargs: Any) -> None:
        """Issue open command to cover."""
        await self._device.open_cover()
