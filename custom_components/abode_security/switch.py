"""Support for Abode Security System switches."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from abode.devices.alarm import Alarm
from abode.devices.switch import Switch
from abode.exceptions import Exception as AbodeException
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import _vendor  # noqa: F401
from .const import DOMAIN, LOGGER
from .decorators import handle_abode_errors
from .entity import AbodeAutomation, AbodeDevice
from .models import AbodeSystem

PARALLEL_UPDATES = 1

try:
    from abode.helpers.timeline import Groups as TimelineGroups
except ImportError:
    TimelineGroups = None

DEVICE_TYPES = ["switch", "valve"]

# Manual alarm types
MANUAL_ALARM_TYPES = ["PANIC", "SILENT_PANIC", "MEDICAL", "CO", "SMOKE_CO", "SMOKE", "BURGLAR"]

# Map alarm types to their event codes
# These codes are from abode.helpers.events.csv
ALARM_TYPE_EVENT_CODES = {
    "PANIC": ["1120"],  # Panic Alert
    "SILENT_PANIC": ["1122"],  # Silent Panic Alert
    "MEDICAL": ["1100"],  # Medical
    "CO": ["1162"],  # CO Detected
    "SMOKE_CO": ["1110", "1162"],  # Fire Alert + CO Detected
    "SMOKE": ["1111"],  # Smoke Detected
    "BURGLAR": ["1133"],  # Burglar Alarm Triggered
}


def _map_event_code_to_alarm_type(event_code: str, alarm_type: str) -> bool:
    """Check if event code matches the alarm type.

    Args:
        event_code: Numeric event code from Abode API
        alarm_type: The alarm type to check against

    Returns:
        True if the event code matches this alarm type
    """
    expected_codes = ALARM_TYPE_EVENT_CODES.get(alarm_type, [])
    return event_code in expected_codes


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Abode switch devices."""
    data: AbodeSystem = entry.runtime_data

    entities: list[SwitchEntity] = [
        AbodeSwitch(data, device)
        for device_type in DEVICE_TYPES
        for device in await data.abode.get_devices(generic_type=device_type)
    ]

    entities.extend(
        AbodeAutomationSwitch(data, automation)
        for automation in await data.abode.get_automations()
    )

    # Add manual alarm switches
    alarm = data.abode.get_alarm()
    entities.extend(
        AbodeManualAlarmSwitch(data, alarm, alarm_type)
        for alarm_type in MANUAL_ALARM_TYPES
    )

    # Add test mode switch (wrapper methods handle missing methods gracefully)
    entities.append(AbodeTestModeSwitch(data, alarm))

    async_add_entities(entities)


class AbodeSwitch(AbodeDevice, SwitchEntity):
    """Representation of an Abode switch."""

    _device: Switch
    _attr_name = None

    @handle_abode_errors("turn on switch device")
    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Turn on the device."""
        await self._device.switch_on()
        LOGGER.info("Switch device turned on")

    @handle_abode_errors("turn off switch device")
    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Turn off the device."""
        await self._device.switch_off()
        LOGGER.info("Switch device turned off")

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return cast(bool, self._device.is_on)


class AbodeAutomationSwitch(AbodeAutomation, SwitchEntity):
    """A switch implementation for Abode automations."""

    _attr_translation_key = "automation"

    async def async_added_to_hass(self) -> None:
        """Set up trigger automation service."""
        await super().async_added_to_hass()

        signal = f"abode_trigger_automation_{self.entity_id}"

        # Create a synchronous wrapper for the async trigger callback
        # This allows async_dispatcher_connect to properly handle the async method
        def _trigger_wrapper() -> None:
            """Wrapper to schedule async trigger as a task."""
            self.hass.async_create_task(self.trigger())

        self.async_on_remove(async_dispatcher_connect(self.hass, signal, _trigger_wrapper))

    @handle_abode_errors("enable automation")
    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Enable the automation."""
        await self._automation.enable(True)
        LOGGER.info("Automation enabled")
        self.async_write_ha_state()

    @handle_abode_errors("disable automation")
    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Disable the automation."""
        await self._automation.enable(False)
        LOGGER.info("Automation disabled")
        self.async_write_ha_state()

    @handle_abode_errors("trigger automation")
    async def trigger(self) -> None:
        """Trigger the automation."""
        await self._automation.trigger()
        LOGGER.info("Automation triggered")

    @property
    def is_on(self) -> bool:
        """Return True if the automation is enabled."""
        return bool(self._automation.enabled)


