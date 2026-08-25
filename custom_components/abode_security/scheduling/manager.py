"""CRUD manager for scheduled arming pairs."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import TYPE_CHECKING, Any

from homeassistant.const import (
    EVENT_HOMEASSISTANT_STARTED,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    Platform,
)
from homeassistant.core import CoreState, Event, EventStateChangedData, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_added_domain,
    async_track_state_change_event,
)
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

# How long a past-startup deferral waits for the panel entity before deciding it
# is not coming.  Floored at HA's own `SLOW_SETUP_MAX_WAIT`: platforms normally
# forward milliseconds after `async_setup`, but HA *permits* them up to 300 s,
# and undershooting that turns a slow forward into a race we lose badly —
# reconcile would stamp `last_disarmed_at` against a panel that was merely late,
# dropping the pair out of ARMED with no way to re-run it.  Waiting the full
# ceiling costs nothing in the case this exists for (no alarm device on the
# account), where nothing is watching anyway.
PANEL_WAIT_TIMEOUT = 300

# Keys for `_panel_wait_handles`; the two deferrals wait independently.
PANEL_WAIT_LISTENER = "listener"
PANEL_WAIT_RECONCILE = "reconcile"


class _RunWithoutPanel:
    """Sentinel for "no panel? do it anyway" in ``_defer_until_panel_exists``.

    The alternative is a warning message, and the two are mutually exclusive —
    one parameter carrying either makes "both" and "neither" unrepresentable
    rather than merely untested.
    """


RUN_WITHOUT_PANEL = _RunWithoutPanel()


class _Unset:
    """Sentinel for "leave this runtime field alone" in ``_persist_runtime``.

    A plain ``None`` default would not do: the success paths need to *clear*
    ``last_error`` and ``last_skip_reason``, so "set to None" and "don't touch"
    have to be distinguishable.
    """


_UNSET = _Unset()


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
        # Outstanding "wait for the panel entity to appear" subscriptions, used
        # instead of EVENT_HOMEASSISTANT_STARTED once HA is already running.
        # Keyed so the listener and the startup reconcile wait independently.
        self._panel_wait_handles: dict[str, CancelHandle] = {}
        # Last mode the panel was actually *in*, ignoring unavailable/unknown.
        # _on_panel_state_changed compares against this rather than the event's
        # own old_state, so a cloud dropout does not erase the fact that the
        # panel was Home before it (#216).
        self._last_panel_state: str | None = None
        self._reconcile_deferred = False
        # In-flight async_arm / async_disarm work, so async_shutdown can cancel
        # it.  State confirmation (#192) can keep one of these alive for ~111 s,
        # which a config-entry unload overlaps as the normal case; without this
        # a late store write, event, or repair issue lands against a manager
        # that is no longer wired up (#201).
        self._inflight: set[asyncio.Task[None]] = set()
        self._shutdown = False

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
        """Cancel pending timers, the panel listener, and in-flight work.

        There is one production call site, in ``_async_teardown_runtime``,
        reached from both ``async_unload_entry`` and ``async_remove_entry``;
        HA's own stop path does not reach it (``ConfigEntries.async_shutdown``
        does not unload entries — it cancels the tasks it tracks, which
        propagates through :meth:`_run_tracked` instead).  Those two entry
        points cannot double-call it: the helper looks the manager up in
        ``hass.data`` and pops it, so a remove after a clean unload finds
        nothing.  The second caller that makes idempotency worth guaranteeing
        is test teardown, which shuts down a manager some tests have already
        shut down.

        Safe to call twice in sequence, but not concurrently: the second caller
        would find ``_inflight`` already drained and return while the first is
        still awaiting the gather.

        The whole sweep runs without an ``await`` up to the ``gather``, so
        nothing can re-register a timer between clearing the handles and
        cancelling the coroutines that create them.  Past that point the
        ``_shutdown`` flag takes over: the gather yields to the loop, and the
        timer-registering helpers check the flag so a WS command arriving in
        that window cannot install a handle nobody will sweep again.

        What the sweep can reach depends on how the two panel deferrals were
        armed.  During startup they are ``EVENT_HOMEASSISTANT_STARTED``
        one-shots, which are *not* unsubscribed here — they hold a reference to
        this manager until HA start fires — and the ``_shutdown`` flag is what
        makes them no-ops.  Past startup they are live state-added
        subscriptions parked in ``_panel_wait_handles``, and those are
        genuinely cancelled below; left alone they would keep a torn-down
        manager subscribed to every alarm_control_panel that appears next.
        """
        self._shutdown = True
        for handle in list(self._pending_handles.values()):
            handle()
        self._pending_handles.clear()
        if self._listener_handle is not None:
            self._listener_handle()
            self._listener_handle = None
        for key in list(self._panel_wait_handles):
            self._cancel_panel_wait(key)
        # Cleared with the handle it belongs to: the two are a pair, and a
        # remembered mode outliving the listener that maintained it would be
        # stale the moment anything learns to restart a shut-down manager.
        self._last_panel_state = None
        tasks = list(self._inflight)
        self._inflight.clear()
        for task in tasks:
            task.cancel()
        # Await them: a cancelled task is not yet a finished one, and returning
        # before it unwinds is the gap this closes.  `return_exceptions=True`
        # because every one of these resolves as a CancelledError, which would
        # otherwise cancel the caller unloading the entry.
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Retrieving the results also swallows any genuine failure, which used
        # to reach asyncio's "Task exception was never retrieved" handler.  A
        # reload is exactly when someone is reading the log, so keep it visible.
        for result in results:
            if isinstance(result, BaseException) and not isinstance(
                result, asyncio.CancelledError
            ):
                _LOGGER.error(
                    "Schedule task failed during shutdown: %s", result, exc_info=result
                )

    def _track(self, coro: Coroutine[Any, Any, None]) -> asyncio.Task[None] | None:
        """Start ``coro`` as a task ``async_shutdown`` can cancel.

        Returns ``None`` — having closed the coroutine — once shut down: a timer
        creates its task inside its callback, before the handle is cancelled, so
        work can still arrive after the sweep.

        Every coroutine the manager spawns on its own goes through here or
        :meth:`_run_tracked` — the two disarm timers, the deferred startup
        reconcile and the manual-override handler — so that no store write,
        event, or repair issue can outlive the manager (#201).  The CRUD methods
        are deliberately not tracked: they are driven by a WS caller that is
        already awaiting them, and it is only their *timer* side effects that
        must not outlive the sweep, which the ``_shutdown`` flag handles.
        """
        if self._shutdown:
            # Name the coroutine: four different coroutines reach this, and
            # "work was dropped" without saying which is not much help to
            # someone debugging a schedule that skipped a reload.
            _LOGGER.debug(
                "Dropped %s; schedule manager is shut down", coro.__qualname__
            )
            coro.close()
            return None
        # Annotated because HA's PEP-695 `async_create_task[_R]` currently infers
        # as Any here, which mypy rejects at the return.
        task: asyncio.Task[None] = self._hass.async_create_task(coro)
        self._inflight.add(task)
        task.add_done_callback(self._inflight.discard)
        return task

    async def _run_tracked(self, coro: Coroutine[Any, Any, None]) -> None:
        """Await :meth:`_track` — the entry point for callers that await.

        Wrapping ``async_arm`` / ``async_disarm`` rather than only the callbacks
        that spawn them means a caller that simply awaits them (tests today, any
        future direct caller) is visible to the sweep too.  The extra task is
        the price: a coroutine cannot cancel the task that awaits it.

        Cancellation still propagates downwards — cancelling the caller cancels
        the inner task it is waiting on — so HA shutdown behaves as before.
        """
        task = self._track(coro)
        if task is not None:
            await task

    # ------------------------------------------------------------------
    # Runtime-field persistence
    # ------------------------------------------------------------------

    async def _persist_runtime(
        self,
        pair_id: str,
        *,
        last_armed_at: datetime | None | _Unset = _UNSET,
        last_disarmed_at: datetime | None | _Unset = _UNSET,
        last_skip_reason: str | None | _Unset = _UNSET,
        last_error: str | None | _Unset = _UNSET,
    ) -> ScheduledPair | None:
        """Merge runtime-owned fields onto the freshest stored pair and persist.

        Every runtime write goes through here, and none of them may write back a
        ``ScheduledPair`` captured before an ``await`` (#202).  ``ScheduledPair``
        is mutable and :meth:`SchedulesStore.async_update` re-inserts the whole
        record by id, so the last writer used to win every field rather than
        only the ones it owns — and :meth:`async_update` builds a *new* instance,
        so a WS edit arriving during the ~111 s confirmation window (#192) was
        silently undone when the arm finished.  The four fields below are
        disjoint from the user-editable ones (``name``, ``weekdays``,
        ``arm_time``, ``disarm_time``, ``enabled``), which is what makes the
        field-level merge unambiguous.

        Returns whatever record is stored once the write settles — callers must
        use *that* for events and for :meth:`_schedule_disarm`, so both see the
        edited window and name — or ``None`` if the pair was deleted meanwhile,
        which is the other half of the same bug: writing the captured copy back
        re-created the record.

        Returning the object we just wrote would leave a narrower version of the
        very race this closes.  ``SchedulesStore.async_update`` is an immediate,
        non-debounced ``Store.async_save``, so it suspends on real disk I/O, and
        a WS edit landing in that window installs a *new* instance — one that
        keeps our runtime fields (its own read happens after the synchronous
        cache write below) but carries the user's edits.  That is the record to
        hand back; the one we wrote is already superseded.
        """
        pair = self._store.get(pair_id)
        if pair is None:
            return None
        if not isinstance(last_armed_at, _Unset):
            pair.last_armed_at = last_armed_at
        if not isinstance(last_disarmed_at, _Unset):
            pair.last_disarmed_at = last_disarmed_at
        if not isinstance(last_skip_reason, _Unset):
            pair.last_skip_reason = last_skip_reason
        if not isinstance(last_error, _Unset):
            pair.last_error = last_error
        await self._store.async_update(pair)
        return self._store.get(pair_id)

    # ------------------------------------------------------------------
    # Timer management
    # ------------------------------------------------------------------

    def _set_disarm_handle(self, pair_id: str, handle: CancelHandle) -> None:
        """Store a one-shot disarm handle, cancelling whatever it replaces.

        Assigning into ``_pending_handles`` blind leaks the handle it overwrites:
        the orphaned timer still fires, and only ``_disarm_impl``'s
        ``derive_state`` guard keeps that harmless — an accident, not a design.
        """
        existing = self._pending_handles.pop((pair_id, "disarm"), None)
        if existing is not None:
            existing()
        self._pending_handles[(pair_id, "disarm")] = handle

    def _register_pair_timers(self, pair_id: str) -> None:
        """Register the daily arm callback for one enabled pair.

        No-op if the pair is missing, disabled, or already has an arm handle.
        Disarm handles are NOT registered here — they're created on-demand by a
        successful arm (or by reconciliation).

        Also a no-op once shut down: this is reachable from the WS create/update
        commands, which are not tracked work, so without the guard one landing
        while ``async_shutdown`` awaits its gather would register a live daily
        timer into a ``_pending_handles`` nobody will sweep again.
        """
        if self._shutdown or (pair_id, "arm") in self._pending_handles:
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

        No-op once shut down.  Not dead code, but the reachable window is
        narrow and worth spelling out: a plain post-shutdown `async_update`
        cannot get here, because the sweep emptied `_pending_handles` so its
        `had_pending_disarm` is False.  What reaches it is a WS update that read
        `had_pending_disarm = True` and is suspended on its own store write when
        the sweep runs — it resumes afterwards and would re-register a one-shot
        disarm nobody will cancel.
        """
        if self._shutdown:
            return
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
            self._track(self._disarm_impl(p, source=ChangeSource.SCHEDULE_DISARM))

        handle = async_call_later(self._hass, delay, _disarm_cb)
        self._set_disarm_handle(pair.id, handle)

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
        """Delete a pair; return True if found, False otherwise.

        Clears the pair's "failed to fire" repair issue too.  Only the arm and
        disarm success paths used to clear it, and both now bail early on a pair
        deleted mid-flight (see :meth:`_persist_runtime`) — which would strand an
        ``is_fixable=False`` issue the user cannot dismiss, naming a schedule
        that no longer exists.  Deleting a schedule that simply failed yesterday
        stranded it the same way, so this closes both.
        """
        self._unregister_timers(pair_id)
        removed = await self._store.async_remove(pair_id)
        if removed:
            self._clear_fire_failed_issue(pair_id)
        return removed

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
        failure, and schedules the matching disarm on success.  Runs as a
        tracked task so teardown can cancel it — see :meth:`_run_tracked`.
        """
        await self._run_tracked(self._arm_impl(pair_id))

    async def _arm_impl(self, pair_id: str) -> None:
        """Body of :meth:`async_arm`; call that instead."""
        pair = self._store.get(pair_id)
        if pair is None or not pair.enabled:
            return

        panel_str = self._panel_state()

        if panel_str == "armed_away":
            # Away is a higher-priority state — skip both arm and disarm.
            persisted = await self._persist_runtime(
                pair_id,
                last_skip_reason=SkipReason.AWAY_ACTIVE,
                last_disarmed_at=self._clock.utcnow(),
            )
            if persisted is None:
                return
            pair = persisted
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
            persisted = await self._persist_runtime(
                pair_id,
                last_skip_reason=SkipReason.ALREADY_HOME,
                last_armed_at=self._clock.utcnow(),
            )
            if persisted is None:
                return
            pair = persisted
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
            persisted = await self._persist_runtime(
                pair_id,
                last_skip_reason=SkipReason.PANEL_UNAVAILABLE,
                last_disarmed_at=self._clock.utcnow(),
            )
            if persisted is None:
                return
            pair = persisted
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
                # `pair_id`, not `pair.id`: identical value, but `pair` is
                # rebound to the re-read record below, and a closure over a
                # variable reassigned later loses its narrowing.
                lambda: self._mode_changer.async_set_mode(
                    "home", ChangeSource.SCHEDULE_ARM, pair_id=pair_id
                ),
                lambda: self._panel_state() == "armed_home",
            )
        except RetryExhausted as err:
            persisted = await self._persist_runtime(
                pair_id, last_error=str(err.last_error)[:200]
            )
            if persisted is None:
                return
            pair = persisted
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

        persisted = await self._persist_runtime(
            pair_id,
            last_armed_at=armed_at,
            last_error=None,
            last_skip_reason=None,
        )
        if persisted is None:
            return
        pair = persisted
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
        and still within window).  Skip if panel is no longer Home.  Runs as a
        tracked task so teardown can cancel it — see :meth:`_run_tracked`.
        """
        await self._run_tracked(self._disarm_impl(pair_id, source=source))

    async def _disarm_impl(
        self,
        pair_id: str,
        *,
        source: ChangeSource,
    ) -> None:
        """Body of :meth:`async_disarm`; call that instead."""
        pair = self._store.get(pair_id)
        if pair is None or not pair.enabled:
            return

        tz = dt_util.DEFAULT_TIME_ZONE
        if derive_state(pair, now=self._clock.utcnow(), tz=tz) != PairState.ARMED:
            return

        panel_str = self._panel_state()

        if panel_str in ("armed_away", "disarmed"):
            # Panel already changed — manual override won.
            persisted = await self._persist_runtime(
                pair_id,
                last_skip_reason=SkipReason.MANUAL_OVERRIDE,
                last_disarmed_at=self._clock.utcnow(),
            )
            if persisted is None:
                return
            pair = persisted
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
            persisted = await self._persist_runtime(
                pair_id,
                last_skip_reason=SkipReason.PANEL_UNAVAILABLE,
                last_disarmed_at=self._clock.utcnow(),
            )
            if persisted is None:
                return
            pair = persisted
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
                # `pair_id` for the same reason as the arm edge above.
                lambda: self._mode_changer.async_set_mode(
                    "standby", source, pair_id=pair_id
                ),
                lambda: self._panel_state() == "disarmed",
            )
        except RetryExhausted as err:
            persisted = await self._persist_runtime(
                pair_id, last_error=str(err.last_error)[:200]
            )
            if persisted is None:
                return
            pair = persisted
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

        persisted = await self._persist_runtime(
            pair_id,
            last_disarmed_at=disarmed_at,
            last_error=None,
            last_skip_reason=None,
        )
        if persisted is None:
            return
        pair = persisted
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
        defer via :meth:`_defer_until_panel_exists` so reconciliation runs once
        the alarm_control_panel entity is available — on HA start during a boot,
        on the entity appearing after a config-entry reload.  Only defers once;
        the deferred pass runs even if the panel never showed up, and proceeds
        conservatively then (marks PANEL_NOT_HOME).
        """
        panel_str = self._panel_state()

        if panel_str is None and not self._reconcile_deferred:
            self._reconcile_deferred = True

            @callback
            def _reconcile_when_panel_exists() -> None:
                # Tracked: an entry unloaded before HA finishes starting would
                # otherwise reconcile — writing to the store and registering a
                # disarm timer — against a manager nobody holds any more.
                self._track(self.async_reconcile_on_startup())

            # Same reload trap as the override listener, and the worse half of
            # it: `_register_all_timers` only restores the daily *arm* callback,
            # so reconciliation is the only thing that rebuilds a one-shot
            # disarm.  Waiting on an EVENT_HOMEASSISTANT_STARTED that will never
            # fire again left a mid-window reload with the panel armed and
            # nothing scheduled to disarm it (#216).
            self._defer_until_panel_exists(
                PANEL_WAIT_RECONCILE,
                _reconcile_when_panel_exists,
                # A panel that never materialises still needs reconciling: the
                # second pass takes the conservative PANEL_NOT_HOME branch.
                on_missing_panel=RUN_WITHOUT_PANEL,
            )
            return

        now = self._clock.utcnow()
        tz = dt_util.DEFAULT_TIME_ZONE
        reconciled = 0

        # Iterate ids and re-read each one, rather than holding the objects the
        # snapshot returned: this loop awaits inside itself, and a WS edit
        # landing in one iteration's write replaces the record a later iteration
        # is still holding (#202).  Re-reading is what keeps `ed` below — the
        # anchor for the disarm timer this loop registers — computed from the
        # user's current `disarm_time` rather than a superseded one.
        #
        # It is the *record* that is re-read, not what it is compared against:
        # `now` and `panel_str` are deliberately sampled once above, so the whole
        # pass reconciles against one instant and one panel reading rather than
        # drifting partway through.  The loop is bounded by one store write per
        # pair it actually writes, so the drift that would buy is negligible.
        for pair_id in [p.id for p in self._store.get_all()]:
            pair = self._store.get(pair_id)
            if pair is None:
                continue  # deleted while an earlier iteration was writing
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
                persisted = await self._persist_runtime(
                    pair_id,
                    last_disarmed_at=now,
                    last_skip_reason=SkipReason.RECONCILE_WINDOW_ELAPSED,
                )
                if persisted is not None:
                    pair = persisted
                _LOGGER.info(
                    "Schedule '%s' reconciled (window elapsed)", pair.name or pair.id
                )
                continue

            if panel_str != "armed_home":
                persisted = await self._persist_runtime(
                    pair_id,
                    last_disarmed_at=now,
                    last_skip_reason=SkipReason.RECONCILE_PANEL_NOT_HOME,
                )
                if persisted is not None:
                    pair = persisted
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
                self._track(self._disarm_impl(p, source=ChangeSource.RECONCILE_DISARM))

            handle = async_call_later(self._hass, delay, _reconcile_disarm_cb)
            self._set_disarm_handle(pair.id, handle)
            reconciled += 1

        _LOGGER.info("Reconciled %d schedules on startup", reconciled)

    # ------------------------------------------------------------------
    # Manual-override listener — Sub-Phase E
    # ------------------------------------------------------------------

    def _start_panel_listener(self) -> None:
        """Register the alarm-panel state-change listener.

        Defers registration via :meth:`_defer_until_panel_exists` if the panel
        entity is not yet in hass.states — which is every setup, since
        ``async_setup`` runs before the platforms are forwarded.
        Guards against double-registration: a second call is a no-op if the
        listener handle is already set.  Past startup ``_defer_until_panel_exists``
        extends that to an outstanding deferral, so a second call cannot orphan
        the subscription the first one made; the startup branch does not dedup,
        but its retry is idempotent because this guard makes the second one a
        no-op.

        The shutdown guard is what stops the deferred retry from resurrecting
        the listener: shutdown sets the handle back to None, so the "already
        registered" check alone would let a post-teardown retry subscribe a dead
        manager to panel state changes with nothing left to unsubscribe it.
        """
        if self._shutdown or self._listener_handle is not None:
            return
        panel_id = self._panel_entity_id()
        if panel_id is None:
            self._defer_panel_listener()
            return

        # Seed the remembered mode from wherever the panel stands right now, so
        # the very first event has something to compare against.  A panel that
        # is already unavailable seeds None — "we have never seen it Home".
        current = self._panel_state()
        self._last_panel_state = (
            None if current in (None, STATE_UNAVAILABLE, STATE_UNKNOWN) else current
        )
        self._listener_handle = async_track_state_change_event(
            self._hass, [panel_id], self._on_panel_state_changed
        )
        # Registered: drop whatever deferral got us here.
        self._cancel_panel_wait(PANEL_WAIT_LISTENER)

    def _defer_panel_listener(self) -> None:
        """Arrange a retry for when the panel entity shows up."""
        self._defer_until_panel_exists(
            PANEL_WAIT_LISTENER,
            self._start_panel_listener,
            on_missing_panel=(
                "Abode panel entity not found after HA start; "
                "schedule manual-override listener is disabled"
            ),
        )

    def _defer_until_panel_exists(
        self,
        key: str,
        action: Callable[[], None],
        *,
        on_missing_panel: _RunWithoutPanel | str,
    ) -> None:
        """Run ``action`` once the Abode panel entity exists.

        Both callers need this because ``async_setup`` runs *before*
        ``async_forward_entry_setups``: the alarm_control_panel entity is never
        in ``hass.states`` yet, so deferring is the normal path on every setup
        rather than an unusual one.

        Which trigger to wait on depends on whether HA is already up.
        ``EVENT_HOMEASSISTANT_STARTED`` is right during startup, but it fires
        once per process — on a config-entry reload (an options change, a HACS
        update, the Reload button) it has already fired and never fires again,
        so a manager waiting on it waits forever (#216).  Past startup, watch
        for the entity itself instead.

        A panel that never turns up at all — an account with no alarm device,
        or the ``alarm is None`` branch in ``alarm_control_panel`` — is handled
        on both triggers, because "wait forever" is the wrong answer for one of
        the two callers.  ``on_missing_panel`` says which:

        ``RUN_WITHOUT_PANEL``
            Run the action anyway.  Reconciliation has its own panel-less branch
            (it marks the pair ``reconcile_panel_not_home``), and skipping it
            would strand ``last_armed_at`` ahead of ``last_disarmed_at``
            forever — the very shape this file is fixing elsewhere.
        a message
            Log it once as a warning and do not run.  The listener has nothing
            to listen to without a panel; past startup the subscription is kept
            so a panel that shows up late is still adopted, while the startup
            one-shot is spent by then and the listener stays disabled until the
            next restart.
        """
        if self._shutdown:
            # Self-guarded like `_schedule_disarm` and `_register_pair_timers`,
            # rather than trusting both callers: `async_shutdown` has already
            # swept `_panel_wait_handles`, so anything armed past that point is
            # never cancelled — a dead manager left subscribed to every panel
            # added for the life of the process.
            return
        if self._hass.state is CoreState.running:
            if key in self._panel_wait_handles:
                return  # already waiting on this one — do not leak the handle

            handles: list[CancelHandle] = []

            @callback
            def _cancel_all() -> None:
                for handle in handles:
                    handle()

            @callback
            def _proceed() -> None:
                self._cancel_panel_wait(key)
                action()

            @callback
            def _on_panel_added(_event: Event[EventStateChangedData]) -> None:
                if self._shutdown:
                    return
                if self._panel_entity_id() is None:
                    # Another integration's alarm_control_panel — keep waiting.
                    return
                _proceed()

            @callback
            def _panel_never_arrived(_now: datetime) -> None:
                # The state-added subscription alone would wait forever, which
                # for reconciliation means the pair never leaves ARMED (#216).
                if self._shutdown or self._panel_entity_id() is not None:
                    return
                if isinstance(on_missing_panel, str):
                    # Keep waiting — unlike the one-shot, this subscription
                    # survives, so a late panel is still picked up.
                    _LOGGER.warning(on_missing_panel)
                    return
                _LOGGER.debug(
                    "Abode panel entity still absent after %ss (%s); "
                    "proceeding without it",
                    PANEL_WAIT_TIMEOUT,
                    key,
                )
                _proceed()

            handles.append(
                async_track_state_added_domain(
                    self._hass, Platform.ALARM_CONTROL_PANEL, _on_panel_added
                )
            )
            handles.append(
                async_call_later(self._hass, PANEL_WAIT_TIMEOUT, _panel_never_arrived)
            )
            self._panel_wait_handles[key] = _cancel_all
            _LOGGER.debug(
                "Abode panel entity not present yet (%s); waiting for it to be added",
                key,
            )
            return

        @callback
        def _retry(_event: Event[Any]) -> None:
            if self._shutdown:
                # Checked before the panel lookup, not just via the caller's
                # own guard: unloading the entry removes the
                # alarm_control_panel entity, so an unloaded manager takes the
                # warning branch below and blames a missing panel for a
                # teardown it caused itself.
                return
            if self._panel_entity_id() is None and isinstance(on_missing_panel, str):
                _LOGGER.warning(on_missing_panel)
                return
            action()

        self._hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _retry)

    @callback
    def _cancel_panel_wait(self, key: str) -> None:
        """Drop one outstanding state-added subscription, if any."""
        handle = self._panel_wait_handles.pop(key, None)
        if handle is not None:
            handle()

    @callback
    def _on_panel_state_changed(self, event: Event[EventStateChangedData]) -> None:
        """Filter state-change events; ignore self-driven schedule transitions."""
        new_state = event.data.get("new_state")

        # Losing the panel is not a mode change.  An Abode cloud dropout drives
        # armed_home -> unavailable -> armed_home in a couple of minutes, and HA
        # mints a fresh context when it marks an entity unavailable, so the
        # CONTEXT_ID_PREFIX check below cannot filter it out.  Treating that as a
        # manual override cancelled the pending disarm and stranded the panel
        # armed for the rest of the night (#216).  Return *without* touching
        # `_last_panel_state`: the blip must not erase the fact that the panel
        # was Home going into it.
        #
        # Excluding those two by name is exhaustive only because the panel maps
        # to `disarmed` / `armed_home` / `armed_away` and nothing else (see
        # AbodeAlarm._sync_attrs in ../alarm_control_panel.py, whose None renders
        # as `unknown`).  Teaching it a transitional state such as `arming` or
        # `triggered` means revisiting this guard.
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        # The comparison is against the last mode the panel was known to be in,
        # not the event's own `old_state`, precisely so a change made while HA
        # was blind still reads correctly: recovering as `disarmed` or
        # `armed_away` is a real leave-Home edge and must still register.
        previous = self._last_panel_state
        # Recorded before the self-driven early return, and unconditionally: our
        # own disarm has to move the memory off armed_home too, or the next
        # genuine change would be misread as leaving Home.  (The old code got
        # this for free from `old_state`.)
        self._last_panel_state = new_state.state

        ctx_id = event.context.id or ""
        if ctx_id.startswith(CONTEXT_ID_PREFIX):
            return  # our own change — ignore

        if new_state.state == "armed_home":
            return
        if previous != "armed_home":
            return

        # Transition left armed_home via a non-self-driven context.
        self._track(self._handle_manual_override())

    async def _handle_manual_override(self) -> None:
        """Cancel pending disarms for all ARMED pairs and mark them overridden."""
        now = self._clock.utcnow()
        tz = dt_util.DEFAULT_TIME_ZONE

        # Ids, then a re-read per iteration, for the same reason as the
        # reconcile loop: this one awaits inside itself too, so the `enabled`
        # and `derive_state` guards below have to run against the record as it
        # stands now rather than as the snapshot found it (#202).  `now` is
        # sampled once for the same reason it is there — one override, one
        # instant, so the pairs it marks all agree on when it happened.
        for pair_id in [p.id for p in self._store.get_all()]:
            pair = self._store.get(pair_id)
            if pair is None:
                continue  # deleted while an earlier iteration was writing
            if not pair.enabled:
                continue
            if derive_state(pair, now=now, tz=tz) != PairState.ARMED:
                continue
            handle = self._pending_handles.pop((pair_id, "disarm"), None)
            if handle is not None:
                handle()
            # Persist BEFORE firing the event (spec constraint).
            persisted = await self._persist_runtime(
                pair_id,
                last_disarmed_at=now,
                last_skip_reason=SkipReason.MANUAL_OVERRIDE,
            )
            if persisted is None:
                continue
            pair = persisted
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
