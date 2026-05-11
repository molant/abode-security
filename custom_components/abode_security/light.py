"""Support for Abode Security System lights."""

from __future__ import annotations

from math import ceil
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    LightEntity,
)
from homeassistant.components.light.const import (
    DEFAULT_MAX_KELVIN,
    DEFAULT_MIN_KELVIN,
    ColorMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .abode.devices.light import Light
from .decorators import handle_abode_errors
from .entity import AbodeDevice
from .models import AbodeSystem

PARALLEL_UPDATES = 1


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Abode light devices."""
    data: AbodeSystem = entry.runtime_data

    async_add_entities(
        AbodeLight(data, device)
        for device in await data.abode.get_devices(generic_type="light")
    )


class AbodeLight(AbodeDevice, LightEntity):
    """Representation of an Abode light."""

    _device: Light
    _attr_name = None
    _attr_max_color_temp_kelvin = DEFAULT_MAX_KELVIN
    _attr_min_color_temp_kelvin = DEFAULT_MIN_KELVIN

    def __init__(self, data: AbodeSystem, device: Light) -> None:
        """Initialize an Abode light."""
        # `is_dimmable` / `is_color_capable` are device capabilities that
        # don't change at runtime, so the supported color modes can be
        # determined once at construction.
        if device.is_dimmable and device.is_color_capable:
            self._attr_supported_color_modes = {ColorMode.COLOR_TEMP, ColorMode.HS}
        elif device.is_dimmable:
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        else:
            self._attr_supported_color_modes = {ColorMode.ONOFF}
        super().__init__(data, device)

    @handle_abode_errors("set light color temperature")
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        if ATTR_COLOR_TEMP_KELVIN in kwargs and self._device.is_color_capable:
            await self._device.set_color_temp(kwargs[ATTR_COLOR_TEMP_KELVIN])
            return

        if ATTR_HS_COLOR in kwargs and self._device.is_color_capable:
            await self._device.set_color(kwargs[ATTR_HS_COLOR])
            return

        if ATTR_BRIGHTNESS in kwargs and self._device.is_dimmable:
            # Convert Home Assistant brightness (0-255) to Abode brightness (0-99)
            # If 100 is sent to Abode, response is 99 causing an error
            await self._device.set_level(ceil(kwargs[ATTR_BRIGHTNESS] * 99 / 255.0))
            return

        await self._device.switch_on()

    @handle_abode_errors("turn off light")
    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Turn off the light."""
        await self._device.switch_off()

    def _sync_attrs(self) -> None:
        """Mirror current light state into `_attr_*` fields."""
        super()._sync_attrs()
        self._attr_is_on = bool(self._device.is_on)

        # Brightness: Abode reports 0–99 (and 100 transiently during init).
        brightness_attr: int | None
        if self._device.is_dimmable and self._device.has_brightness:
            raw = int(self._device.brightness)
            brightness_attr = 255 if raw == 100 else ceil(raw * 255 / 99.0)
        else:
            brightness_attr = None
        self._attr_brightness = brightness_attr

        # Color: only populated when the device reports color support.
        color_temp_attr: int | None
        hs_color_attr: tuple[float, float] | None
        if self._device.has_color:
            color_temp_attr = int(self._device.color_temp)
            hs_color_attr = self._device.color
        else:
            color_temp_attr = None
            hs_color_attr = None
        self._attr_color_temp_kelvin = color_temp_attr
        self._attr_hs_color = hs_color_attr

        # Color mode: derived from capabilities plus the current hs_color
        # presence (so a color-capable bulb in CT mode reports COLOR_TEMP).
        if self._device.is_dimmable and self._device.is_color_capable:
            self._attr_color_mode = (
                ColorMode.HS
                if self._attr_hs_color is not None
                else ColorMode.COLOR_TEMP
            )
        elif self._device.is_dimmable:
            self._attr_color_mode = ColorMode.BRIGHTNESS
        else:
            self._attr_color_mode = ColorMode.ONOFF