class AbodeManualAlarmSwitch(SwitchEntity):
    """A switch for triggering and dismissing manual alarms."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _device: Alarm
    _alarm_type: str
    _timeline_id: str | None = None
    _is_on: bool = False

    # Icon mapping for alarm types
    ALARM_ICONS = {
        "CO": "mdi:molecule-co",
        "SMOKE_CO": "mdi:molecule-co",
        "MEDICAL": "mdi:hospital",
        "PANIC": "mdi:exclamation-thick",
        "SILENT_PANIC": "mdi:exclamation-thick",
        "SMOKE": "mdi:smoke-detector-alert",
        "BURGLAR": "mdi:alarm-light",
    }

    # Display name mapping for alarm types
    ALARM_NAMES = {
        "CO": "CO Alarm",
        "SMOKE_CO": "Smoke CO Alarm",
        "MEDICAL": "Medical Alarm",
        "PANIC": "Panic Alarm",
        "SILENT_PANIC": "Silent Panic Alarm",
        "SMOKE": "Smoke Alarm",
        "BURGLAR": "Burglar Alarm",
    }

    def __init__(
        self, data: AbodeSystem, device: Alarm, alarm_type: str
    ) -> None:
        """Initialize the manual alarm switch."""
        self._data = data
        self._device = device
        self._alarm_type = alarm_type
        self._attr_unique_id = f"{device.id}-manual-alarm-{alarm_type.lower()}"
        self._attr_name = self.ALARM_NAMES.get(alarm_type, alarm_type.replace('_', ' ').title())
        self._attr_icon = self.ALARM_ICONS.get(alarm_type)
        self._attr_available = True

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information for this entity."""
        return {
            "identifiers": {(DOMAIN, self._device.id)},
            "manufacturer": "Abode",
            "model": self._device.type,
            "name": self._device.name,
        }

    async def _subscribe_to_events(
        self,
        event_group: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> None:
        """Subscribe to Abode timeline events."""
        try:
            await asyncio.wait_for(
                self.hass.async_add_executor_job(
                    self._data.abode.events.add_event_callback,
                    event_group,
                    callback,
                ),
                timeout=10.0,
            )
            LOGGER.debug(f"Subscribed to {event_group} events")
        except asyncio.TimeoutError:
            LOGGER.warning(f"Timeout subscribing to {event_group} events")
        except Exception as ex:
            LOGGER.warning(f"Could not subscribe to {event_group} events: %s", ex)

    async def _unsubscribe_from_events(
        self,
        event_group: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> None:
        """Unsubscribe from Abode timeline events."""
        if not hasattr(self._data.abode.events, "remove_event_callback"):
            LOGGER.debug("remove_event_callback not available, skipping unsubscribe")
            return

        try:
            await asyncio.wait_for(
                self.hass.async_add_executor_job(
                    self._data.abode.events.remove_event_callback,
                    event_group,
                    callback,
                ),
                timeout=10.0,
            )
            LOGGER.debug(f"Unsubscribed from {event_group} events")
        except asyncio.TimeoutError:
            LOGGER.warning(f"Timeout unsubscribing from {event_group} events")
        except Exception as ex:
            LOGGER.warning(f"Could not unsubscribe from {event_group} events: %s", ex)

    async def async_added_to_hass(self) -> None:
        """Subscribe to timeline events when added to Home Assistant."""
        await super().async_added_to_hass()

        if TimelineGroups is None:
            LOGGER.warning("Timeline groups not available, state sync disabled")
            return

        # Subscribe to alarm trigger events
        await self._subscribe_to_events(TimelineGroups.ALARM, self._alarm_event_callback)

        # Subscribe to alarm end/dismiss events
        await self._subscribe_to_events(TimelineGroups.ALARM_END, self._alarm_end_callback)

    async def async_will_remove_from_hass(self) -> None:
        """Clean up event subscriptions when removed."""
        await super().async_will_remove_from_hass()

        if TimelineGroups is None:
            return

        # Remove event callbacks
        await self._unsubscribe_from_events(TimelineGroups.ALARM, self._alarm_event_callback)
        await self._unsubscribe_from_events(TimelineGroups.ALARM_END, self._alarm_end_callback)

    def _alarm_event_callback(self, event: dict[str, Any]) -> None:
        """Handle alarm trigger events from timeline.

        Args:
            event: Timeline event dictionary containing alarm information
        """
        # Check if this is an actual alarm event
        if event.get('is_alarm') != '1':
            return

        # Only update if event matches this alarm type
        event_code = event.get('event_code', '')
        if not _map_event_code_to_alarm_type(event_code, self._alarm_type):
            return

        # Update state when alarm is triggered
        self._timeline_id = event.get('id')
        self._is_on = True
        LOGGER.debug(
            "Alarm %s triggered via event (event_id: %s, code: %s)",
            self._alarm_type,
            self._timeline_id,
            event_code,
        )
        self.schedule_update_ha_state()

    def _alarm_end_callback(self, event: dict[str, Any]) -> None:
        """Handle alarm end/dismiss events from timeline.

        Args:
            event: Timeline event dictionary indicating alarm dismissal
        """
        # Log for debugging
        LOGGER.debug(
            "Alarm end callback fired - alarm_type: %s, event_code: %s, is_alarm: %s, event_id: %s",
            self._alarm_type,
            event.get('event_code'),
            event.get('is_alarm'),
            event.get('id'),
        )

        # Check if this is an actual alarm event
        # Note: Some dismissal events might have is_alarm='0' or be missing, so accept all events in ALARM_END group

        # When any alarm is dismissed, turn off all alarms
        # (since triggering one alarm dismisses all in Abode)
        self._timeline_id = None
        self._is_on = False
        LOGGER.info(
            "Alarm %s ended via event (event_code: %s, all alarms dismissed)",
            self._alarm_type,
            event.get('event_code'),
        )
        self.schedule_update_ha_state()

    @handle_abode_errors("trigger manual alarm")
    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Trigger the manual alarm."""
        if self._is_on:
            LOGGER.debug("Alarm %s already triggered, ignoring duplicate trigger", self._alarm_type)
            return

        response = await self._device.trigger_manual_alarm(self._alarm_type)
        # Safely extract event_id from response, handling non-dict responses
        if isinstance(response, dict):
            self._timeline_id = response.get('event_id')
        else:
            self._timeline_id = None

        LOGGER.info(
            "Triggered manual alarm of type: %s (event_id: %s)",
            self._alarm_type,
            self._timeline_id,
        )
        self._is_on = True
        self.async_write_ha_state()

    @handle_abode_errors("dismiss timeline event")
    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Dismiss the manual alarm (if timeline event ID is available)."""
        if self._timeline_id:
            await self._data.abode.dismiss_timeline_event(self._timeline_id)
            LOGGER.info("Dismissed timeline event: %s", self._timeline_id)
            self._timeline_id = None

        self._is_on = False
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return True if the alarm is active."""
        return self._is_on


class AbodeTestModeSwitch(SwitchEntity):
    """A switch for controlling Abode test mode."""

    _attr_has_entity_name = True
    _attr_name = "Test Mode"
    _attr_icon = "mdi:test-tube"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, data: AbodeSystem, alarm: Alarm) -> None:
        """Initialize the test mode switch."""
        self._data = data
        self._alarm = alarm
        self._is_on = False
        self._user_enabled = False  # Track if user explicitly enabled test mode
        self._last_state_change: datetime | None = None  # Track when state was last changed
        # Use alarm device ID for unique ID to link to the alarm device
        self._attr_unique_id = f"{alarm.id}-test-mode"
        self._attr_available = True
        # Start with polling disabled - will be enabled after first successful fetch
        # to ensure async_added_to_hass can set initial status before polling starts
        self._attr_should_poll = False
        self._initial_sync_done = False

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information for this entity."""
        return {
            "identifiers": {(DOMAIN, self._alarm.id)},
            "manufacturer": "Abode",
            "model": self._alarm.type,
            "name": self._alarm.name,
        }

    async def async_added_to_hass(self) -> None:
        """Update test mode status on first add."""
        LOGGER.info("Test mode switch added to Home Assistant, fetching initial status")
        await super().async_added_to_hass()
        await self._refresh_test_mode_status()

    async def _refresh_test_mode_status(self) -> None:
        """Refresh test mode status from Abode."""
        try:
            self._is_on = await self._data.get_test_mode()
            LOGGER.info("Initial test mode status fetched: %s", self._is_on)
            self.async_write_ha_state()

            # Enable polling after first successful fetch
            if not self._initial_sync_done:
                LOGGER.debug("Enabling polling after initial sync")
                self._attr_should_poll = True
                self._initial_sync_done = True
        except AbodeException as ex:
            if not self._data.test_mode_supported:
                LOGGER.info("Test mode unsupported; disabling test mode switch")
                self._attr_available = False
                self._attr_should_poll = False
                self.async_write_ha_state()
                return
            LOGGER.error("Failed to get test mode status (AbodeException): %s", ex)
            import traceback
            LOGGER.debug("Traceback: %s", traceback.format_exc())
        except Exception as ex:
            LOGGER.error("Unexpected error getting test mode status: %s", ex)
            import traceback
            LOGGER.debug("Traceback: %s", traceback.format_exc())

    async def async_update(self) -> None:
        """Update test mode status."""
        # Skip polling for 5 seconds after a state change to let API catch up
        if self._last_state_change is not None:
            time_since_change = datetime.now(UTC) - self._last_state_change
            if time_since_change < timedelta(seconds=5):
                LOGGER.debug("Skipping test mode poll (waiting for API to catch up)")
                return

        try:
            previous_state = self._is_on
            self._is_on = await self._data.get_test_mode()

            LOGGER.debug("Polling test mode status: was %s, now %s", previous_state, self._is_on)

            if previous_state != self._is_on:
                LOGGER.info("Test mode status changed: %s -> %s", previous_state, self._is_on)

            # If test mode was enabled by user but is now off externally (e.g., 30-min timeout),
            # stop polling to save resources
            if self._user_enabled and previous_state and not self._is_on:
                LOGGER.info("Test mode auto-disabled (30-min timeout), stopping polling")
                self._user_enabled = False
                self._attr_should_poll = False
        except AbodeException as ex:
            if not self._data.test_mode_supported:
                LOGGER.info("Test mode unsupported; disabling test mode switch")
                self._attr_available = False
                self._attr_should_poll = False
                self.async_write_ha_state()
                return
            LOGGER.error("Failed to update test mode status: %s", ex)
        except Exception as ex:
            LOGGER.error("Unexpected error updating test mode status: %s", ex)

    @handle_abode_errors("enable test mode")
    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Enable test mode."""
        await self._data.set_test_mode(True)
        LOGGER.info("Test mode enabled")
        self._user_enabled = True  # User explicitly enabled test mode
        # Trust the state we just set (API may need time to process)
        self._is_on = True
        self._last_state_change = datetime.now(UTC)
        self.schedule_update_ha_state()

    @handle_abode_errors("disable test mode")
    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Disable test mode."""
        await self._data.set_test_mode(False)
        LOGGER.info("Test mode disabled")
        self._user_enabled = False  # User explicitly disabled test mode
        # Trust the state we just set (API may need time to process)
        self._is_on = False
        self._last_state_change = datetime.now(UTC)
        self.schedule_update_ha_state()

    @property
    def is_on(self) -> bool:
        """Return True if test mode is enabled."""
        return self._is_on
