"""Support for Abode Security System entities."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable
from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .abode.automation import Automation as AbodeAuto
from .abode.devices.alarm import Alarm as AbodeAlarm
from .abode.devices.base import Device as AbodeDev
from .const import ATTRIBUTION, DOMAIN
from .models import AbodeSystem

# Subclasses extend `_sync_attrs` to mirror platform-specific state into
# `_attr_*` fields (e.g. `_attr_is_on`, `_attr_brightness`). The base class
# resolves `extra_state_attributes` and `device_info` through `_attr_*` rather
# than `@property` overrides so that pyright's `reportIncompatibleVariableOverride`
# stays quiet against HA-2025's cached_property-backed entity base classes (#70).


class AbodeEntity(Entity):
    """Representation of an Abode entity."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    # SocketIO connectivity, the only availability signal the base class has.
    # Assumed up until the connection callback says otherwise, so entities
    # don't start out unavailable before the first event arrives.
    _connection_available = True

    def __init__(self, data: AbodeSystem) -> None:
        """Initialize Abode entity."""
        self._data = data
        self._attr_should_poll = data.polling
        self._abode_system = data

    async def _run_executor_with_timeout(
        self, fn: Callable[..., Any], *args: Any
    ) -> None:
        """Run a sync callable in the executor, suppressing TimeoutError.

        Mirrors the 10s wait/suppress pattern used across Abode
        subscribe/unsubscribe callbacks so we don't block HA's event loop on
        a slow Abode call.
        """
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(
                self.hass.async_add_executor_job(fn, *args),
                timeout=10.0,
            )

    async def async_added_to_hass(self) -> None:
        """Subscribe to Abode connection status updates."""
        await self._run_executor_with_timeout(
            self._data.abode.events.add_connection_status_callback,
            self.unique_id,
            self._update_connection_status,
        )
        self._abode_system.entity_ids.add(self.entity_id)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from Abode connection status updates."""
        await self._run_executor_with_timeout(
            self._data.abode.events.remove_connection_status_callback,
            self.unique_id,
        )

    def _resolve_available(self) -> bool:
        """Resolve availability from every signal this entity tracks.

        Subclasses extend this to fold in per-device signals (e.g. a sensor
        that has dropped off the RF network). Within `AbodeEntity` and
        `AbodeDevice` both writers of `_attr_available` — the SocketIO
        callback and the device-state sync — go through here, so neither can
        clobber the other's half of the answer (#210).

        `switch.py` predates this and still assigns `_attr_available`
        directly on its alarm-attached switches, so a CMS switch that marked
        itself unavailable after repeated poll errors is still reset by the
        next connection-status callback. Migrating those to an override here
        would fix that; it is out of scope for #210.
        """
        return self._connection_available

    def _update_connection_status(self) -> None:
        """Update the entity available property."""
        self._connection_available = self._data.abode.events.connected
        self._attr_available = self._resolve_available()
        self.schedule_update_ha_state()


class AbodeDevice(AbodeEntity):
    """Representation of an Abode device."""

    def __init__(self, data: AbodeSystem, device: AbodeDev) -> None:
        """Initialize Abode device."""
        super().__init__(data)
        self._device = device
        self._attr_unique_id = device.uuid
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device.id)},
            manufacturer="Abode",
            model=self._device.type,
            name=self._device.name,
            sw_version="1.0.0",
        )
        self._sync_attrs()

    async def async_added_to_hass(self) -> None:
        """Subscribe to device events."""
        await super().async_added_to_hass()
        await self._run_executor_with_timeout(
            self._data.abode.events.add_device_callback,
            self._device.id,
            self._update_callback,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from device events."""
        await super().async_will_remove_from_hass()
        await self._run_executor_with_timeout(
            self._data.abode.events.remove_all_device_callbacks, self._device.id
        )

    async def async_update(self) -> None:
        """Update device state."""
        await self._device.refresh()
        self._sync_attrs()

    def _sync_attrs(self) -> None:
        """Refresh `_attr_*` fields from current device state.

        Subclasses extend this to mirror platform-specific attributes
        (e.g. `_attr_is_on` on switches). Called from `__init__`,
        `async_update`, and `_update_callback`.
        """
        self._attr_extra_state_attributes = {
            "device_id": self._device.id,
            "battery_low": self._device.battery_low,
            "no_response": self._device.no_response,
            "device_type": self._device.type,
        }
        self._attr_available = self._resolve_available()

    def _update_callback(self, _device: AbodeDev) -> None:
        """Update the device state."""
        self._sync_attrs()
        self.schedule_update_ha_state()


class AbodeAlarmAttachedEntity(AbodeEntity):
    """Base for entities anchored to the alarm device, not a physical sensor.

    Used by manual-alarm, CMS-setting, and test-mode switches: they all hang
    off the alarm panel rather than a separate Abode device, so they share a
    single canonical `device_info` here. Keeping it in one place avoids the
    per-class drift that produced issue #8 (one copy missing `sw_version`).
    """

    def __init__(self, data: AbodeSystem, alarm: AbodeAlarm) -> None:
        """Initialize an alarm-attached entity."""
        super().__init__(data)
        self._alarm = alarm
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._alarm.id)},
            manufacturer="Abode",
            model=self._alarm.type,
            name=self._alarm.name,
            sw_version="1.0.0",
        )


class AbodeAutomation(AbodeEntity):
    """Representation of an Abode automation."""

    def __init__(self, data: AbodeSystem, automation: AbodeAuto) -> None:
        """Initialize for Abode automation."""
        super().__init__(data)
        self._automation = automation
        self._attr_name = automation.name
        self._attr_unique_id = automation.id
        self._attr_extra_state_attributes = {
            "type": "CUE automation",
        }

    async def async_update(self) -> None:
        """Update automation state."""
        await self._automation.refresh()
