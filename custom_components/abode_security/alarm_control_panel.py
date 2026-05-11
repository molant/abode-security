"""Support for Abode Security System alarm control panels."""

from __future__ import annotations

from homeassistant.components.alarm_control_panel import AlarmControlPanelEntity
from homeassistant.components.alarm_control_panel.const import (
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .abode.devices.alarm import Alarm
from .const import LOGGER
from .decorators import handle_abode_errors
from .entity import AbodeDevice
from .models import AbodeSystem


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Abode alarm control panel device."""
    data: AbodeSystem = entry.runtime_data
    alarm = data.abode.get_alarm()
    if alarm is None:
        # Reachable on transient pre-load state or accounts without an alarm
        # device. Skip the panel entity rather than constructing it with None.
        LOGGER.warning("No alarm device available; skipping alarm_control_panel entity")
        return
    async_add_entities([AbodeAlarm(data, alarm)])


class AbodeAlarm(AbodeDevice, AlarmControlPanelEntity):
    """An alarm_control_panel implementation for Abode."""

    _attr_name = None
    _attr_code_arm_required = False
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
    )
    _device: Alarm

    @handle_abode_errors("disarm alarm")
    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        del code  # unused; signature mirrors AlarmControlPanelEntity
        await self._device.set_standby()
        LOGGER.info("Alarm disarmed")

    @handle_abode_errors("arm alarm in home mode")
    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        del code  # unused; signature mirrors AlarmControlPanelEntity
        await self._device.set_home()
        LOGGER.info("Alarm armed in home mode")

    @handle_abode_errors("arm alarm in away mode")
    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        del code  # unused; signature mirrors AlarmControlPanelEntity
        await self._device.set_away()
        LOGGER.info("Alarm armed in away mode")

    @handle_abode_errors("trigger manual alarm")
    async def trigger_manual_alarm(self, alarm_type: str) -> None:
        """Trigger a manual alarm."""
        await self._device.trigger_manual_alarm(alarm_type)
        LOGGER.info("Triggered manual alarm of type: %s", alarm_type)

    @handle_abode_errors("acknowledge timeline event")
    async def acknowledge_timeline_event(self, timeline_id: str) -> None:
        """Acknowledge a timeline alarm event."""
        await self._abode_system.abode.acknowledge_timeline_event(timeline_id)
        LOGGER.info("Acknowledged timeline event: %s", timeline_id)

    @handle_abode_errors("dismiss timeline event")
    async def dismiss_timeline_event(self, timeline_id: str) -> None:
        """Dismiss a timeline alarm event."""
        await self._abode_system.abode.dismiss_timeline_event(timeline_id)
        LOGGER.info("Dismissed timeline event: %s", timeline_id)

    def _sync_attrs(self) -> None:
        """Mirror alarm state and panel-specific attributes into `_attr_*`."""
        # Override base extra_state_attributes entirely: alarm panel exposes
        # battery_backup / cellular_backup instead of the device defaults.
        self._attr_extra_state_attributes = {
            "device_id": self._device.id,
            "battery_backup": self._device.battery,
            "cellular_backup": self._device.is_cellular,
        }
        if self._device.is_standby:
            self._attr_alarm_state = AlarmControlPanelState.DISARMED
        elif self._device.is_away:
            self._attr_alarm_state = AlarmControlPanelState.ARMED_AWAY
        elif self._device.is_home:
            self._attr_alarm_state = AlarmControlPanelState.ARMED_HOME
        else:
            self._attr_alarm_state = None
