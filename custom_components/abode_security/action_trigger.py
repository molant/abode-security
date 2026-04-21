"""Action Trigger Coordinator for Abode Security.

Listens to Home Assistant state changes and triggers matching actions
when binary sensors activate.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later

from .const import DOMAIN

if TYPE_CHECKING:
    from .action_manager import AbodeAction, ActionManager

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
        for state in self._hass.states.async_all("alarm_control_panel"):
            if state.entity_id.startswith("alarm_control_panel.abode"):
                return STATE_TO_MODE.get(state.state)
        return None

    @callback
    def _handle_state_change(self, event: Event) -> None:
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

        # Schedule processing (don't block event loop)
        self._hass.async_create_task(
            self._process_sensor_activation(entity_id),
            f"action_trigger_{entity_id}",
        )

    async def _process_sensor_activation(self, entity_id: str) -> None:
        """Process a sensor activation and trigger matching actions.

        Args:
            entity_id: The binary_sensor entity that was activated
        """
        current_mode = self._get_current_mode()
        if current_mode is None:
            _LOGGER.debug(
                "No alarm panel found, skipping action trigger for %s", entity_id
            )
            return

        # Get actions for current mode (only enabled actions)
        actions = await self._action_manager.async_get_by_mode(current_mode)

        for action in actions:
            # Check if this sensor is in the action's sensor list
            if entity_id not in action.sensor_entity_ids:
                continue

            # Check debounce
            if not self._should_trigger(action.id, entity_id):
                _LOGGER.debug(
                    "Debouncing action %s for sensor %s", action.name, entity_id
                )
                continue

            # Trigger the action
            await self._trigger_action(action, entity_id, current_mode)

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
        self, action: AbodeAction, triggered_by: str, current_mode: str
    ) -> None:
        """Trigger an action, potentially with delay.

        Args:
            action: The action to trigger
            triggered_by: The sensor entity ID that triggered this
            current_mode: The current alarm mode
        """
        _LOGGER.info(
            "Action '%s' triggered by %s in mode %s",
            action.name,
            triggered_by,
            current_mode,
        )

        if action.delay_seconds > 0:
            # Schedule delayed execution using HA's async_call_later
            task_key = f"{action.id}:{triggered_by}"
            _LOGGER.debug(
                "Delaying action '%s' for %d seconds", action.name, action.delay_seconds
            )

            @callback
            def delayed_callback(_now: datetime) -> None:
                """Execute the delayed action."""
                self._pending_delays.pop(task_key, None)
                self._hass.async_create_task(
                    self._delayed_execute(action, triggered_by, current_mode),
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
            await self._execute_action(action, triggered_by, current_mode)

    async def _delayed_execute(
        self, action: AbodeAction, triggered_by: str, current_mode: str
    ) -> None:
        """Execute an action after delay timer fires.

        Args:
            action: The action to execute
            triggered_by: The sensor entity ID that triggered this
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

        await self._execute_action(action, triggered_by, current_mode)

    async def _execute_action(
        self, action: AbodeAction, triggered_by: str, current_mode: str
    ) -> None:
        """Execute an action by triggering alarms.

        Args:
            action: The action to execute
            triggered_by: The sensor entity ID that triggered this
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

        # Fire event
        event_data = {
            "action_id": action.id,
            "action_name": action.name,
            "triggered_by": triggered_by,
            "mode": current_mode,
            "alarms_triggered": alarms_triggered,
            "alarms_failed": alarms_failed,
            "timestamp": datetime.now(UTC).isoformat(),
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
