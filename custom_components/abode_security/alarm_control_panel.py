"""Support for Abode Security System alarm control panels."""

from __future__ import annotations

from . import _vendor  # noqa: F401

from abode.devices.alarm import Alarm

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .models import AbodeSystem
from .const import DOMAIN, LOGGER
from .decorators import handle_abode_errors
from .entity import AbodeDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Abode alarm control panel device."""
    data: AbodeSystem = entry.runtime_data
    async_add_entities(
        [AbodeAlarm(data, await hass.async_add_executor_job(data.abode.get_alarm))]
    )


class AbodeAlarm(AbodeDevice, AlarmControlPanelEntity):
    """An alarm_control_panel implementation for Abode."""

    _attr_name = None
    _attr_code_arm_required = False
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
    )
    _device: Alarm

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the state of the device."""
        if self._device.is_standby:
            return AlarmControlPanelState.DISARMED
        if self._device.is_away:
            return AlarmControlPanelState.ARMED_AWAY
        if self._device.is_home:
            return AlarmControlPanelState.ARMED_HOME
        return None

    def alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        self._device.set_standby()

    def alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        self._device.set_home()

    def alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        self._device.set_away()

    @handle_abode_errors("trigger manual alarm")
    def trigger_manual_alarm(self, alarm_type: str) -> None:
        """Trigger a manual alarm."""
        self._device.trigger_manual_alarm(alarm_type)
        LOGGER.info("Triggered manual alarm of type: %s", alarm_type)

    @handle_abode_errors("acknowledge timeline event")
    def acknowledge_timeline_event(self, timeline_id: str) -> None:
        """Acknowledge a timeline alarm event."""
        self._abode_system.abode.acknowledge_timeline_event(timeline_id)
        LOGGER.info("Acknowledged timeline event: %s", timeline_id)

    @handle_abode_errors("dismiss timeline event")
    def dismiss_timeline_event(self, timeline_id: str) -> None:
        """Dismiss a timeline alarm event."""
        self._abode_system.abode.dismiss_timeline_event(timeline_id)
        LOGGER.info("Dismissed timeline event: %s", timeline_id)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the state attributes."""
        return {
            "device_id": self._device.id,
            "battery_backup": self._device.battery,
            "cellular_backup": self._device.is_cellular,
        }
