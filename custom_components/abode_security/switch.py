"""Support for Abode Security System switches."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .abode.devices.alarm import Alarm
from .abode.devices.switch import Switch
from .abode.exceptions import Exception as AbodeException
from .abode.helpers.timeline import Groups as TimelineGroups
from .const import DOMAIN, LOGGER, TRIGGERABLE_ALARM_TYPES
from .decorators import handle_abode_errors
from .entity import AbodeAlarmAttachedEntity, AbodeAutomation, AbodeDevice
from .models import AbodeSystem

PARALLEL_UPDATES = 1

DEVICE_TYPES = ["switch", "valve"]

# Alarm types that get a switch entity. All seven reflect inbound alarm state
# from the timeline, but only a subset can be *triggered* — see below.
MANUAL_ALARM_TYPES = [
    "PANIC",
    "SILENT_PANIC",
    "MEDICAL",
    "CO",
    "SMOKE_CO",
    "SMOKE",
    "BURGLAR",
]

# Which of the above can actually be raised on demand lives in const.py as
# TRIGGERABLE_ALARM_TYPES — the other four fail with 400 errorCode 16013.

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


# How long entity removal waits for a cancelled event-ID lookup to unwind. The
# lookup only ever awaits network I/O and `asyncio.sleep`, so this is a backstop
# against blocking teardown, not an expected duration.
EVENT_ID_TASK_TEARDOWN_SECONDS = 5.0


@dataclass
class _EventIdLookup:
    """One run of the background timeline event-ID lookup.

    Handed to the task that performs it, so everything about that run is reached
    through a reference the task holds rather than through entity state a later
    alarm cycle can overwrite. That is what makes the abandoned-dismissal report
    exactly-once: one lookup per task, one `finally` per task, and the report
    reads the object it was given. No identity checks, no verdict that has to
    survive an await.

    `dismissal_requested` is set by `async_turn_off` when it finds no event ID to
    dismiss with; `dismissal_settled` when the dismissal was sent, or made moot by
    the alarm ending; `superseded` when another `TimelineGroups.ALARM` event
    arrived after the dismissal was asked for, which disqualifies `_timeline_id`
    as a fallback target; `withheld_target` is that disqualified ID, recorded
    where the decision is made so the warning can name it without re-reading
    entity state that may since have moved on.
    """

    task: asyncio.Task[None] | None = None
    dismissal_requested: bool = False
    dismissal_settled: bool = False
    superseded: bool = False
    withheld_target: str | None = None


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

    def _sync_attrs(self) -> None:
        """Mirror current switch state into `_attr_is_on`."""
        super()._sync_attrs()
        self._attr_is_on = cast(bool, self._device.is_on)


class AbodeAutomationSwitch(AbodeAutomation, SwitchEntity):
    """A switch implementation for Abode automations."""

    _attr_translation_key = "automation"

    async def async_added_to_hass(self) -> None:
        """Set up trigger automation service."""
        await super().async_added_to_hass()

        signal = f"abode_trigger_automation_{self.entity_id}"

        async def _trigger_and_log() -> None:
            """Run the trigger, logging any failure rather than dropping it.

            `add_job` fire-and-forgets, so a failure here has no caller to
            reach: it would escape as an unretrieved task exception, which
            reaches the user as an anonymous asyncio traceback with no mention
            of which automation failed. Naming the entity is the most this path
            can do — `abode_security.trigger_automation` fans out over the
            dispatcher, so the service call itself cannot report per-entity
            failure. See `features/pending.md`.

            The catch is deliberately broad. `handle_abode_errors` only
            converts `AbodeException`, but the embedded client re-raises bare
            `TimeoutError` / `aiohttp.ClientError` once its retries are
            exhausted (`abode/client.py`), and a network blip is the likelier
            real-world failure of the two. Anything narrower leaks exactly the
            traceback this exists to prevent. `exception()` keeps the stack for
            the cases the decorator never annotated.
            """
            try:
                await self.trigger()
            except Exception:  # noqa: BLE001 - no caller to re-raise to
                LOGGER.exception("Automation %s failed to trigger", self.entity_id)

        # Create a synchronous wrapper for the async trigger callback
        # Use add_job() instead of async_create_task() for thread safety -
        # the callback may be invoked from a thread pool executor
        def _trigger_wrapper() -> None:
            """Wrapper to schedule async trigger as a task."""
            self.hass.add_job(_trigger_and_log())

        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal, _trigger_wrapper)
        )

    def __init__(self, data: AbodeSystem, automation: Any) -> None:
        """Initialize an automation switch with its current enabled state."""
        super().__init__(data, automation)
        self._attr_is_on = bool(automation.enabled)

    @handle_abode_errors("enable automation")
    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Enable the automation."""
        await self._automation.enable(True)
        LOGGER.info("Automation enabled")
        self._attr_is_on = True
        self.async_write_ha_state()

    @handle_abode_errors("disable automation")
    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Disable the automation."""
        await self._automation.enable(False)
        LOGGER.info("Automation disabled")
        self._attr_is_on = False
        self.async_write_ha_state()

    @handle_abode_errors("trigger automation")
    async def trigger(self) -> None:
        """Trigger the automation."""
        await self._automation.trigger()
        LOGGER.info("Automation triggered")

    async def async_update(self) -> None:
        """Refresh the automation and mirror its `enabled` flag into `_attr_is_on`."""
        await super().async_update()
        self._attr_is_on = bool(self._automation.enabled)


class AbodeManualAlarmSwitch(AbodeAlarmAttachedEntity, SwitchEntity):
    """A switch for triggering and dismissing manual alarms."""

    _alarm_type: str
    _timeline_id: str | None = None
    # Non-None only while a lookup may still be running: set when the task is
    # created, cleared by the task's own unwind or by whoever cancels it.
    _lookup: _EventIdLookup | None = None

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
        self._attr_is_on = False
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
        # Cancel first so the lookup stops early, but wait for it *after* the
        # callbacks are gone: `_alarm_event_callback` / `_alarm_end_callback`
        # both call `schedule_update_ha_state()`, and waiting here first would
        # leave them registered against a half-torn-down entity for as long as
        # the task takes to unwind.
        lookup = self._lookup
        self._cancel_event_id_lookup()
        task = lookup.task if lookup is not None else None

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

        if task is not None:
            # `asyncio.wait` rather than `await task` under
            # `suppress(CancelledError)`: that cannot tell the task's own
            # cancellation from a cancellation of *this* coroutine, and would
            # swallow the latter.
            _, pending = await asyncio.wait(
                {task}, timeout=EVENT_ID_TASK_TEARDOWN_SECONDS
            )
            if pending:
                # Not expected to fire — the task only ever awaits network I/O
                # and `asyncio.sleep`. If it does, the task outlives the entity
                # and its next state write raises against a removed one, so say
                # which entity so the two can be connected.
                LOGGER.warning(
                    "Event id lookup for the %s alarm did not unwind within "
                    "%.0fs of being cancelled",
                    self._alarm_type,
                    EVENT_ID_TASK_TEARDOWN_SECONDS,
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

        # An ALARM event arriving after a dismissal was asked for disqualifies
        # this ID as that dismissal's fallback *target*. It may be a genuinely new
        # alarm or just our own alarm's late event — the payload cannot tell, and
        # since deferral only happens when no ID had arrived yet, the late-event
        # case is the likelier one. `dismiss_timeline_event` ignores one specific
        # event, so guessing wrong the other way would silently swallow an alarm
        # nobody has seen. The dismissal still goes out if the lookup finds its
        # own event id.
        lookup = self._lookup
        if lookup is not None and lookup.dismissal_requested:
            lookup.superseded = True

        # Update state when alarm is triggered
        self._timeline_id = event.get("id")
        self._attr_is_on = True
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
        # The alarm is over, so an in-flight event-ID lookup has nothing left to
        # do — and a dismissal riding on it is now satisfied rather than
        # abandoned: the alarm ending is what it was waiting for. Safe to cancel
        # from here: timeline callbacks run on the event loop
        # (`event_controller._execute_callback`).
        self._cancel_event_id_lookup(settled=True)
        self._attr_is_on = False
        LOGGER.info(
            "Alarm %s ended via event (event_code: %s, all alarms dismissed)",
            self._alarm_type,
            event.get("event_code"),
        )
        self.schedule_update_ha_state()

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Trigger the manual alarm.

        Errors are deliberately *not* swallowed: the caller (the actions
        executor, or a user's automation) has to be able to tell a raised
        alarm from a no-op, otherwise a security action that failed looks
        exactly like one that worked.
        """
        if self._alarm_type not in TRIGGERABLE_ALARM_TYPES:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="alarm_type_not_triggerable",
                translation_placeholders={
                    "alarm_type": self._alarm_type,
                    "supported": ", ".join(sorted(TRIGGERABLE_ALARM_TYPES)),
                },
            )

        # Cleared *before* the POST, not after: the SocketIO ALARM event for
        # this alarm can land while the request is still in flight, and
        # `_alarm_event_callback`'s ID is the authoritative one. Anything still
        # set at this point belongs to a previous alarm.
        previous_timeline_id = self._timeline_id
        was_resolving = self._lookup is not None
        self._cancel_event_id_lookup()
        self._timeline_id = None

        try:
            await self._alarm.trigger_manual_alarm(self._alarm_type)
        except BaseException:
            # No new alarm was raised, so nothing superseded the one this switch
            # was already tracking. Leaving the ID cleared would strand a live
            # alarm with no way to dismiss it — its SocketIO ALARM event fired
            # long ago and will not repeat. BaseException, not Exception: a POST
            # cancelled at shutdown strands the ID exactly the same way.
            if self._timeline_id is None and self._attr_is_on:
                self._timeline_id = previous_timeline_id
            if self._timeline_id is None and was_resolving and self._attr_is_on:
                # The cancelled lookup cannot be restored the way the ID can, so
                # the previous alarm is now live with neither an ID nor anything
                # still trying to find one. A 429 on a re-trigger inside the
                # 30-67s resolution window is enough to get here, and without
                # this the loss is invisible until someone tries to dismiss.
                LOGGER.warning(
                    "Re-triggering the %s alarm failed after its previous event "
                    "id lookup was cancelled — the earlier alarm may still be "
                    "live in Abode with no id to dismiss it",
                    self._alarm_type,
                )
            raise

        LOGGER.info("Triggered manual alarm of type: %s", self._alarm_type)
        self._attr_is_on = True
        self.async_write_ha_state()

        # Resolving the timeline event ID polls Abode for up to ~67s (the API
        # does not expose a triggered alarm on the timeline for 30-60s). It is
        # only needed for a later dismissal, so it runs off the critical path —
        # the alarm is already raised, and the `action_triggered` event that
        # drives the user's notification fires as soon as this returns. See
        # issue #194.
        #
        # An action wired to several alarm switches now polls once per switch on
        # the same retry schedule, so those requests arrive together rather than
        # spread out by the old inline serialization. The timeline endpoint has
        # not shown the 429s the panel/CMS endpoints do; if it starts to, jitter
        # belongs in `Alarm.timeline_event_retry_delays`, not here.
        # Assigned before the task is created, not after: under eager start the
        # coroutine can reach its `finally` first, and that clears `self._lookup`
        # only when it still points at this lookup. Unwound on failure so a lookup
        # that never ran cannot linger and make `was_resolving` lie.
        lookup = _EventIdLookup()
        self._lookup = lookup
        try:
            lookup.task = self.hass.async_create_background_task(
                self._async_resolve_timeline_id(lookup),
                name=f"abode_security resolve alarm event id {self._alarm_type}",
            )
        except BaseException:
            if self._lookup is lookup:
                self._lookup = None
            raise

    async def _async_resolve_timeline_id(self, lookup: _EventIdLookup) -> None:
        """Resolve the timeline event ID, then store it or spend it dismissing."""
        try:
            event_id = await self._alarm.find_alarm_event_id()

            if lookup.dismissal_requested:
                # `async_turn_off` ran while this lookup was still in flight and
                # handed the dismissal here rather than dropping it.
                await self._async_send_dismissal(lookup, event_id)
                return

            if not event_id:
                return

            # Two ways this result can already be stale by the time it lands:
            # `_alarm_event_callback` supplied the real ID over SocketIO (better
            # source, keep it), or the alarm was dismissed/ended in the meantime
            # (storing the ID would make the next `turn_off` dismiss an event
            # that is already gone).
            if not self._attr_is_on or self._timeline_id is not None:
                LOGGER.debug(
                    "Discarding polled event id %s for %s (is_on=%s, known id=%s)",
                    event_id,
                    self._alarm_type,
                    self._attr_is_on,
                    self._timeline_id,
                )
                return

            self._timeline_id = event_id
            LOGGER.info(
                "Resolved timeline event id for %s alarm: %s",
                self._alarm_type,
                event_id,
            )
        finally:
            # Every exit — resolved, gave up, dismissal sent, dismissal failed,
            # cancelled by `_cancel_event_id_lookup`, or cancelled out of band by
            # HA at shutdown — passes through here exactly once per task, and
            # reports the lookup it was *handed* rather than whatever the entity
            # currently points at. That is what makes "an abandoned dismissal is
            # reported exactly once" hold by construction: a later cycle can
            # replace `self._lookup`, but it cannot reach this one's obligation.
            if self._lookup is lookup:
                self._lookup = None
            if lookup.dismissal_requested and not lookup.dismissal_settled:
                # Names the withheld id and why: on the `superseded` path this
                # warning is the only output, and the remedy is a manual dismissal.
                LOGGER.warning(
                    "The pending dismissal of the %s alarm was not sent — the "
                    "alarm may still be live in Abode (superseded=%s, "
                    "withheld id=%s)",
                    self._alarm_type,
                    lookup.superseded,
                    lookup.withheld_target,
                )

    async def _async_send_dismissal(
        self, lookup: _EventIdLookup, event_id: str | None
    ) -> None:
        """Send a dismissal `async_turn_off` could not send itself.

        Runs inside the background lookup task, so it has no caller to raise to
        and must consume its own errors — an escaping exception would surface
        only as an unretrieved-task traceback. Anything short of success leaves
        `lookup.dismissal_settled` false, and the caller's `finally` says so.
        """
        # The polled ID wins. Note what the poll does and does not guarantee:
        # `_find_timeline_alarm_event` takes the newest `is_alarm` event aged
        # `[0, 90]`s relative to its own start, so it cannot return an alarm
        # raised *after* this lookup began, but a flat 90s backward bound means it
        # can return an earlier one (see `features/pending.md`). `_timeline_id` is
        # the fallback for a poll that came back empty on a transient error — and
        # only while nothing newer has arrived, because `dismiss_timeline_event`
        # ignores one specific event, and spending this dismissal on an alarm
        # raised after the user asked for it would silently swallow one they have
        # not seen.
        target = event_id
        if target is None:
            if lookup.superseded:
                lookup.withheld_target = self._timeline_id
            else:
                target = self._timeline_id
        if not target:
            return

        try:
            await self._data.abode.dismiss_timeline_event(target)
        except Exception:
            LOGGER.exception(
                "Deferred dismissal of the %s alarm (timeline event %s) failed",
                self._alarm_type,
                target,
            )
            return

        lookup.dismissal_settled = True
        LOGGER.info("Dismissed timeline event: %s (deferred)", target)
        # Reconcile: `_alarm_event_callback` may have flipped the switch back on
        # and stored this ID during the deferral window. Waiting for ALARM_END to
        # tidy up would leave the switch reporting a live alarm, holding an ID
        # that now points at a dismissed event. Guarded, because that same
        # callback may instead hold a *newer* alarm's ID, and its ALARM event
        # will not repeat — clearing it would make that alarm undismissable.
        if self._timeline_id in (None, target):
            self._timeline_id = None
            self._attr_is_on = False
            self.async_write_ha_state()
        else:
            # Mirrors the inline path's warning. "Your dismissal landed on an
            # older event and a newer alarm is live" is the more confusing of the
            # two outcomes, so it should not be the quieter one.
            LOGGER.warning(
                "Dismissed the %s alarm's earlier timeline event %s, but a newer "
                "alarm (event %s) is live — leaving the switch on so it can still "
                "be dismissed",
                self._alarm_type,
                target,
                self._timeline_id,
            )

    def _cancel_event_id_lookup(self, *, settled: bool = False) -> None:
        """Stop the in-flight event-ID lookup.

        `settled` when whatever a pending dismissal was waiting for has already
        happened. Settling the obligation is the *only* thing that keeps the
        abandoned-dismissal warning off the benign paths; every other caller
        leaves it outstanding and the owning task reports it as it unwinds.

        Two callers pass it, and they know it to different degrees. `ALARM_END`
        knows it: Abode said the alarm is over. The inline branch of
        `async_turn_off` is making a judgement — it just dismissed the ID now on
        the entity, and treats that as discharging an earlier request for which no
        ID had arrived. In that situation the lookup is necessarily `superseded`
        (only `_alarm_event_callback` can put an ID there while a dismissal is
        outstanding, and it sets that flag), so this settles on exactly the
        ambiguity `_async_send_dismissal` refuses to resolve. The asymmetry is
        deliberate: deferral only happens when no ID had arrived, which makes the
        late-own-event reading the likely one, and warning here would fire on that
        common path — the false alarm that makes the real warnings worthless. The
        cost is that the rarer reading (a genuinely different alarm) settles an
        obligation that was not actually met, silently. `dismiss_timeline_event`
        ignoring one specific event is what makes both readings survivable: the
        other alarm keeps its own ID and stays dismissable.
        """
        lookup = self._lookup
        if lookup is None:
            return

        if settled:
            lookup.dismissal_settled = True
        self._lookup = None

        task = lookup.task
        if task is not None and not task.done():
            task.cancel()

    @handle_abode_errors("dismiss timeline event")
    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Dismiss the manual alarm (if timeline event ID is available)."""
        lookup = self._lookup
        superseded_by: str | None = None
        if self._timeline_id:
            # Captured before the await, and logged from the capture: reading the
            # attribute back afterwards can name an event that was never
            # dismissed, on a path where the log is the audit trail.
            target = self._timeline_id
            await self._data.abode.dismiss_timeline_event(target)
            LOGGER.info("Dismissed timeline event: %s", target)
            # Settles any dismissal riding on the lookup: what it was waiting to
            # do has just been done. Reached only *after* the await — a failed
            # inline dismissal raises through `handle_abode_errors` and leaves the
            # obligation outstanding as a fallback.
            self._cancel_event_id_lookup(settled=True)
            # Same reconciliation rule as the deferred path: only clear what was
            # actually dismissed. `_alarm_event_callback` can fire during the
            # await with a *newer* alarm's id, and that alarm's ALARM event will
            # not repeat — clearing it would make it undismissable, and reporting
            # the switch off would hide it.
            if self._timeline_id in (None, target):
                self._timeline_id = None
            else:
                superseded_by = self._timeline_id
        elif lookup is not None and lookup.dismissal_requested:
            LOGGER.info(
                "A dismissal of the %s alarm is already pending on its event id lookup",
                self._alarm_type,
            )
        elif lookup is not None and lookup.task is not None:
            # The ID is still being resolved. Waiting for it here is the wrong
            # trade twice over: Abode typically needs 30-60s to expose the event
            # at all, and `PARALLEL_UPDATES = 1` means a blocked `turn_off`
            # serializes every other Abode switch call behind it — including the
            # `switch.turn_on` that raises the *next* alarm, which is exactly the
            # latency #194 set out to remove. So the dismissal is handed to the
            # lookup instead, and sent the moment the ID lands.
            lookup.dismissal_requested = True
            LOGGER.info(
                "No timeline event id for the %s alarm yet; the dismissal will "
                "be sent to Abode as soon as the lookup resolves",
                self._alarm_type,
            )
        elif self._attr_is_on:
            # Not silent: the switch is about to report off while the alarm may
            # still be live in Abode, and that is a security path. Reachable when
            # neither the SocketIO ALARM event nor the timeline poll ever
            # produced an ID.
            LOGGER.warning(
                "No timeline event id for the %s alarm — nothing was dismissed "
                "in Abode; the switch is reporting off regardless",
                self._alarm_type,
            )

        if superseded_by is None:
            self._attr_is_on = False
        else:
            LOGGER.warning(
                "A new %s alarm (timeline event %s) was raised while the previous "
                "one was being dismissed — leaving the switch on so it can still "
                "be dismissed",
                self._alarm_type,
                superseded_by,
            )
        self.async_write_ha_state()


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
        self._attr_is_on = False
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
            self._attr_is_on = await getter()
            LOGGER.info(
                "Initial %s status fetched: %s (CMS cache=%s)",
                self._attr_name,
                self._attr_is_on,
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
            previous_state = self._attr_is_on
            getter = getattr(self._data, self._getter_name)
            self._attr_is_on = await getter()

            LOGGER.debug(
                "%s status: was %s, now %s",
                self._attr_name,
                previous_state,
                self._attr_is_on,
            )

            if previous_state != self._attr_is_on:
                LOGGER.info(
                    "%s status changed: %s -> %s",
                    self._attr_name,
                    previous_state,
                    self._attr_is_on,
                )
            self._post_update(previous_state, self._attr_is_on)
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
        self._attr_is_on = True
        self._last_state_change = datetime.now(UTC)
        self.schedule_update_ha_state()

    @handle_abode_errors("disable CMS setting")
    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Disable the CMS setting."""
        setter = getattr(self._data, self._setter_name)
        await setter(False)
        LOGGER.info("%s disabled", self._attr_name)
        self._attr_is_on = False
        self._last_state_change = datetime.now(UTC)
        self.schedule_update_ha_state()

    def _post_update(self, previous: bool | None, current: bool | None) -> None:
        """Hook called inside async_update on a successful poll, before the error counter resets."""


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
        # Mirror parent's success signal: _attr_is_on flips True only if the
        # API call didn't raise. (handle_abode_errors re-raises as
        # HomeAssistantError, so a failure never reaches this line at all.)
        if self._attr_is_on:
            self._user_enabled = True

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable test mode and clear the user-enabled flag."""
        await super().async_turn_off(**kwargs)
        if not self._attr_is_on:
            self._user_enabled = False

    def _post_update(self, previous: bool | None, current: bool | None) -> None:
        """Stop polling after the API auto-disables a user-enabled test mode."""
        if self._user_enabled and previous and not current:
            LOGGER.info("Test mode auto-disabled (30-min timeout), stopping polling")
            self._user_enabled = False
            self._attr_should_poll = False
