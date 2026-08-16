"""CRUD manager for scheduled arming pairs."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import Event, EventStateChangedData, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.util import dt as dt_util

from ..const import (
    CONTEXT_ID_PREFIX,
    DOMAIN,
    EVENT_SCHEDULE_FAILED,
    EVENT_SCHEDULE_FIRED,
    EVENT_SCHEDULE_SKIPPED,
    MAX_SCHEDULE_NAME_LENGTH,
    REPAIR_ISSUE_SCHEDULE_FIRE_FAILED,
)
from .clock import Clock
from .mode_changer import ModeChanger
from .models import (
    _TIME_RE,
    WEEKDAYS,
    ChangeSource,
    ScheduledPair,
    SkipReason,
    weekday_index,
)
from .retry import RetryExhausted, async_retry_confirmed
from .scheduler import CancelHandle, ScheduleClock
from .state_machine import (
    DISARM_WINDOW_GRACE,
    PairState,
    derive_state,
    expected_disarm_at,
    parse_hhmm,
)
from .store import SchedulesStore

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class ScheduleManager:
    """CRUD over SchedulesStore with field validation."""

    def __init__(
        self,
        hass: HomeAssistant,
        store: SchedulesStore,
        clock: Clock,
        scheduler_clock: ScheduleClock,
        mode_changer: ModeChanger,
    ) -> None:
        """Initialize the manager with injected dependencies."""
        self._hass = hass
        self._store = store
        self._clock = clock
        self._scheduler_clock = scheduler_clock
        self._mode_changer = mode_changer
        # Keyed by (pair_id, "arm" | "disarm") — "arm" is the daily ScheduleClock
        # handle; "disarm" is the one-shot async_call_later handle created after
        # a successful arm (or restored by reconciliation).
        self._pending_handles: dict[tuple[str, str], CancelHandle] = {}
        self._listener_handle: CancelHandle | None = None
        self._reconcile_deferred = False

    # ------------------------------------------------------------------
    # Panel helpers — single read path; never call hass.states.get directly.
    # ------------------------------------------------------------------

    def _panel_entity_id(self) -> str | None:
        """Return the alarm panel entity_id, or None if not registered."""
        from ..helpers import find_abode_alarm_panel

        state = find_abode_alarm_panel(self._hass)
        return state.entity_id if state is not None else None

    def _panel_state(self) -> str | None:
        """Return the current alarm panel state string, or None."""
        from ..helpers import find_abode_alarm_panel

        state = find_abode_alarm_panel(self._hass)
        return state.state if state is not None else None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_setup(self) -> None:
        """Load persistent state, register timers, and reconcile open windows."""
        await self._store.async_load()
        self._register_all_timers()
        self._start_panel_listener()
        await self.async_reconcile_on_startup()

    async def async_shutdown(self) -> None:
        """Cancel all pending timers and the panel state-change listener."""
        for handle in list(self._pending_handles.values()):
            handle()
        self._pending_handles.clear()
        if self._listener_handle is not None:
            self._listener_handle()
            self._listener_handle = None

    # ------------------------------------------------------------------
    # Timer management
    # ------------------------------------------------------------------

    def _register_pair_timers(self, pair_id: str) -> None:
        """Register the daily arm callback for one enabled pair.

        No-op if the pair is missing, disabled, or already has an arm handle.
        Disarm handles are NOT registered here — they're created on-demand by a
        successful arm (or by reconciliation).
        """
        if (pair_id, "arm") in self._pending_handles:
            return
        pair = self._store.get(pair_id)
        if pair is None or not pair.enabled:
            return
        arm_t = parse_hhmm(pair.arm_time)
        weekday_set = frozenset(weekday_index(d) for d in pair.weekdays)
        pid = pair.id  # capture by value — avoid late-binding closure bugs

        async def _arm_callback() -> None:
            await self.async_arm(pid)

        handle = self._scheduler_clock.async_track_daily(
            _arm_callback,
            hour=arm_t.hour,
            minute=arm_t.minute,
            weekdays=weekday_set,
        )
        self._pending_handles[(pair_id, "arm")] = handle

    def _register_all_timers(self) -> None:
        """Register arm callbacks for all pairs.  Called once from async_setup."""
        for pair in self._store.get_all():
            self._register_pair_timers(pair.id)

    def _unregister_timers(self, pair_id: str) -> None:
        """Cancel and remove both arm and disarm handles for a pair."""
        for edge in ("arm", "disarm"):
            handle = self._pending_handles.pop((pair_id, edge), None)
            if handle is not None:
                handle()

    def _schedule_disarm(self, pair: ScheduledPair) -> None:
        """Register a one-shot disarm timer after a successful arm.

        Uses pair.last_armed_at (already set by caller) as the anchor for
        expected_disarm_at so the timer fires at the correct wall-clock time.
        """
        assert pair.last_armed_at is not None
        tz = dt_util.DEFAULT_TIME_ZONE
        now = self._clock.utcnow()
        expected = expected_disarm_at(pair, last_armed_at=pair.last_armed_at, tz=tz)
        delay = (expected - now).total_seconds()
        if delay < 0:
            # The anchor is the arm edge, but state confirmation can return up to
            # 111 s later (#192), so a window shorter than that lands here with
            # the boundary already passed.  Dropping the timer would leave the
            # panel armed with nothing to disarm it — worse than the day-long
            # window the edge anchor exists to prevent.
            #
            # `DISARM_WINDOW_GRACE` is the same tolerance `derive_state` applies,
            # so these two branches agree with it: inside the grace it still
            # reports ARMED and `async_disarm` will act, past the grace it
            # reports IDLE and `async_disarm` would no-op anyway.
            if -delay > DISARM_WINDOW_GRACE.total_seconds():
                _LOGGER.warning(
                    "Disarm delay for '%s' is %s s (past the grace window); "
                    "skipping timer",
                    pair.name or pair.id,
                    delay,
                )
                return
            _LOGGER.info(
                "Disarm boundary for '%s' already passed by %s s; disarming now",
                pair.name or pair.id,
                -delay,
            )
            delay = 0
        pid = pair.id

        @callback
        def _disarm_cb(_now: datetime, p: str = pid) -> None:
            self._hass.async_create_task(self.async_disarm(p))

        handle = async_call_later(self._hass, delay, _disarm_cb)
        self._pending_handles[(pair.id, "disarm")] = handle

    # ------------------------------------------------------------------
    # CRUD — now also wires/unwires timers
    # ------------------------------------------------------------------

    async def async_create(
        self,
        *,
        name: str = "",
        weekdays: list[str],
        arm_time: str,
        disarm_time: str,
        enabled: bool = True,
    ) -> ScheduledPair:
        """Create and persist a new schedule pair.

        Raises:
            ValueError: if validation fails or the schedule cap is reached.
        """
        pair = ScheduledPair(
            id=str(uuid.uuid4()),
            name=name,
            weekdays=weekdays,
            arm_time=arm_time,
            disarm_time=disarm_time,
            enabled=enabled,
            created_at=self._clock.utcnow(),
        )
        self._validate(pair)
        await self._store.async_add(pair)
        self._register_pair_timers(pair.id)
        return pair

    async def async_update(self, pair_id: str, **kwargs: Any) -> ScheduledPair | None:
        """Apply a partial update to a pair.

        Only the writable fields (name, weekdays, arm_time, disarm_time, enabled)
        are accepted.  Raises ``ValueError`` on validation failure; returns
        ``None`` if the pair doesn't exist.
        """
        pair = self._store.get(pair_id)
        if pair is None:
            return None

        writable = {"name", "weekdays", "arm_time", "disarm_time", "enabled"}
        unknown = set(kwargs) - writable
        if unknown:
            raise ValueError(f"non-writable field(s): {sorted(unknown)!r}")

        updated = ScheduledPair(
            id=pair.id,
            name=kwargs.get("name", pair.name),
            weekdays=kwargs.get("weekdays", pair.weekdays),
            arm_time=kwargs.get("arm_time", pair.arm_time),
            disarm_time=kwargs.get("disarm_time", pair.disarm_time),
            enabled=kwargs.get("enabled", pair.enabled),
            created_at=pair.created_at,
            last_armed_at=pair.last_armed_at,
            last_disarmed_at=pair.last_disarmed_at,
            last_skip_reason=pair.last_skip_reason,
            last_error=pair.last_error,
        )
        self._validate(updated)
        # A pending one-shot disarm timer (created on-demand by a successful arm)
        # is NOT re-registered by _register_pair_timers, so the blanket
        # _unregister_timers below would silently drop it.  Editing the name or
        # toggling `enabled` while the panel is armed would then leave the panel
        # armed with no auto-disarm.  Detect a pending disarm and re-establish it
        # after the update: recompute from the updated pair so a changed
        # disarm_time reschedules correctly, while a name-only edit is a no-op.
        had_pending_disarm = (pair_id, "disarm") in self._pending_handles
        self._unregister_timers(pair_id)
        await self._store.async_update(updated)
        self._register_pair_timers(pair_id)
        # Disabling the pair (or clearing the arm anchor) leaves it disarm-less;
        # async_disarm no-ops on a disabled pair, so don't re-arm a timer there.
        if had_pending_disarm and updated.enabled and updated.last_armed_at is not None:
            self._schedule_disarm(updated)
        return updated

    async def async_delete(self, pair_id: str) -> bool:
        """Delete a pair; return True if found, False otherwise."""
        self._unregister_timers(pair_id)
        return await self._store.async_remove(pair_id)

    async def async_get(self, pair_id: str) -> ScheduledPair | None:
        """Return a pair by id."""
        return self._store.get(pair_id)

    async def async_get_all(self) -> list[ScheduledPair]:
        """Return all pairs."""
        return self._store.get_all()

    # ------------------------------------------------------------------
    # Runtime — arm/disarm
    # ------------------------------------------------------------------

    async def async_arm(self, pair_id: str) -> None:
        """Fire the arm edge for one pair.

        Evaluates the skip rule against live panel state, retries on transient
        failure, and schedules the matching disarm on success.
        """
        pair = self._store.get(pair_id)
        if pair is None or not pair.enabled:
            return

        panel_str = self._panel_state()

        if panel_str == "armed_away":
            # Away is a higher-priority state — skip both arm and disarm.
            pair.last_skip_reason = SkipReason.AWAY_ACTIVE
            pair.last_disarmed_at = self._clock.utcnow()
            await self._store.async_update(pair)
            self._fire_event(
                EVENT_SCHEDULE_SKIPPED,
                pair,
                action="arm",
                reason=SkipReason.AWAY_ACTIVE,
            )
            _LOGGER.info("Schedule '%s' skipped (away_active)", pair.name or pair.id)
            return

        if panel_str == "armed_home":
            # Already Home — take ownership so our disarm fires later.
            pair.last_skip_reason = SkipReason.ALREADY_HOME
            pair.last_armed_at = self._clock.utcnow()
            await self._store.async_update(pair)
            self._fire_event(
                EVENT_SCHEDULE_SKIPPED,
                pair,
                action="arm",
                reason=SkipReason.ALREADY_HOME,
            )
            _LOGGER.info("Schedule '%s' skipped (already_home)", pair.name or pair.id)
            self._schedule_disarm(pair)
            return

        if panel_str != "disarmed":
            # Intermediate state or panel unavailable — conservative: skip.
            pair.last_skip_reason = SkipReason.PANEL_UNAVAILABLE
            pair.last_disarmed_at = self._clock.utcnow()
            await self._store.async_update(pair)
            self._fire_event(
                EVENT_SCHEDULE_SKIPPED,
                pair,
                action="arm",
                reason=SkipReason.PANEL_UNAVAILABLE,
            )
            _LOGGER.info(
                "Schedule '%s' skipped (panel_unavailable, state=%r)",
                pair.name or pair.id,
                panel_str,
            )
            return

        # panel_str == "disarmed" — proceed with arm.
        #
        # Anchor the arm to when the edge fired, NOT to when confirmation
        # returned.  `expected_disarm_at` rolls the disarm forward a full day
        # when the anchor is already past `disarm_time`, and state confirmation
        # can now spend up to 111 s (21 s of retries + a 90 s confirmation wait)
        # before returning.  A legal short window — say arm 22:00 / disarm 22:01
        # — would otherwise stamp 22:01:30, roll to the next day, and leave the
        # panel armed for ~24 h with nothing but an info log to show for it.
        armed_at = self._clock.utcnow()
        try:
            await async_retry_confirmed(
                lambda: self._mode_changer.async_set_mode(
                    "home", ChangeSource.SCHEDULE_ARM, pair_id=pair.id
                ),
                lambda: self._panel_state() == "armed_home",
            )
        except RetryExhausted as err:
            pair.last_error = str(err.last_error)[:200]
            await self._store.async_update(pair)
            self._fire_event(
                EVENT_SCHEDULE_FAILED,
                pair,
                action="arm",
                error=pair.last_error,
                attempts=err.attempts,
            )
            self._raise_fire_failed_issue(pair, str(err.last_error), "arm")
            _LOGGER.warning(
                "Schedule '%s' failed after %d attempts",
                pair.name or pair.id,
                err.attempts,
            )
            return

        pair.last_armed_at = armed_at
        pair.last_error = None
        pair.last_skip_reason = None
        await self._store.async_update(pair)
        self._fire_event(EVENT_SCHEDULE_FIRED, pair, action="arm", target_mode="home")
        self._clear_fire_failed_issue(pair.id)
        _LOGGER.info("Schedule '%s' fired arm", pair.name or pair.id)
        self._schedule_disarm(pair)

    async def async_disarm(
        self,
        pair_id: str,
        *,
        source: ChangeSource = ChangeSource.SCHEDULE_DISARM,
    ) -> None:
        """Fire the disarm edge for one pair.

        Guards: pair must be in ARMED state (last_armed_at > last_disarmed_at
        and still within window).  Skip if panel is no longer Home.
        """
        pair = self._store.get(pair_id)
        if pair is None or not pair.enabled:
            return

        tz = dt_util.DEFAULT_TIME_ZONE
        if derive_state(pair, now=self._clock.utcnow(), tz=tz) != PairState.ARMED:
            return

        panel_str = self._panel_state()

        if panel_str in ("armed_away", "disarmed"):
            # Panel already changed — manual override won.
            pair.last_skip_reason = SkipReason.MANUAL_OVERRIDE
            pair.last_disarmed_at = self._clock.utcnow()
            await self._store.async_update(pair)
            self._fire_event(
                EVENT_SCHEDULE_SKIPPED,
                pair,
                action="disarm",
                reason=SkipReason.MANUAL_OVERRIDE,
            )
            _LOGGER.info(
                "Schedule '%s' skipped (manual_override)", pair.name or pair.id
            )
            return

        if panel_str != "armed_home":
            # Intermediate state or unavailable — conservative: skip.
            pair.last_skip_reason = SkipReason.PANEL_UNAVAILABLE
            pair.last_disarmed_at = self._clock.utcnow()
            await self._store.async_update(pair)
            self._fire_event(
                EVENT_SCHEDULE_SKIPPED,
                pair,
                action="disarm",
                reason=SkipReason.PANEL_UNAVAILABLE,
            )
            _LOGGER.info(
                "Schedule '%s' skipped (panel_unavailable, state=%r)",
                pair.name or pair.id,
                panel_str,
            )
            return

        # panel_str == "armed_home" — proceed with disarm.
        # Anchored at the edge for the same reason as the arm above.
        disarmed_at = self._clock.utcnow()
        try:
            await async_retry_confirmed(
                lambda: self._mode_changer.async_set_mode(
                    "standby", source, pair_id=pair.id
                ),
                lambda: self._panel_state() == "disarmed",
            )
        except RetryExhausted as err:
            pair.last_error = str(err.last_error)[:200]
            await self._store.async_update(pair)
            self._fire_event(
                EVENT_SCHEDULE_FAILED,
                pair,
                action="disarm",
                error=pair.last_error,
                attempts=err.attempts,
            )
            self._raise_fire_failed_issue(pair, str(err.last_error), "disarm")
            _LOGGER.warning(
                "Schedule '%s' failed after %d attempts",
                pair.name or pair.id,
                err.attempts,
            )
            return

        pair.last_disarmed_at = disarmed_at
        pair.last_error = None
        pair.last_skip_reason = None
        await self._store.async_update(pair)
        self._fire_event(
            EVENT_SCHEDULE_FIRED, pair, action="disarm", target_mode="standby"
        )
        self._clear_fire_failed_issue(pair.id)
        _LOGGER.info("Schedule '%s' fired disarm", pair.name or pair.id)

    # ------------------------------------------------------------------
    # Events and repair issues
    # ------------------------------------------------------------------

    def _fire_event(self, name: str, pair: ScheduledPair, **extra: Any) -> None:
        """Build and fire an HA bus event for a schedule transition."""
        now_iso = self._clock.utcnow().isoformat()
        payload: dict[str, Any] = {
            "schedule_id": pair.id,
            "schedule_name": pair.name,
        }
        if name == EVENT_SCHEDULE_FIRED:
            payload["action"] = extra.get("action")
            payload["target_mode"] = extra.get("target_mode")
            payload["fired_at"] = now_iso
        elif name == EVENT_SCHEDULE_SKIPPED:
            payload["action"] = extra.get("action")
            payload["reason"] = str(extra.get("reason", ""))
            payload["skipped_at"] = now_iso
        elif name == EVENT_SCHEDULE_FAILED:
            payload["action"] = extra.get("action")
            payload["error"] = extra.get("error", "")
            payload["attempts"] = extra.get("attempts")
            payload["failed_at"] = now_iso
        self._hass.bus.async_fire(name, payload)

    def _raise_fire_failed_issue(
        self, pair: ScheduledPair, error: str, action: str
    ) -> None:
        """Raise the "schedule failed to fire" repair issue.

        ``action`` is "arm" or "disarm". The event payload has carried it from
        the start; without it in the issue too, the user is told a schedule
        failed but not which half — and the two have very different
        consequences (a failed arm leaves the house unarmed).
        """
        ir.async_create_issue(
            self._hass,
            DOMAIN,
            f"{REPAIR_ISSUE_SCHEDULE_FIRE_FAILED}_{pair.id}",
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key=REPAIR_ISSUE_SCHEDULE_FIRE_FAILED,
            translation_placeholders={
                "schedule_name": pair.name or pair.id,
                "action": action,
                "error": error[:200],
            },
        )

    def _clear_fire_failed_issue(self, pair_id: str) -> None:
        ir.async_delete_issue(
            self._hass,
            DOMAIN,
            f"{REPAIR_ISSUE_SCHEDULE_FIRE_FAILED}_{pair_id}",
        )

    # ------------------------------------------------------------------
    # Reconciliation — Sub-Phase D
    # ------------------------------------------------------------------

    async def async_reconcile_on_startup(self) -> None:
        """Re-register disarm timers for pairs that were armed before restart.

        Conservative: if the window has elapsed or the panel is no longer Home,
        mark the pair as disarmed without calling mode_changer.

        If the panel entity is not yet in hass.states (platforms not loaded yet),
        defer to EVENT_HOMEASSISTANT_STARTED so reconciliation runs after the
        alarm_control_panel entity is available.  Only defers once; a second call
        with a still-missing panel proceeds conservatively (marks PANEL_NOT_HOME).
        """
        panel_str = self._panel_state()

        if panel_str is None and not self._reconcile_deferred:
            self._reconcile_deferred = True

            @callback
            def _reconcile_after_start(_event: Event[Any]) -> None:
                self._hass.async_create_task(self.async_reconcile_on_startup())

            self._hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, _reconcile_after_start
            )
            return

        now = self._clock.utcnow()
        tz = dt_util.DEFAULT_TIME_ZONE
        reconciled = 0

        for pair in self._store.get_all():
            if not pair.enabled:
                continue
            if pair.last_armed_at is None:
                continue
            if (
                pair.last_disarmed_at is not None
                and pair.last_disarmed_at >= pair.last_armed_at
            ):
                continue

            # Pair was armed and never disarmed — determine action.
            ed = expected_disarm_at(pair, last_armed_at=pair.last_armed_at, tz=tz)

            # Intentional asymmetry with derive_state: reconcile uses a strict
            # `now >= ed` with NO grace, while derive_state allows
            # DISARM_WINDOW_GRACE for an on-time timer that fires a hair late.
            # On startup there is no in-flight timer to be late, and we must be
            # conservative — a genuinely missed window (HA was down) must be
            # marked disarmed WITHOUT auto-disarming the panel hours later. Do
            # NOT add the grace here to "match" derive_state.
            if now >= ed:
                pair.last_disarmed_at = now
                pair.last_skip_reason = SkipReason.RECONCILE_WINDOW_ELAPSED
                await self._store.async_update(pair)
                _LOGGER.info(
                    "Schedule '%s' reconciled (window elapsed)", pair.name or pair.id
                )
                continue

            if panel_str != "armed_home":
                pair.last_disarmed_at = now
                pair.last_skip_reason = SkipReason.RECONCILE_PANEL_NOT_HOME
                await self._store.async_update(pair)
                _LOGGER.info(
                    "Schedule '%s' reconciled (panel not home)", pair.name or pair.id
                )
                continue

            # In window, still Home — re-register one-shot disarm timer.
            # Bind pair.id via default arg (`p=pair.id`) to avoid late-binding
            # closure bug: without it every callback would capture the last pair.id.
            delay = (ed - now).total_seconds()
            pid = pair.id

            @callback
            def _reconcile_disarm_cb(_now: datetime, p: str = pid) -> None:
                self._hass.async_create_task(
                    self.async_disarm(p, source=ChangeSource.RECONCILE_DISARM)
                )

            handle = async_call_later(self._hass, delay, _reconcile_disarm_cb)
            self._pending_handles[(pair.id, "disarm")] = handle
            reconciled += 1

        _LOGGER.info("Reconciled %d schedules on startup", reconciled)

    # ------------------------------------------------------------------
    # Manual-override listener — Sub-Phase E
    # ------------------------------------------------------------------

    def _start_panel_listener(self) -> None:
        """Register the alarm-panel state-change listener.

        Defers registration via EVENT_HOMEASSISTANT_STARTED if the panel
        entity is not yet in hass.states (e.g. called before platforms load).
        Guards against double-registration: a second call is a no-op if the
        listener handle is already set.
        """
        if self._listener_handle is not None:
            return
        panel_id = self._panel_entity_id()
        if panel_id is None:

            @callback
            def _retry(_event: Event[Any]) -> None:
                if self._panel_entity_id() is None:
                    _LOGGER.warning(
                        "Abode panel entity not found after HA start; "
                        "schedule manual-override listener is disabled"
                    )
                    return
                self._start_panel_listener()

            self._hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _retry)
            return

        self._listener_handle = async_track_state_change_event(
            self._hass, [panel_id], self._on_panel_state_changed
        )

    @callback
    def _on_panel_state_changed(self, event: Event[EventStateChangedData]) -> None:
        """Filter state-change events; ignore self-driven schedule transitions."""
        ctx_id = event.context.id or ""
        if ctx_id.startswith(CONTEXT_ID_PREFIX):
            return  # our own change — ignore

        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state == "armed_home":
            return
        if old_state is None or old_state.state != "armed_home":
            return

        # Transition left armed_home via a non-self-driven context.
        self._hass.async_create_task(self._handle_manual_override())

    async def _handle_manual_override(self) -> None:
        """Cancel pending disarms for all ARMED pairs and mark them overridden."""
        now = self._clock.utcnow()
        tz = dt_util.DEFAULT_TIME_ZONE

        for pair in self._store.get_all():
            if not pair.enabled:
                continue
            if derive_state(pair, now=now, tz=tz) != PairState.ARMED:
                continue
            handle = self._pending_handles.pop((pair.id, "disarm"), None)
            if handle is not None:
                handle()
            pair.last_disarmed_at = now
            pair.last_skip_reason = SkipReason.MANUAL_OVERRIDE
            # Persist BEFORE firing the event (spec constraint).
            await self._store.async_update(pair)
            self._fire_event(
                EVENT_SCHEDULE_SKIPPED,
                pair,
                action="disarm",
                reason=SkipReason.MANUAL_OVERRIDE,
            )
            _LOGGER.info(
                "Schedule '%s' skipped (manual_override)", pair.name or pair.id
            )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self, pair: ScheduledPair) -> None:
        """Validate all user-settable fields.  Raises ``ValueError`` if invalid."""
        if len(pair.name) > MAX_SCHEDULE_NAME_LENGTH:
            raise ValueError(
                f"name must be at most {MAX_SCHEDULE_NAME_LENGTH} characters"
            )

        if not pair.weekdays:
            raise ValueError("weekdays must be non-empty")
        unknown_days = [d for d in pair.weekdays if d not in WEEKDAYS]
        if unknown_days:
            raise ValueError(f"unknown weekday(s): {unknown_days!r}")
        if len(pair.weekdays) != len(set(pair.weekdays)):
            raise ValueError("weekdays must not contain duplicates")

        if not _TIME_RE.match(pair.arm_time):
            raise ValueError("arm_time must match HH:MM (24-hour)")
        if not _TIME_RE.match(pair.disarm_time):
            raise ValueError("disarm_time must match HH:MM (24-hour)")
        if pair.arm_time == pair.disarm_time:
            raise ValueError("arm_time and disarm_time must differ")
