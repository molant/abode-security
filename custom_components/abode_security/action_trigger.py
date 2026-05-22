"""Action Trigger Coordinator for Abode Security.

Listens to Home Assistant state changes and triggers matching actions
when binary sensors activate.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
    callback,
)
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_call_later

from . import snapshot
from .const import DOMAIN
from .helpers import find_abode_alarm_panel

if TYPE_CHECKING:
    from .action_manager import AbodeAction, ActionManager


@dataclass(frozen=True)
class _SensorTriggerContext:
    """Immutable snapshot of sensor state captured at the moment of trigger."""

    entity_id: str
    friendly_name: str | None
    device_class: str | None
    previous_state: str | None
    new_state: str | None
    area_id: str | None
    area_name: str | None


_LOGGER = logging.getLogger(__name__)

# Mapping from alarm_control_panel states to mode IDs
STATE_TO_MODE = {
    "disarmed": "standby",
    "armed_home": "home",
    "armed_away": "away",
}


class ActionTriggerCoordinator:
    """Coordinates action triggers based on sensor state changes."""

    def __init__(
        self,
        hass: HomeAssistant,
        action_manager: ActionManager,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            action_manager: ActionManager for querying actions
        """
        self._hass = hass
        self._action_manager = action_manager
        self._unsub_state_change: Any = None
        self._pending_delays: dict[str, CALLBACK_TYPE] = {}
        self._last_trigger_times: dict[str, float] = {}

    async def async_start(self) -> None:
        """Start listening for state changes."""
        self._unsub_state_change = self._hass.bus.async_listen(
            EVENT_STATE_CHANGED, self._handle_state_change
        )
        _LOGGER.info("ActionTriggerCoordinator started")

    async def async_stop(self) -> None:
        """Stop listening and cancel pending delays."""
        if self._unsub_state_change:
            self._unsub_state_change()
            self._unsub_state_change = None

        # Cancel all pending delayed triggers
        for unsub in self._pending_delays.values():
            unsub()
        self._pending_delays.clear()
        self._last_trigger_times.clear()

        _LOGGER.info("ActionTriggerCoordinator stopped")

    def _get_current_mode(self) -> str | None:
        """Get the current alarm mode.

        Returns:
            Mode string ('standby', 'home', 'away') or None if no alarm panel found.
        """
        panel_state = find_abode_alarm_panel(self._hass)
        if panel_state is None:
            return None
        return STATE_TO_MODE.get(panel_state.state)

    @callback
    def _handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Handle state change events.

        Filters for binary_sensor entities transitioning to 'on' state.
        """
        entity_id = event.data.get("entity_id", "")

        # Only process binary_sensor entities
        if not entity_id.startswith("binary_sensor."):
            return

        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")

        # Only process genuine "off" -> "on" transitions.
        # Rejecting any other old_state (None, "unavailable", "unknown", "on") avoids
        # spurious triggers on HA restart, where a currently-open sensor transitions
        # "unavailable" -> "on" and would otherwise fire the alarm.
        if new_state is None or new_state.state != "on":
            return
        if old_state is None or old_state.state != "off":
            return

        # Capture sensor context at trigger time. Area resolution uses the
        # entity → device fallback chain so a sensor without a direct area
        # still gets area context from its device.
        area_id: str | None = None
        entity_entry = er.async_get(self._hass).async_get(entity_id)
        if entity_entry is not None:
            area_id = entity_entry.area_id
            if area_id is None and entity_entry.device_id is not None:
                device_entry = dr.async_get(self._hass).async_get(
                    entity_entry.device_id
                )
                if device_entry is not None:
                    area_id = device_entry.area_id

        area_name: str | None = None
        if area_id is not None:
            area_entry = ar.async_get(self._hass).async_get_area(area_id)
            if area_entry is not None:
                area_name = area_entry.name

        context = _SensorTriggerContext(
            entity_id=entity_id,
            friendly_name=new_state.attributes.get("friendly_name"),
            device_class=new_state.attributes.get("device_class"),
            previous_state=old_state.state,
            new_state=new_state.state,
            area_id=area_id,
            area_name=area_name,
        )

        # Schedule processing (don't block event loop)
        self._hass.async_create_task(
            self._process_sensor_activation(context),
            f"action_trigger_{entity_id}",
        )

    async def _process_sensor_activation(self, context: _SensorTriggerContext) -> None:
        """Process a sensor activation and trigger matching actions.

        Args:
            context: Snapshot of sensor state captured at the moment of trigger
        """
        current_mode = self._get_current_mode()
        if current_mode is None:
            _LOGGER.debug(
                "No alarm panel found, skipping action trigger for %s",
                context.entity_id,
            )
            return

        # Get actions for current mode (only enabled actions)
        actions = await self._action_manager.async_get_by_mode(current_mode)

        for action in actions:
            # Check if this sensor is in the action's sensor list
            if context.entity_id not in action.sensor_entity_ids:
                continue

            # Check debounce
            if not self._should_trigger(action.id, context.entity_id):
                _LOGGER.debug(
                    "Debouncing action %s for sensor %s", action.name, context.entity_id
                )
                continue

            # Trigger the action
            await self._trigger_action(action, context, current_mode)

    def _should_trigger(self, action_id: str, sensor_id: str) -> bool:
        """Check if an action should trigger based on debounce settings.

        Args:
            action_id: The action ID
            sensor_id: The sensor entity ID

        Returns:
            True if the action should trigger, False if debounced
        """
        key = f"{action_id}:{sensor_id}"
        now = datetime.now(UTC).timestamp()

        # Get debounce setting from config
        config = self._hass.data.get(DOMAIN, {}).get("config", {})
        debounce_seconds = config.get("debounce_seconds", 1.0)

        last_trigger = self._last_trigger_times.get(key, 0)
        if now - last_trigger < debounce_seconds:
            return False

        self._last_trigger_times[key] = now
        return True

    async def _trigger_action(
        self, action: AbodeAction, context: _SensorTriggerContext, current_mode: str
    ) -> None:
        """Trigger an action, potentially with delay.

        Args:
            action: The action to trigger
            context: Snapshot of sensor state captured at the moment of trigger;
                     carried into the closure so delayed callbacks use trigger-time data
            current_mode: The current alarm mode
        """
        _LOGGER.info(
            "Action '%s' triggered by %s in mode %s",
            action.name,
            context.entity_id,
            current_mode,
        )

        if action.delay_seconds > 0:
            # Schedule delayed execution using HA's async_call_later
            task_key = f"{action.id}:{context.entity_id}"
            _LOGGER.debug(
                "Delaying action '%s' for %d seconds", action.name, action.delay_seconds
            )

            @callback
            def delayed_callback(_now: datetime) -> None:
                """Execute the delayed action."""
                self._pending_delays.pop(task_key, None)
                self._hass.async_create_task(
                    self._delayed_execute(action, context, current_mode),
                    f"action_delay_exec_{task_key}",
                )

            # If a delay is already pending for this (action, sensor) pair, cancel
            # it before scheduling a new one. Otherwise the prior unsub is lost and
            # the action double-fires.
            if existing := self._pending_delays.pop(task_key, None):
                existing()
            unsub = async_call_later(self._hass, action.delay_seconds, delayed_callback)
            self._pending_delays[task_key] = unsub
        else:
            # Execute immediately
            await self._execute_action(action, context, current_mode)

    async def _delayed_execute(
        self, action: AbodeAction, context: _SensorTriggerContext, current_mode: str
    ) -> None:
        """Execute an action after delay timer fires.

        Args:
            action: The action to execute
            context: Snapshot of sensor state captured at the moment of trigger
            current_mode: The current alarm mode
        """
        # Re-check if action is still enabled
        current_action = await self._action_manager.async_get(action.id)
        if current_action is None:
            _LOGGER.debug("Action '%s' was deleted during delay", action.name)
            return
        if not current_action.enabled:
            _LOGGER.debug("Action '%s' was disabled during delay", action.name)
            return

        # Re-check alarm mode: the user may have disarmed (or otherwise
        # changed mode) during the delay window, in which case the action
        # no longer applies and firing now would surprise the user.
        current_mode_now = self._get_current_mode()
        if current_mode_now is None:
            _LOGGER.debug(
                "Alarm panel unavailable during delay; skipping action '%s'",
                action.name,
            )
            return
        if current_mode_now not in current_action.modes:
            _LOGGER.info(
                "Alarm mode changed (%s -> %s) during delay; skipping action '%s'",
                current_mode,
                current_mode_now,
                action.name,
            )
            return

        # Pass the freshly fetched current_action so any edits made during the
        # delay window (e.g. updated alarm_entity_ids) take effect — the
        # captured `action` reference may now be stale.
        await self._execute_action(current_action, context, current_mode_now)

    async def _execute_action(
        self, action: AbodeAction, context: _SensorTriggerContext, current_mode: str
    ) -> None:
        """Execute an action by triggering alarms.

        Args:
            action: The action to execute
            context: Snapshot of sensor state captured at the moment of trigger
            current_mode: The current alarm mode
        """
        alarms_triggered: list[str] = []
        alarms_failed: list[str] = []

        for alarm_entity_id in action.alarm_entity_ids:
            try:
                await self._hass.services.async_call(
                    "switch",
                    "turn_on",
                    {"entity_id": alarm_entity_id},
                    blocking=True,
                )
                alarms_triggered.append(alarm_entity_id)
            except Exception as err:
                _LOGGER.warning(
                    "Failed to trigger alarm %s for action '%s': %s",
                    alarm_entity_id,
                    action.name,
                    err,
                )
                alarms_failed.append(alarm_entity_id)

        # Record the trigger
        await self._action_manager.async_record_trigger(action.id)

        # Resolve co-located camera and optionally capture a snapshot.
        # Snapshot runs only in home/away — standby still populates camera_entity_id
        # so users can see the wiring, but snapshot_path stays None.
        camera_entity_id = snapshot.resolve_co_located_camera(
            self._hass, context.entity_id
        )
        snapshot_path: str | None = None
        snapshot_error: str | None = None
        if camera_entity_id is not None and current_mode in ("home", "away"):
            fs_path, url = snapshot.build_snapshot_path(
                action.id,
                context.entity_id,
                datetime.now(UTC),
                Path(self._hass.config.path("www")),
            )
            capture_err = await snapshot.async_capture(
                self._hass,
                camera_entity_id=camera_entity_id,
                filesystem_path=fs_path,
            )
            if capture_err is None:
                snapshot_path = url
            else:
                snapshot_error = capture_err

        # Fire event
        event_data = {
            "action_id": action.id,
            "action_name": action.name,
            "triggered_by": context.entity_id,
            "mode": current_mode,
            "alarms_triggered": alarms_triggered,
            "alarms_failed": alarms_failed,
            "timestamp": datetime.now(UTC).isoformat(),
            # Sensor context captured at trigger time — not re-fetched here so
            # delayed actions carry the state that caused the trigger, not the
            # current state which may have changed.
            "sensor_friendly_name": context.friendly_name,
            "sensor_device_class": context.device_class,
            "previous_state": context.previous_state,
            "new_state": context.new_state,
            "sensor_area_id": context.area_id,
            "sensor_area_name": context.area_name,
            "camera_entity_id": camera_entity_id,
            "snapshot_path": snapshot_path,
            "snapshot_error": snapshot_error,
        }
        self._hass.bus.async_fire("abode_security.action_triggered", event_data)

        _LOGGER.info(
            "Action '%s' executed: %d alarms triggered, %d failed",
            action.name,
            len(alarms_triggered),
            len(alarms_failed),
        )

    def cancel_pending_for_action(self, action_id: str) -> None:
        """Cancel all pending delayed triggers for an action.

        Called by ActionManager when an action is deleted or disabled.

        Args:
            action_id: The action ID to cancel pending triggers for
        """
        to_cancel = [
            key for key in self._pending_delays if key.startswith(f"{action_id}:")
        ]
        for key in to_cancel:
            unsub = self._pending_delays.pop(key, None)
            if unsub:
                unsub()
                _LOGGER.debug("Cancelled pending delay for action %s", action_id)
