"""Support for Abode Security System cameras."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any, cast

import aiohttp
from abode.devices.base import Device
from abode.devices.camera import Camera as AbodeCam
from abode.helpers import timeline
from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import Throttle

from . import _vendor  # noqa: F401
from .const import LOGGER
from .entity import AbodeDevice
from .models import AbodeSystem

PARALLEL_UPDATES = 1
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=90)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Abode camera devices."""
    data: AbodeSystem = entry.runtime_data

    async_add_entities(
        AbodeCamera(data, device, timeline.CAPTURE_IMAGE)
        for device in await data.abode.get_devices(generic_type="camera")
    )


class AbodeCamera(AbodeDevice, Camera):
    """Representation of an Abode camera."""

    _device: AbodeCam
    _attr_name = None

    def __init__(self, data: AbodeSystem, device: Device, event: Event) -> None:
        """Initialize the Abode device."""
        AbodeDevice.__init__(self, data, device)
        Camera.__init__(self)
        self._event = event
        self._image_content: bytes | None = None

    async def async_added_to_hass(self) -> None:
        """Subscribe Abode events."""
        await super().async_added_to_hass()

        # Wrap the async callback since add_timeline_callback expects sync callbacks
        def sync_capture_wrapper(capture: Any) -> None:
            """Sync wrapper to schedule async capture callback."""
            # Use Home Assistant's async_create_task for proper cleanup on removal
            self.hass.async_create_task(self._capture_callback(capture))

        try:
            await asyncio.wait_for(
                self.hass.async_add_executor_job(
                    self._data.abode.events.add_timeline_callback,
                    self._event,
                    sync_capture_wrapper,
                ),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            pass  # Timeout on timeline callback registration is non-critical

        signal = f"abode_camera_capture_{self.entity_id}"
        self.async_on_remove(async_dispatcher_connect(self.hass, signal, self.capture))

    def capture(self) -> bool:
        """Request a new image capture."""
        # Use Home Assistant's async_create_task for proper cleanup on removal
        self.hass.async_create_task(self._async_capture())
        return True  # Return True to indicate task was scheduled

    async def _async_capture(self) -> None:
        """Capture image asynchronously."""
        try:
            await self._device.capture()
        except Exception as ex:
            LOGGER.debug("Failed to capture image: %s", ex)

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def refresh_image(self) -> None:
        """Find a new image on the timeline."""
        # Use Home Assistant's async_create_task for proper cleanup on removal
        # This returns immediately while the coroutine runs in the event loop
        self.hass.async_create_task(self._async_refresh_image())

    async def _async_refresh_image(self) -> None:
        """Async version of refresh_image."""
        try:
            if await self._device.refresh_image():
                await self._async_get_image()
        except Exception as ex:
            LOGGER.debug("Failed to refresh image: %s", ex)

    async def _async_get_image(self) -> None:
        """Attempt to download the most recent capture asynchronously."""
        if self._device.image_url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        self._device.image_url,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as response:
                        response.raise_for_status()
                        self._image_content = await response.read()
            except aiohttp.ClientError as err:
                LOGGER.warning("Failed to get camera image: %s", err)
                self._image_content = None
        else:
            self._image_content = None

    def camera_image(
        self, _width: int | None = None, _height: int | None = None
    ) -> bytes | None:
        """Get a camera image."""
        self.refresh_image()

        if self._image_content:
            return self._image_content

        return None

    def turn_on(self) -> None:
        """Turn on camera."""
        # Use Home Assistant's async_create_task for proper cleanup on removal
        self.hass.async_create_task(self._async_privacy_mode(False))

    def turn_off(self) -> None:
        """Turn off camera."""
        # Use Home Assistant's async_create_task for proper cleanup on removal
        self.hass.async_create_task(self._async_privacy_mode(True))

    async def _async_privacy_mode(self, enable: bool) -> None:
        """Set privacy mode asynchronously."""
        try:
            await self._device.privacy_mode(enable)
        except Exception as ex:
            LOGGER.debug("Failed to set privacy mode: %s", ex)

    async def _capture_callback(self, capture: Any) -> None:
        """Update the image with the device then refresh device asynchronously."""
        try:
            await self._device.update_image_location(capture)
            await self._async_get_image()
            self.schedule_update_ha_state()
        except Exception as ex:
            LOGGER.debug("Failed to update image from capture: %s", ex)

    @property
    def is_on(self) -> bool:
        """Return true if on."""
        return cast(bool, self._device.is_on)
