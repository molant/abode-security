"""Support for Abode Security System switches."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .abode.devices.alarm import Alarm
from .abode.devices.switch import Switch
from .abode.exceptions import Exception as AbodeException
from .abode.helpers.timeline import Groups as TimelineGroups
from .const import LOGGER
from .decorators import handle_abode_errors
from .entity import AbodeAlarmAttachedEntity, AbodeAutomation, AbodeDevice
from .models import AbodeSystem

PARALLEL_UPDATES = 1

DEVICE_TYPES = ["switch", "valve"]

# Manual alarm types
MANUAL_ALARM_TYPES = [
    "PANIC",
    "SILENT_PANIC",
    "MEDICAL",
    "CO",
    "SMOKE_CO",
    "SMOKE",
    "BURGLAR",
]

# Map alarm types to their event codes
# These codes are from .abode.helpers.events.csv
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

    # Add manual alarm switches. `get_alarm()` returns `Alarm | None`; the
    # None branch is reachable when the panel is still initializing or the
    # account has no alarm device — skip the alarm-attached switches in that
    # case rather than constructing them with None and crashing on access.
    alarm = data.abode.get_alarm()
    if alarm is not None:
        entities.extend(
            AbodeManualAlarmSwitch(data, alarm, alarm_type)
            for alarm_type in MANUAL_ALARM_TYPES
        )
        # CMS settings switches (wrapper methods handle missing methods gracefully).
        entities.extend(
            AbodeCMSSettingSwitch(data, alarm, *row) for row in _CMS_SWITCHES
        )
        entities.append(AbodeTestModeSwitch(data, alarm))
    else:
        LOGGER.warning(
            "No alarm device available; skipping alarm-attached switches",
        )

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
        # Use add_job() instead of async_create_task() for thread safety -
        # the callback may be invoked from a thread pool executor
        def _trigger_wrapper() -> None:
            """Wrapper to schedule async trigger as a task."""
            self.hass.add_job(self.trigger())

        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal, _trigger_wrapper)
        )

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


class AbodeManualAlarmSwitch(AbodeAlarmAttachedEntity, SwitchEntity):
    """A switch for triggering and dismissing manual alarms."""

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

    def __init__(self, data: AbodeSystem, alarm: Alarm, alarm_type: str) -> None:
        """Initialize the manual alarm switch."""
        super().__init__(data, alarm)
        self._alarm_type = alarm_type
        # Manual alarm state comes from timeline events, not polling.
        # Override even when integration polling is enabled.
        self._attr_should_poll = False
        self._attr_unique_id = f"{alarm.id}-manual-alarm-{alarm_type.lower()}"
        self._attr_name = self.ALARM_NAMES.get(
            alarm_type, alarm_type.replace("_", " ").title()
        )
        self._attr_icon = self.ALARM_ICONS.get(alarm_type)
        self._attr_available = True

    async def async_added_to_hass(self) -> None:
        """Subscribe to timeline events when added to Home Assistant."""
        await super().async_added_to_hass()
        await self._run_executor_with_timeout(
            self._data.abode.events.add_event_callback,
            TimelineGroups.ALARM,
            self._alarm_event_callback,
        )
        await self._run_executor_with_timeout(
            self._data.abode.events.add_event_callback,
            TimelineGroups.ALARM_END,
            self._alarm_end_callback,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up event subscriptions when removed."""
        await super().async_will_remove_from_hass()
        await self._run_executor_with_timeout(
            self._data.abode.events.remove_event_callback,
            TimelineGroups.ALARM,
            self._alarm_event_callback,
        )
        await self._run_executor_with_timeout(
            self._data.abode.events.remove_event_callback,
            TimelineGroups.ALARM_END,
            self._alarm_end_callback,
        )

    def _alarm_event_callback(self, event: dict[str, Any]) -> None:
        """Handle alarm trigger events from timeline.

        Args:
            event: Timeline event dictionary containing alarm information
        """
        # Check if this is an actual alarm event
        if event.get("is_alarm") != "1":
            return

        # Only update if event matches this alarm type
        event_code = event.get("event_code", "")
        if not _map_event_code_to_alarm_type(event_code, self._alarm_type):
            return

        # Update state when alarm is triggered
        self._timeline_id = event.get("id")
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
            event.get("event_code"),
            event.get("is_alarm"),
            event.get("id"),
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
            event.get("event_code"),
        )
        self.schedule_update_ha_state()

    @handle_abode_errors("trigger manual alarm")
    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Trigger the manual alarm."""
        if self._is_on:
            LOGGER.debug(
                "Alarm %s already triggered, ignoring duplicate trigger",
                self._alarm_type,
            )
            return

        response = await self._alarm.trigger_manual_alarm(self._alarm_type)
        # Safely extract event_id from response, handling non-dict responses
        if isinstance(response, dict):
            self._timeline_id = response.get("event_id")
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


class AbodeCMSSettingSwitch(AbodeAlarmAttachedEntity, SwitchEntity):
    """Base class for CMS configuration switches.

    Also serves as the base for the test-mode switch, which differs only in
    its support-flag attribute, its unique-id suffix, and a post-update hook
    that stops polling when test mode auto-disables on its 30-min timeout.
    """

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        data: AbodeSystem,
        alarm: Alarm,
        name: str,
        icon: str,
        getter_name: str,
        setter_name: str,
        unique_id_suffix: str | None = None,
        support_flag: str = "cms_settings_supported",
    ) -> None:
        """Initialize the CMS setting switch."""
        super().__init__(data, alarm)
        self._attr_name = name
        self._attr_icon = icon
        self._getter_name = getter_name
        self._setter_name = setter_name
        self._support_flag = support_flag
        self._is_on = False
        self._last_state_change: datetime | None = None
        self._error_count = 0
        # unique_id must stay stable across the issue #7 refactor — explicit
        # suffix overrides the default getter-derived form.
        suffix = unique_id_suffix or getter_name.lower().replace("_", "-")
        self._attr_unique_id = f"{alarm.id}-{suffix}"
        self._attr_available = True
        self._attr_should_poll = False
        self._initial_sync_done = False

    def _update_connection_status(self) -> None:
        # When this setting isn't supported by the account, _refresh_status /
        # async_update have permanently marked the entity unavailable and
        # disabled polling. Don't let a SocketIO reconnect resurrect it.
        # Uses _support_flag so AbodeTestModeSwitch (test_mode_supported) and
        # plain CMS switches (cms_settings_supported) share this code.
        if not getattr(self._data, self._support_flag):
            return
        super()._update_connection_status()

    async def async_added_to_hass(self) -> None:
        """Update setting status on first add."""
        LOGGER.info("CMS setting switch %s added to Home Assistant", self._attr_name)
        await super().async_added_to_hass()
        await self._refresh_status()

    async def _refresh_status(self) -> None:
        """Refresh setting status from Abode."""
        try:
            getter = getattr(self._data, self._getter_name)
            self._is_on = await getter()
            LOGGER.info(
                "Initial %s status fetched: %s (CMS cache=%s)",
                self._attr_name,
                self._is_on,
                getattr(self._data, "cms_settings_cache", None),
            )
            self.async_write_ha_state()

            # Enable polling after first successful fetch
            if not self._initial_sync_done:
                LOGGER.debug(
                    "Enabling polling for %s after initial sync", self._attr_name
                )
                self._attr_should_poll = True
                self._initial_sync_done = True
        except AbodeException as ex:
            if not getattr(self._data, self._support_flag):
                LOGGER.info("%s unsupported; disabling switch", self._attr_name)
                self._attr_available = False
                self._attr_should_poll = False
                self.async_write_ha_state()
                return
            LOGGER.error("Failed to get %s status: %s", self._attr_name, ex)
        except Exception as ex:
            LOGGER.error("Unexpected error getting %s status: %s", self._attr_name, ex)

    async def async_update(self) -> None:
        """Update setting status."""
        # Skip polling for 5 seconds after a state change
        if self._last_state_change is not None:
            time_since_change = datetime.now(UTC) - self._last_state_change
            if time_since_change < timedelta(seconds=5):
                LOGGER.debug("Skipping %s poll (waiting for API)", self._attr_name)
                return

        # Skip polling if not connected - prevents flapping unavailable state
        if (
            hasattr(self._data.abode, "_connection_status")
            and self._data.abode._connection_status != "connected"
        ):
            LOGGER.debug("Skipping %s poll (not connected)", self._attr_name)
            return

        try:
            previous_state = self._is_on
            getter = getattr(self._data, self._getter_name)
            self._is_on = await getter()

            LOGGER.debug(
                "%s status: was %s, now %s",
                self._attr_name,
                previous_state,
                self._is_on,
            )

            if previous_state != self._is_on:
                LOGGER.info(
                    "%s status changed: %s -> %s",
                    self._attr_name,
                    previous_state,
                    self._is_on,
                )
            self._post_update(previous_state, self._is_on)
            # Mark available on successful poll and reset error count
            self._error_count = 0
            if not self._attr_available:
                self._attr_available = True
                self.async_write_ha_state()
        except AbodeException as ex:
            if not getattr(self._data, self._support_flag):
                LOGGER.info("%s unsupported; disabling switch", self._attr_name)
                self._attr_available = False
                self._attr_should_poll = False
                self.async_write_ha_state()
                return
            # Only mark unavailable after multiple consecutive errors
            self._error_count += 1
            if self._error_count >= 3:
                LOGGER.warning(
                    "Marking %s unavailable after %d errors",
                    self._attr_name,
                    self._error_count,
                )
                self._attr_available = False
                self.async_write_ha_state()
            else:
                LOGGER.debug(
                    "Failed to update %s (attempt %d): %s",
                    self._attr_name,
                    self._error_count,
                    ex,
                )
        except Exception as ex:
            # Only mark unavailable after multiple consecutive errors
            self._error_count += 1
            if self._error_count >= 3:
                LOGGER.warning(
                    "Marking %s unavailable after %d errors",
                    self._attr_name,
                    self._error_count,
                )
                self._attr_available = False
                self.async_write_ha_state()
            else:
                LOGGER.debug(
                    "Unexpected error updating %s (attempt %d): %s",
                    self._attr_name,
                    self._error_count,
                    ex,
                )

    @handle_abode_errors("enable CMS setting")
    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Enable the CMS setting."""
        setter = getattr(self._data, self._setter_name)
        await setter(True)
        LOGGER.info("%s enabled", self._attr_name)
        self._is_on = True
        self._last_state_change = datetime.now(UTC)
        self.schedule_update_ha_state()

    @handle_abode_errors("disable CMS setting")
    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Disable the CMS setting."""
        setter = getattr(self._data, self._setter_name)
        await setter(False)
        LOGGER.info("%s disabled", self._attr_name)
        self._is_on = False
        self._last_state_change = datetime.now(UTC)
        self.schedule_update_ha_state()

    def _post_update(self, previous: bool, current: bool) -> None:
        """Hook called inside async_update on a successful poll, before the error counter resets."""

    @property
    def is_on(self) -> bool:
        """Return True if the CMS setting is enabled."""
        return self._is_on


# (display name, icon, getter, setter) for each CMS-setting switch.
_CMS_SWITCHES: tuple[tuple[str, str, str, str], ...] = (
    (
        "Monitoring Active",
        "mdi:shield-check",
        "get_monitoring_active",
        "set_monitoring_active",
    ),
    ("Send Media", "mdi:camera", "get_send_media", "set_send_media"),
    (
        "Dispatch Without Verification",
        "mdi:police-badge",
        "get_dispatch_without_verification",
        "set_dispatch_without_verification",
    ),
    ("Dispatch Fire", "mdi:fire-truck", "get_dispatch_fire", "set_dispatch_fire"),
    (
        "Dispatch Medical",
        "mdi:hospital-box",
        "get_dispatch_medical",
        "set_dispatch_medical",
    ),
    (
        "Dispatch Police",
        "mdi:police-badge",
        "get_dispatch_police",
        "set_dispatch_police",
    ),
)


class AbodeTestModeSwitch(AbodeCMSSettingSwitch):
    """A switch for controlling Abode test mode.

    Differs from a plain CMS-setting switch in two places: it consults the
    ``test_mode_supported`` flag (CMS-setting support is independent of
    test-mode support), and it stops polling after the API auto-disables
    test mode on its 30-minute server-side timeout.
    """

    def __init__(self, data: AbodeSystem, alarm: Alarm) -> None:
        """Initialize the test mode switch."""
        super().__init__(
            data,
            alarm,
            name="Test Mode",
            icon="mdi:test-tube",
            getter_name="get_test_mode",
            setter_name="set_test_mode",
            unique_id_suffix="test-mode",
            support_flag="test_mode_supported",
        )
        self._user_enabled = False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable test mode and remember the user enabled it."""
        await super().async_turn_on(**kwargs)
        # Mirror parent's success signal: _is_on flips True only if the API
        # call didn't raise (handle_abode_errors swallows AbodeError).
        if self._is_on:
            self._user_enabled = True

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable test mode and clear the user-enabled flag."""
        await super().async_turn_off(**kwargs)
        if not self._is_on:
            self._user_enabled = False

    def _post_update(self, previous: bool, current: bool) -> None:
        """Stop polling after the API auto-disables a user-enabled test mode."""
        if self._user_enabled and previous and not current:
            LOGGER.info("Test mode auto-disabled (30-min timeout), stopping polling")
            self._user_enabled = False
            self._attr_should_poll = False
