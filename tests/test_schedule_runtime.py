"""Runtime tests for ScheduleManager (arm/disarm, skip rules, reconciliation, listener).

All tests use fake Clock, ScheduleClock, and ModeChanger so they run without a
mock Abode server.  Time control relies on:
  - FakeClock.utcnow() for manager-internal timestamps.
  - async_fire_time_changed(hass, dt, fire_all=True) to fire async_call_later
    callbacks (which use async_track_point_in_utc_time internally).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Generator
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import Context, CoreState, HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.abode_security.const import (
    CONTEXT_ID_PREFIX,
    EVENT_SCHEDULE_FAILED,
    EVENT_SCHEDULE_FIRED,
    EVENT_SCHEDULE_SKIPPED,
    REPAIR_ISSUE_SCHEDULE_FIRE_FAILED,
    SCHEDULE_RETRY_TOTAL_ATTEMPTS,
)
from custom_components.abode_security.scheduling.manager import (
    PANEL_WAIT_LISTENER,
    PANEL_WAIT_RECONCILE,
    PANEL_WAIT_TIMEOUT,
    RUN_WITHOUT_PANEL,
    ScheduleManager,
)
from custom_components.abode_security.scheduling.mode_changer import ModeChangeFailed
from custom_components.abode_security.scheduling.models import (
    ChangeSource,
    ScheduledPair,
    SkipReason,
)
from custom_components.abode_security.scheduling.scheduler import CancelHandle
from custom_components.abode_security.scheduling.state_machine import expected_disarm_at
from custom_components.abode_security.scheduling.store import SchedulesStore

# ---------------------------------------------------------------------------
# Helpers — event capture
# ---------------------------------------------------------------------------

_PANEL = "alarm_control_panel.abode_test"


def _set_panel(hass: HomeAssistant, state: str, context: Context | None = None) -> None:
    hass.states.async_set(_PANEL, state, context=context)


@contextmanager
def _no_retry_sleeps() -> Generator[None]:
    """Make the retry backoff and the #192 confirmation wait instant.

    Note this stubs the stdlib ``asyncio.sleep`` for the duration of the block —
    ``retry_mod.asyncio`` is the module singleton, not a module-local alias — so
    keep the block tight around the call under test.  ``patch.object`` restores
    it on every exit path, including exceptions.
    """
    import custom_components.abode_security.scheduling.retry as retry_mod

    with patch.object(retry_mod.asyncio, "sleep", AsyncMock()):
        yield


def _capture_events(hass: HomeAssistant, event_name: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    async def _listener(ev):  # type: ignore[no-untyped-def]
        events.append(ev.data)

    hass.bus.async_listen(event_name, _listener)
    return events


async def _expected_disarm(manager: ScheduleManager, pair_id: str) -> datetime:
    """Compute a pair's expected disarm instant using the live HA timezone.

    The runtime hass fixture sets a non-UTC timezone, so tests must derive the
    disarm boundary the same way the manager does rather than hardcoding a UTC
    wall-clock time.
    """
    pair = await manager.async_get(pair_id)
    assert pair is not None and pair.last_armed_at is not None
    return expected_disarm_at(
        pair, last_armed_at=pair.last_armed_at, tz=dt_util.DEFAULT_TIME_ZONE
    )


# ---------------------------------------------------------------------------
# Fake dependencies
# ---------------------------------------------------------------------------


class FakeClock:
    """Controllable clock for tests."""

    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime(2030, 1, 7, 22, 0, 0, tzinfo=UTC)

    def set(self, dt: datetime) -> None:
        self._now = dt

    def now(self) -> datetime:
        return self._now

    def utcnow(self) -> datetime:
        return self._now


class FakeScheduleClock:
    """Stores registered arm callbacks; never auto-fires."""

    def __init__(self) -> None:
        self._handles: dict[int, dict[str, Any]] = {}
        self._next_id = 0

    def async_track_daily(
        self,
        callback: Callable[[], Awaitable[None]],
        *,
        hour: int,
        minute: int,
        weekdays: frozenset[int],
    ) -> CancelHandle:
        hid = self._next_id
        self._next_id += 1
        self._handles[hid] = {
            "callback": callback,
            "hour": hour,
            "minute": minute,
            "weekdays": weekdays,
        }

        def cancel() -> None:
            self._handles.pop(hid, None)

        return cancel

    async def fire(self, hour: int, minute: int) -> None:
        """Manually trigger all callbacks registered for (hour, minute)."""
        for info in list(self._handles.values()):
            if info["hour"] == hour and info["minute"] == minute:
                await info["callback"]()


class FakeModeChanger:
    """Records calls; raises ModeChangeFailed on demand."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self._fail_times: int = 0  # how many times to fail before succeeding
        self.attempts: int = 0  # every call, successful or not
        # Called with the 1-based attempt number before the call resolves.  Lets
        # a test move the panel underneath an in-flight mode change, the way a
        # real ~60 s arm completes while retries are still firing (#192).
        self.on_attempt: Callable[[int], None] | None = None
        # Set by `block()`: the call parks until released, standing in for an
        # operation still in flight at teardown (#201).
        self.started = asyncio.Event()
        self._release: asyncio.Event | None = None

    def set_fail_count(self, n: int) -> None:
        self._fail_times = n

    def block(self) -> asyncio.Event:
        """Make every call hang until the returned Event is set.

        Stands in for the confirmation wait: a real in-flight operation is
        parked on an ``asyncio.sleep`` inside the poll, and this parks on an
        Event instead so a test controls when — and whether — it resumes.
        """
        self._release = asyncio.Event()
        return self._release

    async def async_set_mode(
        self,
        target: str,
        source: ChangeSource,
        *,
        pair_id: str | None = None,
    ) -> None:
        self.attempts += 1
        if self.on_attempt is not None:
            self.on_attempt(self.attempts)
        if self._release is not None:
            self.started.set()
            await self._release.wait()
        if self._fail_times > 0:
            self._fail_times -= 1
            raise ModeChangeFailed("transient error")
        self.calls.append({"target": target, "source": source, "pair_id": pair_id})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock(datetime(2030, 1, 7, 22, 0, 0, tzinfo=UTC))


@pytest.fixture
def fake_scheduler() -> FakeScheduleClock:
    return FakeScheduleClock()


@pytest.fixture
def fake_mode_changer() -> FakeModeChanger:
    return FakeModeChanger()


@pytest.fixture
async def manager(
    hass: HomeAssistant,
    fake_clock: FakeClock,
    fake_scheduler: FakeScheduleClock,
    fake_mode_changer: FakeModeChanger,
):
    store = SchedulesStore(hass)
    mgr = ScheduleManager(hass, store, fake_clock, fake_scheduler, fake_mode_changer)
    await store.async_load()  # load empty store; skip full async_setup
    yield mgr
    await mgr.async_shutdown()


# ---------------------------------------------------------------------------
# Sub-Phase C: arm / disarm flows
# ---------------------------------------------------------------------------


class TestArmFlow:
    async def test_happy_path_arm(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Arm fires mode_changer and emits schedule_fired event."""
        _set_panel(hass, "disarmed")
        fired = _capture_events(hass, EVENT_SCHEDULE_FIRED)

        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        await manager.async_arm(pair.id)

        assert len(fake_mode_changer.calls) == 1
        call = fake_mode_changer.calls[0]
        assert call["target"] == "home"
        assert call["source"] == ChangeSource.SCHEDULE_ARM
        assert call["pair_id"] == pair.id

        await hass.async_block_till_done()
        assert len(fired) == 1
        assert fired[0]["action"] == "arm"
        assert fired[0]["target_mode"] == "home"
        assert fired[0]["schedule_id"] == pair.id

    async def test_happy_path_disarm_after_arm(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """After arm, disarm fires at expected_disarm_at time."""
        _set_panel(hass, "disarmed")

        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        await manager.async_arm(pair.id)

        # Simulate panel going to armed_home (arm succeeded).
        _set_panel(hass, "armed_home")

        fired = _capture_events(hass, EVENT_SCHEDULE_FIRED)

        # Advance clock and fire time-based callbacks for disarm.  Fire a couple
        # of seconds PAST the exact boundary: async_call_later fires at-or-after
        # the scheduled instant, so the real utcnow() read inside async_disarm is
        # always a hair late.  Pinning the clock to the exact microsecond would
        # mask the boundary bug (see test_disarm_fires_when_slightly_past_boundary).
        disarm_dt = await _expected_disarm(manager, pair.id) + timedelta(seconds=2)
        fake_clock.set(disarm_dt)
        async_fire_time_changed(hass, disarm_dt, fire_all=True)
        await hass.async_block_till_done(wait_background_tasks=True)

        disarm_calls = [c for c in fake_mode_changer.calls if c["target"] == "standby"]
        assert len(disarm_calls) == 1
        assert disarm_calls[0]["source"] == ChangeSource.SCHEDULE_DISARM
        assert disarm_calls[0]["pair_id"] == pair.id

        await hass.async_block_till_done()
        assert any(e["action"] == "disarm" for e in fired)

    @pytest.mark.parametrize(
        "late_delta",
        [
            timedelta(microseconds=1),  # event-loop jitter
            timedelta(seconds=2),  # task-scheduling latency
            timedelta(minutes=1),  # event-loop backlog, still within grace
        ],
    )
    async def test_disarm_fires_when_slightly_past_boundary(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
        late_delta: timedelta,
    ) -> None:
        """Regression: disarm still fires when utcnow() is just past expected_disarm.

        The one-shot disarm timer fires at-or-after expected_disarm_at, so the
        clock is always slightly late by the time async_disarm re-checks the
        derived state.  Before the DISARM_WINDOW_GRACE fix, the strict
        ``now > expected_disarm`` check treated the pair as IDLE and silently
        skipped the disarm (panel stayed armed).
        """
        _set_panel(hass, "disarmed")
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        await manager.async_arm(pair.id)
        _set_panel(hass, "armed_home")

        fire_at = await _expected_disarm(manager, pair.id) + late_delta
        fake_clock.set(fire_at)
        async_fire_time_changed(hass, fire_at, fire_all=True)
        await hass.async_block_till_done(wait_background_tasks=True)

        disarm_calls = [c for c in fake_mode_changer.calls if c["target"] == "standby"]
        assert len(disarm_calls) == 1, f"disarm skipped for late_delta={late_delta}"
        assert disarm_calls[0]["source"] == ChangeSource.SCHEDULE_DISARM

    async def test_disarm_skipped_when_window_missed_beyond_grace(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """A window missed by more than the grace is treated as IDLE — no disarm.

        Protects the safety net: if the timer somehow fires hours late (e.g. the
        event loop was wedged), we must NOT auto-disarm long after the intended
        window.  The conservative startup-reconcile path handles genuine misses.
        """
        _set_panel(hass, "disarmed")
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        await manager.async_arm(pair.id)
        _set_panel(hass, "armed_home")

        fire_at = await _expected_disarm(manager, pair.id) + timedelta(hours=2)
        fake_clock.set(fire_at)
        async_fire_time_changed(hass, fire_at, fire_all=True)
        await hass.async_block_till_done(wait_background_tasks=True)

        disarm_calls = [c for c in fake_mode_changer.calls if c["target"] == "standby"]
        assert len(disarm_calls) == 0

    async def test_skip_away_active(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """When panel is armed_away, arm is skipped and no mode_changer call made."""
        _set_panel(hass, "armed_away")
        skipped = _capture_events(hass, EVENT_SCHEDULE_SKIPPED)

        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        await manager.async_arm(pair.id)

        assert len(fake_mode_changer.calls) == 0
        await hass.async_block_till_done()
        assert len(skipped) == 1
        assert skipped[0]["reason"] == SkipReason.AWAY_ACTIVE

        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        assert refreshed.last_disarmed_at is not None
        assert refreshed.last_armed_at is None

        # Disarm timer must NOT fire (last_disarmed_at is set, pair is IDLE).
        _set_panel(hass, "armed_home")
        async_fire_time_changed(
            hass, datetime(2030, 1, 8, 6, 0, 0, tzinfo=UTC), fire_all=True
        )
        await hass.async_block_till_done(wait_background_tasks=True)
        assert len(fake_mode_changer.calls) == 0

    async def test_skip_already_home_takes_ownership_and_schedules_disarm(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """When panel is already armed_home, no arm call but last_armed_at set and disarm scheduled."""
        _set_panel(hass, "armed_home")
        skipped = _capture_events(hass, EVENT_SCHEDULE_SKIPPED)

        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        await manager.async_arm(pair.id)

        assert len(fake_mode_changer.calls) == 0
        await hass.async_block_till_done()
        assert len(skipped) == 1
        assert skipped[0]["reason"] == SkipReason.ALREADY_HOME

        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        assert refreshed.last_armed_at is not None

        # Disarm SHOULD fire later.
        fired = _capture_events(hass, EVENT_SCHEDULE_FIRED)
        disarm_dt = datetime(2030, 1, 8, 6, 0, 0, tzinfo=UTC)
        fake_clock.set(disarm_dt)
        async_fire_time_changed(hass, disarm_dt, fire_all=True)
        await hass.async_block_till_done(wait_background_tasks=True)

        disarm_calls = [c for c in fake_mode_changer.calls if c["target"] == "standby"]
        assert len(disarm_calls) == 1
        assert any(e["action"] == "disarm" for e in fired)

    async def test_skip_panel_unavailable(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Intermediate panel states → skip with panel_unavailable reason."""
        for state in ("unavailable", "unknown", "arming", "triggered"):
            _set_panel(hass, state)
            skipped = _capture_events(hass, EVENT_SCHEDULE_SKIPPED)

            pair = await manager.async_create(
                weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
            )
            await manager.async_arm(pair.id)
            await hass.async_block_till_done()

            assert len(skipped) == 1
            assert skipped[0]["reason"] == SkipReason.PANEL_UNAVAILABLE
            await manager.async_delete(pair.id)

    async def test_skip_panel_none(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """If panel entity not registered, skip with panel_unavailable."""
        # Don't set any panel state.
        skipped = _capture_events(hass, EVENT_SCHEDULE_SKIPPED)

        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        await manager.async_arm(pair.id)
        await hass.async_block_till_done()

        assert len(skipped) == 1
        assert skipped[0]["reason"] == SkipReason.PANEL_UNAVAILABLE

    async def test_disabled_pair_noop(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_mode_changer: FakeModeChanger,
        fake_scheduler: FakeScheduleClock,
    ) -> None:
        """Disabled pair registers no timers and async_arm is a no-op."""
        _set_panel(hass, "disarmed")

        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00", enabled=False
        )
        # No arm handle registered.
        assert (pair.id, "arm") not in manager._pending_handles

        await manager.async_arm(pair.id)
        assert len(fake_mode_changer.calls) == 0

    async def test_unknown_pair_id_noop(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        await manager.async_arm("nonexistent-id")
        assert len(fake_mode_changer.calls) == 0

    async def test_arm_timer_registered_on_create(
        self,
        manager: ScheduleManager,
        fake_scheduler: FakeScheduleClock,
    ) -> None:
        """Creating a pair registers an arm timer."""
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        assert (pair.id, "arm") in manager._pending_handles

    async def test_update_re_registers_timers(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_scheduler: FakeScheduleClock,
    ) -> None:
        """Updating a pair cancels old handle and registers a new one."""
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        old_handle = manager._pending_handles[(pair.id, "arm")]

        # Patch to track if old handle was called.
        cancelled = []
        original = old_handle

        def tracking_cancel() -> None:
            cancelled.append(True)
            original()

        manager._pending_handles[(pair.id, "arm")] = tracking_cancel

        await manager.async_update(pair.id, arm_time="21:00")
        assert len(cancelled) == 1
        assert (pair.id, "arm") in manager._pending_handles

    async def test_update_while_armed_preserves_disarm(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Editing a pair while armed must NOT drop the pending disarm timer.

        Regression: async_update cancels all handles then re-registers only the
        arm timer.  Without preserving the on-demand disarm handle, a name edit
        or `enabled` toggle while the panel is armed would leave it armed with no
        auto-disarm.
        """
        _set_panel(hass, "disarmed")
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        await manager.async_arm(pair.id)
        _set_panel(hass, "armed_home")
        assert (pair.id, "disarm") in manager._pending_handles

        # Edit an arm-unrelated field while armed.
        await manager.async_update(pair.id, name="Weeknights")
        assert (pair.id, "disarm") in manager._pending_handles, (
            "pending disarm was dropped by async_update"
        )

        # Disarm must still fire at the (unchanged) expected time.
        fire_at = await _expected_disarm(manager, pair.id) + timedelta(seconds=2)
        fake_clock.set(fire_at)
        async_fire_time_changed(hass, fire_at, fire_all=True)
        await hass.async_block_till_done(wait_background_tasks=True)

        disarm_calls = [c for c in fake_mode_changer.calls if c["target"] == "standby"]
        assert len(disarm_calls) == 1

    async def test_update_disarm_time_while_armed_reschedules(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Editing disarm_time while armed recomputes the disarm boundary.

        The pending disarm is rebuilt from the updated pair (the comment in
        async_update promises a changed disarm_time reschedules correctly), so
        the guard now accepts the NEW expected_disarm_at.  A clock value between
        the old and new boundary — which the original 06:00 window would have
        treated as elapsed (past grace) and skipped — must still disarm.
        """
        _set_panel(hass, "disarmed")
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        await manager.async_arm(pair.id)
        _set_panel(hass, "armed_home")
        old_disarm = await _expected_disarm(manager, pair.id)

        # Move disarm later (07:00); the timer must follow.
        await manager.async_update(pair.id, disarm_time="07:00")
        assert (pair.id, "disarm") in manager._pending_handles
        new_disarm = await _expected_disarm(manager, pair.id)
        # New boundary is an hour later than the old one.
        assert new_disarm == old_disarm + timedelta(hours=1)

        # Fire at a clock between old (06:00) and new (07:00) boundary, well past
        # the old window's grace.  Under the new disarm_time this is still within
        # the window → ARMED → disarms.  Had the edit not been applied to the
        # derived window, this would be treated as elapsed and skipped.
        fire_at = old_disarm + timedelta(minutes=30)
        assert fire_at > old_disarm + timedelta(minutes=5)  # past old grace
        assert fire_at < new_disarm
        fake_clock.set(fire_at)
        async_fire_time_changed(hass, fire_at, fire_all=True)
        await hass.async_block_till_done(wait_background_tasks=True)
        disarm_calls = [c for c in fake_mode_changer.calls if c["target"] == "standby"]
        assert len(disarm_calls) == 1

    async def test_update_disabling_while_armed_cancels_disarm(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Disabling a pair while armed cancels the pending disarm (no auto-disarm)."""
        _set_panel(hass, "disarmed")
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        await manager.async_arm(pair.id)
        _set_panel(hass, "armed_home")
        assert (pair.id, "disarm") in manager._pending_handles

        fire_at = await _expected_disarm(manager, pair.id) + timedelta(seconds=2)
        await manager.async_update(pair.id, enabled=False)
        assert (pair.id, "disarm") not in manager._pending_handles

        fake_clock.set(fire_at)
        async_fire_time_changed(hass, fire_at, fire_all=True)
        await hass.async_block_till_done(wait_background_tasks=True)

        disarm_calls = [c for c in fake_mode_changer.calls if c["target"] == "standby"]
        assert len(disarm_calls) == 0

    async def test_delete_cancels_timers(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_scheduler: FakeScheduleClock,
    ) -> None:
        """Deleting a pair cancels its arm timer."""
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        assert (pair.id, "arm") in manager._pending_handles

        await manager.async_delete(pair.id)
        assert (pair.id, "arm") not in manager._pending_handles


class TestRetryBehavior:
    async def test_retry_success_on_attempt_2(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """mode_changer fails once, then succeeds — arm completes, no schedule_failed."""
        _set_panel(hass, "disarmed")
        failed_events = _capture_events(hass, EVENT_SCHEDULE_FAILED)

        fake_mode_changer.set_fail_count(1)
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )

        with _no_retry_sleeps():
            await manager.async_arm(pair.id)

        await hass.async_block_till_done()
        assert len(failed_events) == 0
        # Should have succeeded eventually (fail once, then succeed).
        arm_calls = [c for c in fake_mode_changer.calls if c["target"] == "home"]
        assert len(arm_calls) == 1

    async def test_retry_exhaustion_fires_schedule_failed_and_repair_issue(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """All retries exhausted → schedule_failed event + repair issue + pair stays IDLE."""
        _set_panel(hass, "disarmed")
        failed = _capture_events(hass, EVENT_SCHEDULE_FAILED)

        fake_mode_changer.set_fail_count(999)
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )

        with _no_retry_sleeps():
            await manager.async_arm(pair.id)

        await hass.async_block_till_done()

        assert len(failed) == 1
        assert failed[0]["attempts"] == SCHEDULE_RETRY_TOTAL_ATTEMPTS
        assert failed[0]["action"] == "arm"

        # Repair issue raised.
        issue_reg = ir.async_get(hass)
        issue = issue_reg.async_get_issue(
            "abode_security",
            f"{REPAIR_ISSUE_SCHEDULE_FIRE_FAILED}_{pair.id}",
        )
        assert issue is not None

        # Pair still IDLE — last_armed_at not set.
        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        assert refreshed.last_armed_at is None

    async def test_repair_issue_cleared_on_next_success(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Repair issue is cleared after a successful arm following a failure."""
        _set_panel(hass, "disarmed")

        fake_mode_changer.set_fail_count(999)
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )

        with _no_retry_sleeps():
            await manager.async_arm(pair.id)

        issue_reg = ir.async_get(hass)
        assert (
            issue_reg.async_get_issue(
                "abode_security", f"{REPAIR_ISSUE_SCHEDULE_FIRE_FAILED}_{pair.id}"
            )
            is not None
        )

        # Now let it succeed.
        fake_mode_changer.set_fail_count(0)
        _set_panel(hass, "disarmed")
        await manager.async_arm(pair.id)

        assert (
            issue_reg.async_get_issue(
                "abode_security", f"{REPAIR_ISSUE_SCHEDULE_FIRE_FAILED}_{pair.id}"
            )
            is None
        )


class TestStateConfirmation:
    """#192 — a successful arm must never be reported as a failure.

    Abode's arm takes ~60 s and answers any mode change issued while it is in
    progress with `2104 Operation error!`.  The retry window (1+4+16 = 21 s) is
    shorter than that, so every retry lands mid-transition and the last one's
    error used to be reported as a total failure — for an arm that worked.
    """

    async def test_arm_confirmed_mid_retry_is_not_a_failure(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Panel reaches armed_home while retries are still firing."""
        _set_panel(hass, "disarmed")
        failed = _capture_events(hass, EVENT_SCHEDULE_FAILED)
        fired = _capture_events(hass, EVENT_SCHEDULE_FIRED)

        # Every call is rejected with 2104, exactly as the live system saw.
        fake_mode_changer.set_fail_count(999)
        # The panel finishes arming while attempt 2 is in flight.
        fake_mode_changer.on_attempt = lambda n: (
            _set_panel(hass, "armed_home") if n == 2 else None
        )

        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )

        with _no_retry_sleeps():
            await manager.async_arm(pair.id)

        await hass.async_block_till_done()

        # No false failure.
        assert failed == []
        issue_reg = ir.async_get(hass)
        assert (
            issue_reg.async_get_issue(
                "abode_security", f"{REPAIR_ISSUE_SCHEDULE_FIRE_FAILED}_{pair.id}"
            )
            is None
        )

        # Treated as the success it was: fired event, armed timestamp, no error,
        # and the matching disarm scheduled.
        assert len(fired) == 1
        assert fired[0]["action"] == "arm"
        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        # Anchored at the arm edge — see the dedicated anchor test below.
        assert refreshed.last_armed_at == fake_clock.utcnow()
        assert refreshed.last_error is None
        assert (pair.id, "disarm") in manager._pending_handles

        # Attempts stop once the panel confirms the target state rather than
        # burning the remaining retries on more 2104s.
        assert fake_mode_changer.attempts == 2

    async def test_arm_confirmed_after_retries_exhausted_is_not_a_failure(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """The whole 21 s retry window falls inside a slow arm.

        All four attempts fail; the panel only settles afterwards, during the
        post-exhaustion confirmation wait.
        """
        _set_panel(hass, "disarmed")
        failed = _capture_events(hass, EVENT_SCHEDULE_FAILED)
        fired = _capture_events(hass, EVENT_SCHEDULE_FIRED)

        fake_mode_changer.set_fail_count(999)
        fake_mode_changer.on_attempt = lambda n: (
            _set_panel(hass, "armed_home")
            if n == SCHEDULE_RETRY_TOTAL_ATTEMPTS
            else None
        )

        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )

        with _no_retry_sleeps():
            await manager.async_arm(pair.id)

        await hass.async_block_till_done()

        assert failed == []
        assert len(fired) == 1
        issue_reg = ir.async_get(hass)
        assert (
            issue_reg.async_get_issue(
                "abode_security", f"{REPAIR_ISSUE_SCHEDULE_FIRE_FAILED}_{pair.id}"
            )
            is None
        )
        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        assert refreshed.last_armed_at is not None
        assert fake_mode_changer.attempts == SCHEDULE_RETRY_TOTAL_ATTEMPTS

    async def test_disarm_confirmed_mid_retry_is_not_a_failure(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Same confirmation applies to the disarm edge."""
        _set_panel(hass, "disarmed")
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        await manager.async_arm(pair.id)
        _set_panel(hass, "armed_home")

        failed = _capture_events(hass, EVENT_SCHEDULE_FAILED)
        fired = _capture_events(hass, EVENT_SCHEDULE_FIRED)

        fake_mode_changer.set_fail_count(999)
        fake_mode_changer.on_attempt = lambda n: (
            _set_panel(hass, "disarmed") if n == 2 else None
        )

        with _no_retry_sleeps():
            await manager.async_disarm(pair.id)

        await hass.async_block_till_done()

        assert failed == []
        assert any(e["action"] == "disarm" for e in fired)
        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        assert refreshed.last_error is None

    async def test_panel_that_never_reaches_target_still_fails(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Confirmation must not swallow a genuine failure."""
        _set_panel(hass, "disarmed")
        failed = _capture_events(hass, EVENT_SCHEDULE_FAILED)

        fake_mode_changer.set_fail_count(999)  # panel never moves
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )

        with _no_retry_sleeps():
            await manager.async_arm(pair.id)

        await hass.async_block_till_done()

        assert len(failed) == 1
        assert failed[0]["attempts"] == SCHEDULE_RETRY_TOTAL_ATTEMPTS
        issue_reg = ir.async_get(hass)
        assert (
            issue_reg.async_get_issue(
                "abode_security", f"{REPAIR_ISSUE_SCHEDULE_FIRE_FAILED}_{pair.id}"
            )
            is not None
        )

    async def test_arm_is_anchored_to_the_edge_not_the_confirmation(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """A slow confirmation must not push the auto-disarm a day out.

        `expected_disarm_at` rolls forward a full day once the anchor is past
        `disarm_time`.  Confirmation can spend up to 111 s (21 s of retries plus
        the 90 s wait), so anchoring on the confirmation instead of the edge
        would silently leave a short window — arm 22:00 / disarm 22:01, a legal
        configuration — armed for ~24 h.
        """
        edge = datetime(2030, 1, 7, 22, 0, 0, tzinfo=UTC)
        fake_clock.set(edge)

        # Derive the HH:MM strings from the live HA tz: the runtime hass fixture
        # is not UTC, and the pair's times are wall-clock local.
        local = edge.astimezone(dt_util.DEFAULT_TIME_ZONE)
        arm_time = local.strftime("%H:%M")
        disarm_time = (local + timedelta(minutes=1)).strftime("%H:%M")

        _set_panel(hass, "disarmed")
        pair = await manager.async_create(
            weekdays=["mon"], arm_time=arm_time, disarm_time=disarm_time
        )

        # Every attempt is rejected and each one burns 30 s of wall clock, so
        # confirmation lands well past the 22:01 disarm boundary.
        fake_mode_changer.set_fail_count(999)

        def _advance(n: int) -> None:
            fake_clock.set(edge + timedelta(seconds=30 * n))
            if n == SCHEDULE_RETRY_TOTAL_ATTEMPTS:
                _set_panel(hass, "armed_home")

        fake_mode_changer.on_attempt = _advance

        with _no_retry_sleeps():
            await manager.async_arm(pair.id)
        await hass.async_block_till_done()

        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        # Anchored at the edge, not at the (much later) confirmation.
        assert refreshed.last_armed_at == edge
        assert fake_clock.utcnow() > edge  # the clock really did move

        # The consequence that matters: disarm stays ~1 minute out, not ~24 h.
        assert await _expected_disarm(manager, pair.id) - edge < timedelta(minutes=5)

        # And the timer those values exist to produce is actually registered.
        # Anchoring at the edge pushes this delay negative for a window shorter
        # than the confirmation budget; dropping the timer there would leave the
        # panel armed with nothing to disarm it.
        assert (pair.id, "disarm") in manager._pending_handles

    async def test_disarm_boundary_passed_during_confirmation_fires_immediately(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """A boundary passed inside the grace disarms now; past it, it is dropped."""
        edge = datetime(2030, 1, 7, 22, 0, 0, tzinfo=UTC)
        fake_clock.set(edge)
        local = edge.astimezone(dt_util.DEFAULT_TIME_ZONE)

        _set_panel(hass, "disarmed")
        pair = await manager.async_create(
            weekdays=["mon"],
            arm_time=local.strftime("%H:%M"),
            disarm_time=(local + timedelta(minutes=1)).strftime("%H:%M"),
        )
        await manager.async_arm(pair.id)
        assert (pair.id, "disarm") in manager._pending_handles

        # 2 minutes past the edge: 1 minute past the disarm boundary, well
        # inside DISARM_WINDOW_GRACE — the timer is registered to fire at once.
        manager._unregister_timers(pair.id)
        fake_clock.set(edge + timedelta(minutes=2))
        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        manager._schedule_disarm(refreshed)
        assert (pair.id, "disarm") in manager._pending_handles

        # 10 minutes past the edge is past the grace — derive_state calls the
        # pair IDLE by then, so async_disarm would no-op; skipping is correct.
        manager._unregister_timers(pair.id)
        fake_clock.set(edge + timedelta(minutes=10))
        manager._schedule_disarm(refreshed)
        assert (pair.id, "disarm") not in manager._pending_handles


class TestOverlappingPairs:
    async def test_overlapping_pairs_a_then_b_then_a_disarm_then_b_disarm(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Two overlapping pairs: A arms 22:00→06:00, B arms 23:00→08:00.

        Step-by-step assertions as specified in the spec's Overlapping pairs test.
        Calls async_disarm directly instead of firing time-based callbacks, because
        the overlapping-pairs logic is about business rules, not timer plumbing
        (which is already covered by test_happy_path_disarm_after_arm).
        """
        arm_a_dt = datetime(2030, 1, 7, 22, 0, 0, tzinfo=UTC)
        arm_b_dt = datetime(2030, 1, 7, 23, 0, 0, tzinfo=UTC)
        disarm_a_dt = datetime(2030, 1, 8, 6, 0, 0, tzinfo=UTC)
        disarm_b_dt = datetime(2030, 1, 8, 8, 0, 0, tzinfo=UTC)

        fake_clock.set(datetime(2030, 1, 7, 20, 0, 0, tzinfo=UTC))
        pair_a = await manager.async_create(
            name="A", weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        pair_b = await manager.async_create(
            name="B", weekdays=["mon"], arm_time="23:00", disarm_time="08:00"
        )

        # Step 1: At 22:00, A arms. Panel is disarmed.
        fake_clock.set(arm_a_dt)
        _set_panel(hass, "disarmed")
        await manager.async_arm(pair_a.id)
        assert len([c for c in fake_mode_changer.calls if c["target"] == "home"]) == 1
        assert fake_mode_changer.calls[-1]["pair_id"] == pair_a.id
        ra = await manager.async_get(pair_a.id)
        assert ra is not None and ra.last_armed_at is not None

        # Step 2: At 23:00, B arms. Panel is armed_home (A just armed it).
        fake_clock.set(arm_b_dt)
        _set_panel(hass, "armed_home")
        skipped = _capture_events(hass, EVENT_SCHEDULE_SKIPPED)
        await manager.async_arm(pair_b.id)
        home_calls = [c for c in fake_mode_changer.calls if c["target"] == "home"]
        assert len(home_calls) == 1  # no mode_changer call for B (already_home)
        await hass.async_block_till_done()
        assert any(e["reason"] == SkipReason.ALREADY_HOME for e in skipped)
        rb = await manager.async_get(pair_b.id)
        assert rb is not None and rb.last_armed_at is not None

        # Step 3: At 06:00, A's disarm timer fires (simulated via direct call).
        # Panel is armed_home → disarm proceeds.
        fake_clock.set(disarm_a_dt)
        await manager.async_disarm(pair_a.id, source=ChangeSource.SCHEDULE_DISARM)
        await hass.async_block_till_done()
        standby_calls = [c for c in fake_mode_changer.calls if c["target"] == "standby"]
        assert len(standby_calls) == 1
        assert standby_calls[0]["pair_id"] == pair_a.id

        # Step 4: Panel transitions armed_home→disarmed with self-driven context.
        # B's pending disarm handle must NOT be cancelled.
        manager._start_panel_listener()
        ctx = Context(id=f"{CONTEXT_ID_PREFIX}{pair_a.id}_abc12345")
        _set_panel(hass, "disarmed", context=ctx)
        await hass.async_block_till_done(wait_background_tasks=True)
        # KEY correctness point: B's disarm handle is still present.
        assert (pair_b.id, "disarm") in manager._pending_handles

        # Step 5: At 08:00, B's disarm fires (simulated). Panel is disarmed.
        # async_disarm checks panel state: disarmed → MANUAL_OVERRIDE skip.
        skipped2 = _capture_events(hass, EVENT_SCHEDULE_SKIPPED)
        fake_clock.set(disarm_b_dt)
        await manager.async_disarm(pair_b.id, source=ChangeSource.SCHEDULE_DISARM)
        await hass.async_block_till_done()

        assert any(e["reason"] == SkipReason.MANUAL_OVERRIDE for e in skipped2)
        standby_calls2 = [
            c for c in fake_mode_changer.calls if c["target"] == "standby"
        ]
        assert len(standby_calls2) == 1  # still only A's disarm, B was skipped


# ---------------------------------------------------------------------------
# Sub-Phase D: Restart reconciliation
# ---------------------------------------------------------------------------


class TestReconciliation:
    async def _armed_pair(
        self,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        arm_dt: datetime,
    ):
        """Helper: create a pair and manually set last_armed_at (simulating pre-restart arm)."""
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        pair.last_armed_at = arm_dt
        await manager._store.async_update(pair)
        return pair

    async def test_reconcile_in_window_still_home(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Pair armed yesterday 22:00; restart at 23:30; panel home → disarm re-scheduled."""
        arm_dt = datetime(2030, 1, 7, 22, 0, 0, tzinfo=UTC)
        restart_dt = datetime(2030, 1, 7, 23, 30, 0, tzinfo=UTC)
        fake_clock.set(restart_dt)
        _set_panel(hass, "armed_home")

        pair = await self._armed_pair(manager, fake_clock, arm_dt)
        await manager.async_reconcile_on_startup()

        # Disarm handle registered.
        assert (pair.id, "disarm") in manager._pending_handles

        # Fire time to 06:00.
        disarm_dt = datetime(2030, 1, 8, 6, 0, 0, tzinfo=UTC)
        fake_clock.set(disarm_dt)
        async_fire_time_changed(hass, disarm_dt, fire_all=True)
        await hass.async_block_till_done(wait_background_tasks=True)

        standby_calls = [c for c in fake_mode_changer.calls if c["target"] == "standby"]
        assert len(standby_calls) == 1

    async def test_reconcile_in_window_panel_not_home(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Pair armed before restart; restart with panel armed_away → mark disarmed, no timer."""
        arm_dt = datetime(2030, 1, 7, 22, 0, 0, tzinfo=UTC)
        restart_dt = datetime(2030, 1, 7, 23, 30, 0, tzinfo=UTC)
        fake_clock.set(restart_dt)
        _set_panel(hass, "armed_away")

        pair = await self._armed_pair(manager, fake_clock, arm_dt)
        await manager.async_reconcile_on_startup()

        assert (pair.id, "disarm") not in manager._pending_handles
        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        assert refreshed.last_skip_reason == SkipReason.RECONCILE_PANEL_NOT_HOME
        assert refreshed.last_disarmed_at is not None

        # No disarm call.
        async_fire_time_changed(
            hass, datetime(2030, 1, 8, 6, 0, 0, tzinfo=UTC), fire_all=True
        )
        await hass.async_block_till_done(wait_background_tasks=True)
        assert len(fake_mode_changer.calls) == 0

    async def test_reconcile_out_of_window(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Pair armed 2 days ago; window elapsed → mark disarmed, no timer."""
        arm_dt = datetime(2030, 1, 5, 22, 0, 0, tzinfo=UTC)  # 2 days ago
        now = datetime(2030, 1, 7, 12, 0, 0, tzinfo=UTC)
        fake_clock.set(now)

        pair = await self._armed_pair(manager, fake_clock, arm_dt)
        # First call with no panel: deferred.
        await manager.async_reconcile_on_startup()
        # Second call: `_reconcile_deferred` is set, so the body runs:
        # out-of-window check doesn't need panel, proceeds immediately.
        await manager.async_reconcile_on_startup()

        assert (pair.id, "disarm") not in manager._pending_handles
        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        assert refreshed.last_skip_reason == SkipReason.RECONCILE_WINDOW_ELAPSED

    async def test_reconcile_missed_arm_no_catchup(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Pair with last_armed_at=None at restart → no reconciliation fires."""
        fake_clock.set(datetime(2030, 1, 7, 22, 30, 0, tzinfo=UTC))

        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        # last_armed_at is None; reconcile should be a no-op.
        await manager.async_reconcile_on_startup()

        assert (pair.id, "disarm") not in manager._pending_handles
        assert len(fake_mode_changer.calls) == 0

    async def test_reconcile_after_ha_start_with_no_panel_is_conservative(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """A panel that never appears must still leave the pair reconciled.

        Drives the real deferral rather than calling the method twice by hand:
        an account with no alarm device — or the `alarm is None` path in
        `alarm_control_panel.async_setup_entry` — reaches HA start with nothing
        to reconcile against, and reconciliation has to run anyway and mark the
        pair conservatively.  Skipping it would leave `last_armed_at` ahead of
        `last_disarmed_at` forever, so `derive_state` reports ARMED for a pair
        nothing will ever disarm — the same shape as the bug this commit fixes.
        """
        arm_dt = datetime(2030, 1, 7, 22, 0, 0, tzinfo=UTC)
        restart_dt = datetime(2030, 1, 7, 23, 30, 0, tzinfo=UTC)
        fake_clock.set(restart_dt)
        hass.set_state(CoreState.starting)

        pair = await self._armed_pair(manager, fake_clock, arm_dt)
        await manager.async_reconcile_on_startup()  # no panel — defers

        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        assert refreshed.last_skip_reason is None  # not yet reconciled

        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)  # panel STILL absent
        await hass.async_block_till_done(wait_background_tasks=True)

        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        assert refreshed.last_skip_reason == SkipReason.RECONCILE_PANEL_NOT_HOME

    def test_panel_wait_timeout_floors_ha_platform_ceiling(self) -> None:
        """The backstop must not undershoot how long HA lets platforms take.

        Pinned against HA's own constant rather than a literal, because the
        number is not arbitrary: platforms normally forward in milliseconds, but
        HA permits up to `SLOW_SETUP_MAX_WAIT`.  Tripping before that turns a
        merely slow forward into reconcile stamping `last_disarmed_at` against a
        panel that was on its way — dropping the pair out of ARMED with nothing
        able to re-run it, which is this issue's own symptom.

        `>=`, not `==`: HA raising its ceiling is what must fail here; HA
        lowering it is harmless, and overshooting costs nothing on the
        panel-less accounts this backstop exists for.
        """
        from homeassistant.setup import SLOW_SETUP_MAX_WAIT

        assert PANEL_WAIT_TIMEOUT >= SLOW_SETUP_MAX_WAIT

    async def test_reconcile_after_reload_with_no_panel_is_conservative(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """The reload branch needs the same panel-never-arrives escape.

        Waiting on the entity is right until the entity is never coming — an
        account with no alarm device reaches this on every reload, and waiting
        forever means the pair never leaves ARMED.  A backstop timer runs the
        conservative pass instead.
        """
        arm_dt = datetime(2030, 1, 7, 22, 0, 0, tzinfo=UTC)
        reload_dt = datetime(2030, 1, 7, 23, 30, 0, tzinfo=UTC)
        fake_clock.set(reload_dt)
        hass.set_state(CoreState.running)

        pair = await self._armed_pair(manager, fake_clock, arm_dt)
        # Anchored BEFORE the deferral arms its timer, so the near-edge fire
        # below is unconditionally earlier than the timer's due instant however
        # long the awaits in between take.  Reading the anchor afterwards left
        # about half a second of real wall clock before the "not yet" assertion
        # started firing the timer for real — a flake pointing at reconcile.
        armed_at = dt_util.utcnow()
        await manager.async_reconcile_on_startup()  # no panel — defers

        assert PANEL_WAIT_RECONCILE in manager._panel_wait_handles
        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        assert refreshed.last_skip_reason is None  # still waiting

        # Not yet: the backstop is real wall-clock, so it must not trip early.
        # (No `fire_all` — that would fire every timer regardless of its due
        # time and leave PANEL_WAIT_TIMEOUT's value unpinned.)
        async_fire_time_changed(
            hass, armed_at + timedelta(seconds=PANEL_WAIT_TIMEOUT - 1)
        )
        await hass.async_block_till_done(wait_background_tasks=True)
        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        assert refreshed.last_skip_reason is None

        # The panel never arrives; the backstop fires.
        async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(seconds=PANEL_WAIT_TIMEOUT + 1)
        )
        await hass.async_block_till_done(wait_background_tasks=True)

        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        assert refreshed.last_skip_reason == SkipReason.RECONCILE_PANEL_NOT_HOME
        assert PANEL_WAIT_RECONCILE not in manager._panel_wait_handles

    async def test_reconcile_survives_a_reload_mid_window(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """#216: the reconcile deferral has the same reload trap as the listener.

        This is the worse half of the pair.  `_register_all_timers` only
        restores the daily *arm* callback, so reconciliation is the only thing
        that rebuilds a one-shot disarm — waiting on an
        EVENT_HOMEASSISTANT_STARTED that has already fired left a mid-window
        reload with the panel armed and nothing scheduled to disarm it.
        """
        arm_dt = datetime(2030, 1, 7, 22, 0, 0, tzinfo=UTC)
        reload_dt = datetime(2030, 1, 7, 23, 30, 0, tzinfo=UTC)
        fake_clock.set(reload_dt)
        hass.set_state(CoreState.running)  # a reload, not a boot

        pair = await self._armed_pair(manager, fake_clock, arm_dt)
        await manager.async_reconcile_on_startup()  # no panel yet — defers

        assert PANEL_WAIT_RECONCILE in manager._panel_wait_handles
        assert (pair.id, "disarm") not in manager._pending_handles

        # HA start will not fire again; the panel appearing is the real signal.
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done(wait_background_tasks=True)
        assert (pair.id, "disarm") not in manager._pending_handles

        _set_panel(hass, "armed_home")
        await hass.async_block_till_done(wait_background_tasks=True)

        assert (pair.id, "disarm") in manager._pending_handles
        assert PANEL_WAIT_RECONCILE not in manager._panel_wait_handles

        # And it really disarms at the boundary.
        disarm_dt = await _expected_disarm(manager, pair.id) + timedelta(seconds=2)
        fake_clock.set(disarm_dt)
        async_fire_time_changed(hass, disarm_dt, fire_all=True)
        await hass.async_block_till_done(wait_background_tasks=True)

        assert [c for c in fake_mode_changer.calls if c["target"] == "standby"]

    async def test_reconcile_deferred_when_panel_unavailable_at_setup(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """If panel is None at first reconcile, defer to EVENT_HOMEASSISTANT_STARTED.

        When the event fires with the panel now available (armed_home), the
        deferred reconciliation re-registers the disarm timer.
        """
        arm_dt = datetime(2030, 1, 7, 22, 0, 0, tzinfo=UTC)
        restart_dt = datetime(2030, 1, 7, 23, 30, 0, tzinfo=UTC)
        fake_clock.set(restart_dt)
        # No panel at first call → deferred.  This is the *startup* branch;
        # past startup the deferral waits on the entity instead (see
        # test_reconcile_survives_a_reload_mid_window).
        hass.set_state(CoreState.starting)

        pair = await self._armed_pair(manager, fake_clock, arm_dt)
        await manager.async_reconcile_on_startup()

        # First call deferred; pair not yet touched.
        assert (pair.id, "disarm") not in manager._pending_handles
        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        assert refreshed.last_skip_reason is None  # not yet reconciled

        # Panel becomes available; fire EVENT_HOMEASSISTANT_STARTED.
        _set_panel(hass, "armed_home")
        hass.bus.async_fire("homeassistant_started")
        await hass.async_block_till_done(wait_background_tasks=True)

        # After event, reconciliation ran and re-registered the disarm timer.
        assert (pair.id, "disarm") in manager._pending_handles

    async def test_reconcile_only_defers_once(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """The `_reconcile_deferred` guard, driven directly.

        Production reaches the second pass through the deferral rather than by
        calling twice (see `test_reconcile_after_ha_start_with_no_panel_is_
        conservative` and its reload sibling); this one exercises the guard and
        the panel-less body on their own, so pin the branch explicitly rather
        than inheriting whatever CoreState the harness defaults to.
        """
        hass.set_state(CoreState.starting)
        arm_dt = datetime(2030, 1, 7, 22, 0, 0, tzinfo=UTC)
        restart_dt = datetime(2030, 1, 7, 23, 30, 0, tzinfo=UTC)
        fake_clock.set(restart_dt)

        pair = await self._armed_pair(manager, fake_clock, arm_dt)
        # First call: deferred.
        await manager.async_reconcile_on_startup()
        # Second call: the guard is already set, so this runs the body.
        await manager.async_reconcile_on_startup()

        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        assert refreshed.last_skip_reason == SkipReason.RECONCILE_PANEL_NOT_HOME


# ---------------------------------------------------------------------------
# Sub-Phase E: Manual-override listener
# ---------------------------------------------------------------------------


class TestManualOverrideListener:
    async def test_manual_disarm_cancels_pending_disarm(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """User manually disarms while pair is ARMED → disarm timer cancelled."""
        _set_panel(hass, "disarmed")
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )

        # Arm the pair.
        await manager.async_arm(pair.id)
        _set_panel(hass, "armed_home")
        assert (pair.id, "disarm") in manager._pending_handles

        # Start the panel listener.
        manager._start_panel_listener()

        skipped = _capture_events(hass, EVENT_SCHEDULE_SKIPPED)

        # User manually disarms (non-schedule context).
        _set_panel(hass, "disarmed")
        await hass.async_block_till_done(wait_background_tasks=True)

        assert (pair.id, "disarm") not in manager._pending_handles
        await hass.async_block_till_done()
        assert any(e["reason"] == SkipReason.MANUAL_OVERRIDE for e in skipped)

    async def test_manual_to_away_cancels_pending_disarm(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Panel goes to armed_away → disarm timer cancelled."""
        _set_panel(hass, "disarmed")
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        await manager.async_arm(pair.id)
        _set_panel(hass, "armed_home")
        manager._start_panel_listener()

        _set_panel(hass, "armed_away")
        await hass.async_block_till_done(wait_background_tasks=True)

        assert (pair.id, "disarm") not in manager._pending_handles

    async def test_self_driven_change_not_treated_as_override(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Manager's own disarm (context.id starts with abode_sched_) is ignored."""
        _set_panel(hass, "disarmed")
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        await manager.async_arm(pair.id)
        _set_panel(hass, "armed_home")
        manager._start_panel_listener()

        # Simulate manager's own transition.
        ctx = Context(id=f"{CONTEXT_ID_PREFIX}{pair.id}_deadbeef")
        _set_panel(hass, "disarmed", context=ctx)
        await hass.async_block_till_done(wait_background_tasks=True)

        # Handle should still be present (listener ignored the event).
        assert (pair.id, "disarm") in manager._pending_handles

    async def test_no_armed_pairs_listener_noop(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
    ) -> None:
        """Panel disarms when no pairs are ARMED — no errors, no events."""
        _set_panel(hass, "armed_home")
        manager._start_panel_listener()
        skipped = _capture_events(hass, EVENT_SCHEDULE_SKIPPED)

        _set_panel(hass, "disarmed")
        await hass.async_block_till_done(wait_background_tasks=True)
        await hass.async_block_till_done()

        assert len(skipped) == 0

    # -- #216: availability blips are not manual overrides -------------------

    async def _armed_with_pending_disarm(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
    ) -> ScheduledPair:
        """Arm a pair, leave the panel Home, and start the override listener."""
        _set_panel(hass, "disarmed")
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        await manager.async_arm(pair.id)
        _set_panel(hass, "armed_home")
        assert (pair.id, "disarm") in manager._pending_handles
        manager._start_panel_listener()
        return pair

    @pytest.mark.parametrize("blip", ["unavailable", "unknown"])
    async def test_availability_blip_keeps_pending_disarm(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
        blip: str,
    ) -> None:
        """#216: a cloud dropout inside the window must not cancel the disarm.

        A SocketIO reconnect flips the panel armed_home → unavailable → armed_home
        in a couple of minutes.  HA mints a fresh context when it marks an entity
        unavailable, so the CONTEXT_ID_PREFIX check cannot filter it out — the
        listener has to recognise unavailability itself.
        """
        pair = await self._armed_with_pending_disarm(hass, manager)
        before = await manager.async_get(pair.id)
        assert before is not None
        skipped = _capture_events(hass, EVENT_SCHEDULE_SKIPPED)

        _set_panel(hass, blip)
        await hass.async_block_till_done(wait_background_tasks=True)
        _set_panel(hass, "armed_home")
        await hass.async_block_till_done(wait_background_tasks=True)
        await hass.async_block_till_done()

        assert (pair.id, "disarm") in manager._pending_handles
        assert len(skipped) == 0
        after = await manager.async_get(pair.id)
        assert after is not None
        assert after.last_disarmed_at == before.last_disarmed_at
        assert after.last_skip_reason == before.last_skip_reason

        # …and the original disarm still fires at its own boundary.
        fired = _capture_events(hass, EVENT_SCHEDULE_FIRED)
        disarm_dt = await _expected_disarm(manager, pair.id) + timedelta(seconds=2)
        fake_clock.set(disarm_dt)
        async_fire_time_changed(hass, disarm_dt, fire_all=True)
        await hass.async_block_till_done(wait_background_tasks=True)

        assert [c for c in fake_mode_changer.calls if c["target"] == "standby"]
        assert any(e["action"] == "disarm" for e in fired)

    async def test_change_made_while_unavailable_is_still_an_override(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Panel recovers as disarmed → the user really did leave Home."""
        pair = await self._armed_with_pending_disarm(hass, manager)
        skipped = _capture_events(hass, EVENT_SCHEDULE_SKIPPED)

        _set_panel(hass, "unavailable")
        await hass.async_block_till_done(wait_background_tasks=True)
        # The dropout itself is a non-event — asserted here so this test fails
        # on the #216 bug rather than passing on it: the old code cancelled the
        # handle on THIS edge, reaching the same end state for the wrong reason.
        assert (pair.id, "disarm") in manager._pending_handles
        assert len(skipped) == 0

        _set_panel(hass, "disarmed")
        await hass.async_block_till_done(wait_background_tasks=True)
        await hass.async_block_till_done()

        assert (pair.id, "disarm") not in manager._pending_handles
        assert any(e["reason"] == SkipReason.MANUAL_OVERRIDE for e in skipped)

    async def test_recovering_as_away_is_still_an_override(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Panel recovers as armed_away → still counts as leaving Home."""
        pair = await self._armed_with_pending_disarm(hass, manager)
        skipped = _capture_events(hass, EVENT_SCHEDULE_SKIPPED)

        _set_panel(hass, "unavailable")
        await hass.async_block_till_done(wait_background_tasks=True)
        # Same reason as the disarmed case above: pin the intermediate edge.
        assert (pair.id, "disarm") in manager._pending_handles
        assert len(skipped) == 0

        _set_panel(hass, "armed_away")
        await hass.async_block_till_done(wait_background_tasks=True)
        await hass.async_block_till_done()

        assert (pair.id, "disarm") not in manager._pending_handles
        assert any(e["reason"] == SkipReason.MANUAL_OVERRIDE for e in skipped)

    async def test_self_driven_disarm_does_not_arm_a_later_override(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """The remembered mode tracks our own transitions too.

        The listener compares against the last mode the panel was known to be in
        rather than the event's ``old_state``, so a self-driven armed_home →
        disarmed must still move that memory off armed_home — otherwise the next
        genuine change would be misread as leaving Home.
        """
        pair = await self._armed_with_pending_disarm(hass, manager)
        skipped = _capture_events(hass, EVENT_SCHEDULE_SKIPPED)

        ctx = Context(id=f"{CONTEXT_ID_PREFIX}{pair.id}_deadbeef")
        _set_panel(hass, "disarmed", context=ctx)
        await hass.async_block_till_done(wait_background_tasks=True)
        assert (pair.id, "disarm") in manager._pending_handles

        # A later user-driven change out of `disarmed` is not a leave-Home edge.
        _set_panel(hass, "armed_away")
        await hass.async_block_till_done(wait_background_tasks=True)
        await hass.async_block_till_done()

        assert (pair.id, "disarm") in manager._pending_handles
        assert len(skipped) == 0

    async def test_unavailable_across_disarm_time_skips(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Pins the landing when the panel is *still* out at disarm_time.

        The listener fix keeps the timer alive across a blip, but a dropout that
        outlasts the window still lands in `_disarm_impl`'s conservative
        panel_unavailable branch: the pair leaves ARMED and nothing re-attempts
        the disarm when the panel returns.  Re-adopting the panel on recovery is
        #212's job; this test exists so that change is a deliberate one.
        """
        pair = await self._armed_with_pending_disarm(hass, manager)
        skipped = _capture_events(hass, EVENT_SCHEDULE_SKIPPED)

        _set_panel(hass, "unavailable")
        await hass.async_block_till_done(wait_background_tasks=True)
        assert (pair.id, "disarm") in manager._pending_handles

        disarm_dt = await _expected_disarm(manager, pair.id) + timedelta(seconds=2)
        fake_clock.set(disarm_dt)
        async_fire_time_changed(hass, disarm_dt, fire_all=True)
        await hass.async_block_till_done(wait_background_tasks=True)

        assert not [c for c in fake_mode_changer.calls if c["target"] == "standby"]
        assert any(e["reason"] == SkipReason.PANEL_UNAVAILABLE for e in skipped)

        # Recovering afterwards does not re-attempt: the pair is out of ARMED.
        _set_panel(hass, "armed_home")
        await hass.async_block_till_done(wait_background_tasks=True)
        assert not [c for c in fake_mode_changer.calls if c["target"] == "standby"]

    # -- #216: the deferral has to survive a config-entry reload -------------

    async def test_reload_waits_for_the_panel_entity_not_ha_start(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
    ) -> None:
        """#216: past startup, EVENT_HOMEASSISTANT_STARTED never fires again.

        `async_setup` runs before `async_forward_entry_setups`, so the panel
        entity is never in `hass.states` yet and the deferral is taken on every
        setup.  Deferring to EVENT_HOMEASSISTANT_STARTED is fine on first boot,
        but that event is once-per-process: after a reload the manager waited on
        something that would never come and the override listener stayed dead
        until the next restart.
        """
        hass.set_state(CoreState.running)  # i.e. a reload, not first boot
        manager._start_panel_listener()

        # Deferred on the entity, not on HA start.
        assert manager._listener_handle is None
        assert PANEL_WAIT_LISTENER in manager._panel_wait_handles

        # Firing HA start again changes nothing — it is not what we waited on.
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()
        assert manager._listener_handle is None

        # The panel arriving is.
        _set_panel(hass, "armed_home")
        await hass.async_block_till_done()

        assert manager._listener_handle is not None
        assert PANEL_WAIT_LISTENER not in manager._panel_wait_handles
        assert manager._last_panel_state == "armed_home"

    async def test_listener_registered_after_reload_still_sees_overrides(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """End to end: the reload-registered listener does its actual job."""
        hass.set_state(CoreState.running)
        manager._start_panel_listener()  # defers on the entity
        _set_panel(hass, "disarmed")  # panel appears — listener registers
        await hass.async_block_till_done()
        assert manager._listener_handle is not None

        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        await manager.async_arm(pair.id)
        _set_panel(hass, "armed_home")
        await hass.async_block_till_done(wait_background_tasks=True)
        assert (pair.id, "disarm") in manager._pending_handles

        skipped = _capture_events(hass, EVENT_SCHEDULE_SKIPPED)
        _set_panel(hass, "disarmed")
        await hass.async_block_till_done(wait_background_tasks=True)
        await hass.async_block_till_done()

        assert (pair.id, "disarm") not in manager._pending_handles
        assert any(e["reason"] == SkipReason.MANUAL_OVERRIDE for e in skipped)

    async def test_foreign_alarm_panel_does_not_register_the_listener(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
    ) -> None:
        """Another integration's alarm_control_panel is not ours to watch.

        Asserted on the *identity* of the outstanding subscription, not merely
        on one being present: without the `_panel_entity_id()` guard a foreign
        panel re-enters `_start_panel_listener`, finds nothing, and defers
        again — reaching an observably identical state via a fresh handle.
        """
        hass.set_state(CoreState.running)
        manager._start_panel_listener()
        waiting_on = manager._panel_wait_handles[PANEL_WAIT_LISTENER]

        hass.states.async_set("alarm_control_panel.someone_elses", "disarmed")
        await hass.async_block_till_done()

        assert manager._listener_handle is None
        assert manager._panel_wait_handles.get(PANEL_WAIT_LISTENER) is waiting_on

        _set_panel(hass, "disarmed")
        await hass.async_block_till_done()
        assert manager._listener_handle is not None

    async def test_full_setup_arms_both_deferrals_and_both_fire(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """The production shape: `async_setup` arms both waits back to back.

        Every other test drives one deferral at a time, but `async_setup`
        registers the listener and the reconcile wait against the same domain.
        Correctness then leans on HA copying its listener list before dispatch,
        so that the first callback cancelling its own subscription mid-dispatch
        does not stop the second from running.  Pin both firing from one arrival.
        """
        arm_dt = datetime(2030, 1, 7, 22, 0, 0, tzinfo=UTC)
        reload_dt = datetime(2030, 1, 7, 23, 30, 0, tzinfo=UTC)
        fake_clock.set(reload_dt)
        hass.set_state(CoreState.running)

        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        pair.last_armed_at = arm_dt  # armed before the reload
        await manager._store.async_update(pair)

        await manager.async_setup()  # no panel yet — both defer

        assert PANEL_WAIT_LISTENER in manager._panel_wait_handles
        assert PANEL_WAIT_RECONCILE in manager._panel_wait_handles
        assert manager._listener_handle is None
        assert (pair.id, "disarm") not in manager._pending_handles

        _set_panel(hass, "armed_home")
        await hass.async_block_till_done(wait_background_tasks=True)

        # Listener registered *and* the disarm timer reconciled back.
        assert manager._listener_handle is not None
        assert manager._last_panel_state == "armed_home"
        assert (pair.id, "disarm") in manager._pending_handles
        assert manager._panel_wait_handles == {}

    async def test_listener_keeps_waiting_when_panel_absent_at_ha_start(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """A miss on the startup one-shot hands off, it does not give up.

        EVENT_HOMEASSISTANT_STARTED does not come round again, so stopping here
        would leave the manual-override listener dead until the next restart.
        The entity subscription is not tied to startup, so the two branches can
        converge on it rather than behaving differently.
        """
        hass.set_state(CoreState.starting)
        manager._start_panel_listener()  # no panel — defers on HA start
        assert manager._panel_wait_handles == {}  # a one-shot, not a subscription

        caplog.clear()
        # Realism, not a precondition: HA does set `running` just before firing
        # this, but the hand-off never consults `hass.state`.
        hass.set_state(CoreState.running)
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)  # panel still absent
        await hass.async_block_till_done()

        # Handed off, and quiet until the backstop — not warned-and-done.
        assert manager._listener_handle is None
        assert PANEL_WAIT_LISTENER in manager._panel_wait_handles
        assert "Abode panel entity not found" not in caplog.text

        # A panel that arrives after HA start is still adopted.
        _set_panel(hass, "armed_home")
        await hass.async_block_till_done()
        assert manager._listener_handle is not None
        assert manager._last_panel_state == "armed_home"
        assert manager._panel_wait_handles == {}

    async def test_listener_warns_after_ha_start_when_panel_never_arrives(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """The hand-off moves the warning to the backstop, it does not drop it.

        A silently disabled manual-override listener on a security integration
        is the wrong kind of quiet, so the account-with-no-alarm-device case
        still says so — just PANEL_WAIT_TIMEOUT later than it used to.
        """
        hass.set_state(CoreState.starting)
        manager._start_panel_listener()
        hass.set_state(CoreState.running)
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)  # panel still absent
        await hass.async_block_till_done()

        caplog.clear()
        async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(seconds=PANEL_WAIT_TIMEOUT + 1)
        )
        await hass.async_block_till_done()

        assert "Abode panel entity not found" in caplog.text
        assert manager._listener_handle is None
        assert PANEL_WAIT_LISTENER in manager._panel_wait_handles  # still waiting

        # Structurally implied by the line above, but "the warning does not
        # consume the subscription" is the property the hand-off turns on, so
        # assert it behaviourally too — as the running-branch twin does.
        _set_panel(hass, "armed_home")
        await hass.async_block_till_done()
        assert manager._listener_handle is not None

    async def test_listener_warns_but_keeps_waiting_when_panel_never_arrives(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """The listener has nothing to do without a panel, so it does not proceed.

        It still says so once — a silently disabled manual-override listener on
        a security integration is the wrong kind of quiet — but the
        subscription survives the warning, so a panel that shows up late is
        still picked up.
        """
        hass.set_state(CoreState.running)
        armed_at = dt_util.utcnow()  # before arming — see the reconcile twin
        manager._start_panel_listener()
        assert PANEL_WAIT_LISTENER in manager._panel_wait_handles

        caplog.clear()
        # Not due yet — pins the constant, which `fire_all` would ignore.
        async_fire_time_changed(
            hass, armed_at + timedelta(seconds=PANEL_WAIT_TIMEOUT - 1)
        )
        await hass.async_block_till_done()
        assert "Abode panel entity not found" not in caplog.text

        async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(seconds=PANEL_WAIT_TIMEOUT + 1)
        )
        await hass.async_block_till_done()

        assert "Abode panel entity not found" in caplog.text
        assert manager._listener_handle is None
        assert PANEL_WAIT_LISTENER in manager._panel_wait_handles  # still waiting

        # A late panel is still adopted.
        _set_panel(hass, "armed_home")
        await hass.async_block_till_done()
        assert manager._listener_handle is not None
        assert manager._last_panel_state == "armed_home"

    async def test_deferring_twice_does_not_leak_a_subscription(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
    ) -> None:
        """A second deferral must not orphan the first subscription.

        `_start_panel_listener`'s own guard only checks `_listener_handle`,
        which is still None while deferred — so without the per-key check a
        second call would overwrite the stored handle and leave the first
        subscription live, holding a torn-down manager for the life of the
        process.  Asserted on identity: a leak is invisible in the key set.
        """
        hass.set_state(CoreState.running)
        manager._start_panel_listener()
        first = manager._panel_wait_handles[PANEL_WAIT_LISTENER]

        manager._start_panel_listener()

        assert manager._panel_wait_handles[PANEL_WAIT_LISTENER] is first
        assert len(manager._panel_wait_handles) == 1

        # And the one that survives is the one shutdown can reach.
        await manager.async_shutdown()
        _set_panel(hass, "disarmed")
        await hass.async_block_till_done()
        assert manager._listener_handle is None

    async def test_shutdown_cancels_the_pending_entity_subscription(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
    ) -> None:
        """The reload deferral is a real subscription, so teardown must drop it.

        Unlike the EVENT_HOMEASSISTANT_STARTED one-shot — which the `_shutdown`
        flag neutralises — this one would otherwise keep a torn-down manager
        subscribed to every alarm_control_panel that appears afterwards.
        """
        hass.set_state(CoreState.running)
        manager._start_panel_listener()
        assert PANEL_WAIT_LISTENER in manager._panel_wait_handles

        await manager.async_shutdown()
        assert manager._panel_wait_handles == {}

        _set_panel(hass, "disarmed")
        await hass.async_block_till_done()
        assert manager._listener_handle is None


# ---------------------------------------------------------------------------
# Sub-Phase F: Event payload shapes and diagnostics
# ---------------------------------------------------------------------------


class TestEventPayloads:
    async def test_schedule_fired_payload_shape(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """schedule_fired event has all required keys."""
        _set_panel(hass, "disarmed")
        fired = _capture_events(hass, EVENT_SCHEDULE_FIRED)
        pair = await manager.async_create(
            name="Test", weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        await manager.async_arm(pair.id)
        await hass.async_block_till_done()

        assert len(fired) == 1
        ev = fired[0]
        for key in (
            "schedule_id",
            "schedule_name",
            "action",
            "target_mode",
            "fired_at",
        ):
            assert key in ev, f"missing key: {key}"
        assert ev["action"] == "arm"
        assert ev["target_mode"] == "home"

    async def test_schedule_skipped_payload_shape(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """schedule_skipped event has all required keys."""
        _set_panel(hass, "armed_away")
        skipped = _capture_events(hass, EVENT_SCHEDULE_SKIPPED)
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        await manager.async_arm(pair.id)
        await hass.async_block_till_done()

        assert len(skipped) == 1
        ev = skipped[0]
        for key in ("schedule_id", "schedule_name", "action", "reason", "skipped_at"):
            assert key in ev, f"missing key: {key}"

    async def test_schedule_failed_payload_shape(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """schedule_failed event has all required keys."""
        _set_panel(hass, "disarmed")
        failed = _capture_events(hass, EVENT_SCHEDULE_FAILED)

        fake_mode_changer.set_fail_count(999)
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        with _no_retry_sleeps():
            await manager.async_arm(pair.id)
        await hass.async_block_till_done()

        assert len(failed) == 1
        ev = failed[0]
        for key in (
            "schedule_id",
            "schedule_name",
            "action",
            "error",
            "attempts",
            "failed_at",
        ):
            assert key in ev, f"missing key: {key}"
        assert ev["attempts"] == SCHEDULE_RETRY_TOTAL_ATTEMPTS


class TestIdempotency:
    async def test_async_disarm_twice_produces_one_panel_change(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Second call to async_disarm on same pair is a no-op (pair in IDLE)."""
        _set_panel(hass, "disarmed")
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        await manager.async_arm(pair.id)
        _set_panel(hass, "armed_home")

        await manager.async_disarm(pair.id)
        await manager.async_disarm(pair.id)  # second call

        standby_calls = [c for c in fake_mode_changer.calls if c["target"] == "standby"]
        assert len(standby_calls) == 1


class _Unretryable(BaseException):
    """Raised past ``async_retry``'s ``catch=Exception``.

    A ``BaseException`` rather than ``KeyboardInterrupt`` so pytest treats it as
    a normal test failure signal instead of aborting the whole run.
    """


class TestShutdown:
    """#201 — teardown must not leave arm/disarm work running.

    State confirmation (#192) keeps an arm or disarm alive for up to ~111 s, so a
    config-entry unload lands mid-flight as the normal case, not an edge one.
    Whatever is still in flight has to be cancelled and awaited, or its store
    write, event, and repair issue outlive the manager that was torn down.
    """

    async def test_shutdown_cancels_in_flight_arm(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """An arm still in flight at shutdown writes nothing afterwards."""
        _set_panel(hass, "disarmed")
        fired = _capture_events(hass, EVENT_SCHEDULE_FIRED)
        failed = _capture_events(hass, EVENT_SCHEDULE_FAILED)

        release = fake_mode_changer.block()

        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        task = hass.async_create_task(manager.async_arm(pair.id))
        await fake_mode_changer.started.wait()

        await manager.async_shutdown()

        # Release what shutdown cancelled.  Without cancellation the arm resumes
        # here and completes against a torn-down manager.
        release.set()
        await hass.async_block_till_done()

        assert task.cancelled()
        assert fired == []
        assert failed == []
        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        assert refreshed.last_armed_at is None
        # A resurrected disarm timer would outlive the manager holding it.
        assert manager._pending_handles == {}

    async def test_shutdown_awaits_the_tasks_it_cancels(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Shutdown must not return while cancelled work is still unwinding.

        Cancelling without gathering passes every other test in this class —
        they all let the loop run before asserting — so this pins the gather
        directly: the task is finished the instant shutdown returns.
        """
        _set_panel(hass, "disarmed")
        fake_mode_changer.block()

        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        task = hass.async_create_task(manager.async_arm(pair.id))
        await fake_mode_changer.started.wait()

        inflight = list(manager._inflight)
        assert len(inflight) == 1

        await manager.async_shutdown()

        assert inflight[0].done()
        await hass.async_block_till_done()
        assert task.cancelled()

    async def test_shutdown_cancels_in_flight_disarm(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Same for the disarm edge, which reaches the manager via a timer."""
        _set_panel(hass, "disarmed")
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        await manager.async_arm(pair.id)
        _set_panel(hass, "armed_home")

        fired = _capture_events(hass, EVENT_SCHEDULE_FIRED)
        failed = _capture_events(hass, EVENT_SCHEDULE_FAILED)
        release = fake_mode_changer.block()

        task = hass.async_create_task(manager.async_disarm(pair.id))
        await fake_mode_changer.started.wait()

        await manager.async_shutdown()

        release.set()
        await hass.async_block_till_done()

        assert task.cancelled()
        assert fired == []
        assert failed == []
        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        assert refreshed.last_disarmed_at is None

    async def test_shutdown_cancels_in_flight_manual_override(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """The override handler writes the store too, so it is tracked as well.

        Its window is far shorter than an arm's — one store write, no retries —
        but it is the same class of late write, and it is the only other
        coroutine the manager spawns on its own.
        """
        _set_panel(hass, "disarmed")
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        await manager.async_arm(pair.id)
        _set_panel(hass, "armed_home")
        manager._start_panel_listener()

        skipped = _capture_events(hass, EVENT_SCHEDULE_SKIPPED)

        # A manual disarm from outside the integration (no schedule context).
        _set_panel(hass, "disarmed")
        await hass.async_block_till_done()
        assert len(skipped) == 1  # handler ran to completion while alive

        # Arm again, then tear down with the handler mid-flight.
        _set_panel(hass, "armed_home")
        await manager.async_arm(pair.id)
        skipped.clear()

        block = asyncio.Event()
        original_update = manager._store.async_update

        async def _blocking_update(updated: Any) -> None:
            await block.wait()
            await original_update(updated)

        manager._store.async_update = _blocking_update  # type: ignore[method-assign]

        _set_panel(hass, "disarmed")
        await asyncio.sleep(0)  # let the listener spawn the handler task

        await manager.async_shutdown()

        block.set()
        await hass.async_block_till_done()

        assert skipped == []

    async def test_deferred_listener_retry_does_not_resurrect_after_shutdown(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
    ) -> None:
        """The panel listener must not come back after teardown.

        `_start_panel_listener` defers to EVENT_HOMEASSISTANT_STARTED when the
        panel is not in `hass.states` yet — exactly the state an entry unloaded
        during startup is in.  Shutdown clears `_listener_handle`, so without
        the shutdown guard the retry would subscribe a dead manager with nothing
        left to unsubscribe it.
        """
        # The EVENT_HOMEASSISTANT_STARTED branch is the *startup* one; past
        # startup the deferral waits on the entity instead (see the reload
        # tests below), so say which branch this test is about.
        hass.set_state(CoreState.starting)
        manager._start_panel_listener()  # no panel yet — defers
        assert manager._listener_handle is None

        await manager.async_shutdown()

        _set_panel(hass, "disarmed")
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()

        assert manager._listener_handle is None
        assert manager._panel_wait_handles == {}

    async def test_startup_retry_arms_nothing_after_shutdown(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """End to end: an HA-start retry on a dead manager is inert.

        Unloading the entry removes the alarm_control_panel entity, so the
        retry's panel lookup fails and it takes the hand-off branch — which on
        a dead manager would mean a live state-added subscription plus a 300 s
        timer the sweep has already run past.  Asserted as behaviour rather
        than as a barrier: `_retry` holds no `_shutdown` check of its own, the
        refusal comes from `_wait_for_panel_entity`'s (pinned on its own by
        `test_panel_entity_wait_is_not_armed_after_shutdown`), and this test
        says the two compose.
        """
        hass.set_state(CoreState.starting)
        manager._start_panel_listener()  # no panel yet — defers
        await manager.async_shutdown()

        caplog.clear()
        hass.set_state(CoreState.running)
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)  # panel still absent
        await hass.async_block_till_done()

        assert manager._panel_wait_handles == {}
        assert "Abode panel entity not found" not in caplog.text

    async def test_shutdown_cancels_a_wait_armed_by_the_startup_hand_off(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
    ) -> None:
        """The hand-off is what brings a startup deferral within the sweep's reach.

        Armed as an EVENT_HOMEASSISTANT_STARTED one-shot, which `async_shutdown`
        cannot cancel and only the `_shutdown` flag neutralises — but once HA
        start fires with no panel it becomes a real subscription, and from then
        on teardown has to cancel it like any other.
        """
        hass.set_state(CoreState.starting)
        manager._start_panel_listener()  # no panel — defers on HA start
        hass.set_state(CoreState.running)
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)  # panel still absent
        await hass.async_block_till_done()
        assert PANEL_WAIT_LISTENER in manager._panel_wait_handles

        await manager.async_shutdown()

        assert manager._panel_wait_handles == {}
        _set_panel(hass, "armed_home")
        await hass.async_block_till_done()
        assert manager._listener_handle is None

    async def test_panel_entity_wait_is_not_armed_after_shutdown(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
    ) -> None:
        """`_wait_for_panel_entity` is self-guarded, not merely well-called.

        Both of its callers check `_shutdown` synchronously first, so this
        guard is defence rather than a live path — and defence that nothing
        exercises is defence that silently rots.  Called directly, because
        going through `_defer_until_panel_exists` stops at the outer guard and
        pins that one instead (see the test below).
        """
        hass.set_state(CoreState.running)
        ran = []

        await manager.async_shutdown()
        manager._wait_for_panel_entity(
            PANEL_WAIT_RECONCILE,
            lambda: ran.append(True),
            on_missing_panel=RUN_WITHOUT_PANEL,
        )

        assert manager._panel_wait_handles == {}

        _set_panel(hass, "armed_home")
        async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(seconds=PANEL_WAIT_TIMEOUT + 1)
        )
        await hass.async_block_till_done()
        assert ran == []

    async def test_panel_deferral_is_not_armed_after_shutdown(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
    ) -> None:
        """The sweep has already run, so anything armed past it is never cancelled.

        Reachable: `async_setup` awaits the store load before it defers, so a
        setup suspended across a teardown resumes straight into this guard.
        Without it the dead manager stays subscribed to every alarm panel added
        for the life of the process — the leak `async_shutdown` exists to avoid.

        The startup leg is why this guard cannot just be left to
        `_wait_for_panel_entity`'s: that branch parks a bus one-shot nothing
        cancels, so the reference is taken before `_retry` can re-check.
        """
        hass.set_state(CoreState.running)
        ran = []

        await manager.async_shutdown()
        manager._defer_until_panel_exists(
            PANEL_WAIT_RECONCILE,
            lambda: ran.append(True),
            on_missing_panel=RUN_WITHOUT_PANEL,
        )

        assert manager._panel_wait_handles == {}

        # Nothing is listening, so neither trigger can reach the action.
        _set_panel(hass, "armed_home")
        async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(seconds=PANEL_WAIT_TIMEOUT + 1)
        )
        await hass.async_block_till_done()
        assert ran == []

        # The startup branch leaks differently — a bus one-shot, not a
        # subscription — so it needs saying separately.
        before = hass.bus.async_listeners().get(EVENT_HOMEASSISTANT_STARTED, 0)
        hass.set_state(CoreState.starting)
        manager._defer_until_panel_exists(
            PANEL_WAIT_RECONCILE,
            lambda: ran.append(True),
            on_missing_panel=RUN_WITHOUT_PANEL,
        )
        assert hass.bus.async_listeners().get(EVENT_HOMEASSISTANT_STARTED, 0) == before

    async def test_timers_are_not_registered_after_shutdown(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
    ) -> None:
        """CRUD is not tracked work, so it needs the flag rather than the sweep.

        `async_shutdown` yields to the loop at its gather, and the manager is
        only popped from `hass.data` afterwards — so a WS create landing in that
        window would otherwise install a daily timer into a `_pending_handles`
        that will never be swept again.
        """
        _set_panel(hass, "disarmed")
        await manager.async_shutdown()

        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )

        assert manager._pending_handles == {}
        # The pair itself is still persisted — only the timer is refused.
        assert await manager.async_get(pair.id) is not None

    async def test_arm_after_shutdown_is_a_no_op(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """A timer that fired just before the sweep must not start new work.

        ``async_call_later``'s callback creates its task before the handle is
        cancelled, so the coroutine can reach the manager after
        ``async_shutdown`` has already swept.
        """
        _set_panel(hass, "disarmed")
        fired = _capture_events(hass, EVENT_SCHEDULE_FIRED)
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )

        await manager.async_shutdown()
        await manager.async_arm(pair.id)
        await hass.async_block_till_done()

        assert fake_mode_changer.attempts == 0
        assert fired == []
        assert manager._pending_handles == {}

    async def test_shutdown_is_idempotent(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
    ) -> None:
        """Unload runs it, and the manager fixture runs it again at teardown.

        Sequentially only — the docstring on `async_shutdown` is explicit that a
        concurrent second caller would find `_inflight` already drained.
        """
        _set_panel(hass, "disarmed")
        await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        manager._start_panel_listener()
        assert manager._pending_handles != {}
        assert manager._listener_handle is not None

        await manager.async_shutdown()
        await manager.async_shutdown()

        # The second call is a genuine no-op, not merely non-raising.
        assert manager._pending_handles == {}
        assert manager._listener_handle is None
        assert manager._panel_wait_handles == {}
        assert manager._last_panel_state is None
        assert manager._inflight == set()

    async def test_shutdown_logs_a_task_that_fails_while_unwinding(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """A genuine failure during teardown must not vanish into the gather.

        `return_exceptions=True` is required so the CancelledErrors don't cancel
        the caller unloading the entry — but it also *retrieves* real
        exceptions, which used to reach asyncio's "task exception was never
        retrieved" handler instead.  A reload is exactly when someone is reading
        the log, so shutdown surfaces them itself.
        """
        started = asyncio.Event()

        async def _fails_while_unwinding() -> None:
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                raise RuntimeError("store write failed while unwinding") from None

        manager._track(_fails_while_unwinding())
        await started.wait()

        caplog.clear()
        await manager.async_shutdown()  # must not propagate

        assert "Schedule task failed during shutdown" in caplog.text
        assert "store write failed while unwinding" in caplog.text

    async def test_cancelling_the_caller_cancels_the_tracked_task(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """HA shutdown still works: cancellation propagates through the wrapper.

        HA cancels the tasks it tracks; the arm now runs one level deeper, so
        that cancellation has to reach through `_run_tracked`'s `await task`.
        It does — `Task.cancel()` cancels the future the task is waiting on —
        and this pins it against a refactor that shields the inner task.
        """
        _set_panel(hass, "disarmed")
        fired = _capture_events(hass, EVENT_SCHEDULE_FIRED)
        fake_mode_changer.block()

        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        task = hass.async_create_task(manager.async_arm(pair.id))
        await fake_mode_changer.started.wait()

        inflight = list(manager._inflight)
        assert len(inflight) == 1

        task.cancel()
        await hass.async_block_till_done()

        assert inflight[0].cancelled()
        assert fired == []

    async def test_unexpected_errors_still_propagate_to_the_caller(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """The task layer must not swallow anything the caller used to see."""
        _set_panel(hass, "disarmed")
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )

        # An `Exception` would be absorbed by async_retry's `catch` and reported
        # as exhaustion, so raise past it: nothing retries a BaseException.
        def _boom(_attempt: int) -> None:
            raise _Unretryable

        fake_mode_changer.on_attempt = _boom

        with pytest.raises(_Unretryable):
            await manager.async_arm(pair.id)

        # The done-callback that drains `_inflight` is scheduled via call_soon,
        # so yield once — a failed task must not be retained either.
        await asyncio.sleep(0)
        assert manager._inflight == set()


class TestConcurrentEdits:
    """#202 — a WS edit landing mid-flight must survive the arm completing.

    `ScheduledPair` is mutable and `SchedulesStore.async_update` re-inserts the
    whole record by id, so whichever writer finishes last used to win every
    field — not just the ones it owns.  State confirmation (#192) holds an arm
    open for up to ~111 s, which is long enough for a user editing the schedule
    from the panel UI to lose the edit.
    """

    async def test_edit_during_in_flight_arm_survives(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """The arm keeps its runtime fields and leaves the edited ones alone."""
        _set_panel(hass, "disarmed")
        release = fake_mode_changer.block()

        pair = await manager.async_create(
            name="Nightly", weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        task = hass.async_create_task(manager.async_arm(pair.id))
        await fake_mode_changer.started.wait()

        # The user edits the schedule while the arm is still confirming.
        await manager.async_update(
            pair.id,
            name="Weeknights",
            weekdays=["mon", "tue"],
            arm_time="22:30",
            disarm_time="06:30",
        )

        release.set()
        await task
        await hass.async_block_till_done()

        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        assert refreshed.name == "Weeknights"
        assert refreshed.weekdays == ["mon", "tue"]
        assert refreshed.arm_time == "22:30"
        assert refreshed.disarm_time == "06:30"
        # …and the arm still recorded itself: the two field sets are disjoint,
        # so neither writer may cost the other its half.
        assert refreshed.last_armed_at is not None
        assert refreshed.last_error is None

    async def test_disarm_timer_honours_a_disarm_time_edited_mid_arm(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """The timer the arm schedules must use the edited window, not the stale one.

        Asserting only on the persisted record would not catch this: writing the
        stale copy back makes the store and the timer agree with each other on
        the *old* time.  So anchor the expectation to the 30-minute shift itself.
        """
        import custom_components.abode_security.scheduling.manager as manager_mod

        _set_panel(hass, "disarmed")
        release = fake_mode_changer.block()

        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        task = hass.async_create_task(manager.async_arm(pair.id))
        await fake_mode_changer.started.wait()

        await manager.async_update(pair.id, disarm_time="06:30")

        delays: list[float] = []
        real_call_later = manager_mod.async_call_later

        def _record(hass_: HomeAssistant, delay: float, action: Any) -> CancelHandle:
            delays.append(delay)
            return real_call_later(hass_, delay, action)  # type: ignore[no-any-return]

        with patch.object(manager_mod, "async_call_later", _record):
            release.set()
            await task
            await hass.async_block_till_done()

        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        assert refreshed.last_armed_at is not None

        tz = dt_util.DEFAULT_TIME_ZONE
        edited_boundary = expected_disarm_at(
            refreshed, last_armed_at=refreshed.last_armed_at, tz=tz
        )
        stale_boundary = expected_disarm_at(
            replace(refreshed, disarm_time="06:00"),
            last_armed_at=refreshed.last_armed_at,
            tz=tz,
        )
        assert edited_boundary - stale_boundary == timedelta(minutes=30)

        assert len(delays) == 1
        assert delays[0] == (edited_boundary - fake_clock.utcnow()).total_seconds()

    async def test_edit_during_in_flight_disarm_survives(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """The disarm edge has the same shape, and the same fix."""
        _set_panel(hass, "disarmed")
        pair = await manager.async_create(
            name="Nightly", weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        await manager.async_arm(pair.id)
        _set_panel(hass, "armed_home")

        release = fake_mode_changer.block()
        task = hass.async_create_task(manager.async_disarm(pair.id))
        await fake_mode_changer.started.wait()

        await manager.async_update(
            pair.id, name="Weeknights", weekdays=["mon", "tue"], arm_time="22:30"
        )

        release.set()
        await task
        await hass.async_block_till_done()

        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        assert refreshed.name == "Weeknights"
        assert refreshed.weekdays == ["mon", "tue"]
        assert refreshed.arm_time == "22:30"
        assert refreshed.last_disarmed_at is not None

    async def test_delete_during_in_flight_arm_is_not_resurrected(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Writing the captured copy back re-created a record the user removed.

        Deleting the pair also drops its disarm obligation — the same trade
        `async_delete` already makes for a pair deleted just after the arm
        completed.
        """
        _set_panel(hass, "disarmed")
        release = fake_mode_changer.block()

        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        task = hass.async_create_task(manager.async_arm(pair.id))
        await fake_mode_changer.started.wait()

        assert await manager.async_delete(pair.id) is True

        release.set()
        await task
        await hass.async_block_till_done()

        assert await manager.async_get(pair.id) is None
        assert manager._pending_handles == {}

    async def test_delete_clears_the_fire_failed_repair_issue(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Bailing on a deleted pair must not strand an undismissable issue.

        Only the arm and disarm success paths clear it, and both now return
        early once the pair is gone — so the delete has to clear it instead, or
        the user keeps an `is_fixable=False` repair issue naming a schedule that
        no longer exists.  Deleting a schedule that merely failed yesterday
        stranded it the same way.
        """
        _set_panel(hass, "disarmed")
        fake_mode_changer.set_fail_count(999)
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )

        with _no_retry_sleeps():
            await manager.async_arm(pair.id)

        issue_reg = ir.async_get(hass)
        issue_id = f"{REPAIR_ISSUE_SCHEDULE_FIRE_FAILED}_{pair.id}"
        assert issue_reg.async_get_issue("abode_security", issue_id) is not None

        assert await manager.async_delete(pair.id) is True

        assert issue_reg.async_get_issue("abode_security", issue_id) is None

    async def test_edit_landing_during_the_store_write_still_wins(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
        fake_mode_changer: FakeModeChanger,
    ) -> None:
        """Re-reading before the write is not enough — the write itself suspends.

        `SchedulesStore.async_update` is an immediate, non-debounced
        `Store.async_save`, so it parks on real disk I/O.  An edit landing in
        *that* window installs a new record, and the object the arm just wrote
        is already superseded — returning it would anchor the disarm timer to
        the old `disarm_time` while the store holds the new one.  The window is
        one disk write rather than ~111 s, but it is the same bug.
        """
        import custom_components.abode_security.scheduling.manager as manager_mod

        _set_panel(hass, "disarmed")
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )

        # Park the arm's own store write, and only that one: the edit issued
        # while it is parked has to be able to complete its own save.
        original_save = manager._store.async_save
        save_parked = asyncio.Event()
        resume_save = asyncio.Event()
        park_next = {"pending": True}

        async def _parking_save() -> None:
            if park_next["pending"]:
                park_next["pending"] = False
                save_parked.set()
                await resume_save.wait()
            await original_save()

        manager._store.async_save = _parking_save  # type: ignore[method-assign]

        delays: list[float] = []
        real_call_later = manager_mod.async_call_later

        def _record(hass_: HomeAssistant, delay: float, action: Any) -> CancelHandle:
            delays.append(delay)
            return real_call_later(hass_, delay, action)  # type: ignore[no-any-return]

        with patch.object(manager_mod, "async_call_later", _record):
            task = hass.async_create_task(manager.async_arm(pair.id))
            async with asyncio.timeout(5):
                await save_parked.wait()

            await manager.async_update(pair.id, disarm_time="06:30")

            resume_save.set()
            await task
            await hass.async_block_till_done()

        refreshed = await manager.async_get(pair.id)
        assert refreshed is not None
        assert refreshed.disarm_time == "06:30"
        assert refreshed.last_armed_at is not None

        tz = dt_util.DEFAULT_TIME_ZONE
        edited_boundary = expected_disarm_at(
            refreshed, last_armed_at=refreshed.last_armed_at, tz=tz
        )
        stale_boundary = expected_disarm_at(
            replace(refreshed, disarm_time="06:00"),
            last_armed_at=refreshed.last_armed_at,
            tz=tz,
        )
        assert edited_boundary - stale_boundary == timedelta(minutes=30)

        assert len(delays) == 1
        assert delays[0] == (edited_boundary - fake_clock.utcnow()).total_seconds()

    async def test_reconcile_rereads_each_pair_it_visits(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
    ) -> None:
        """Reconcile awaits inside its loop, so a later pair can change mid-pass.

        The anchor that matters is `expected_disarm_at`, which feeds the disarm
        timer this loop registers: reading it off the `get_all()` snapshot
        computes the boundary from a `disarm_time` the user has already
        replaced.  The deferred pass runs after HA start — or, past
        startup, once the panel entity appears — by which point the WS API is
        live, so this is reachable rather than theoretical.
        """
        import custom_components.abode_security.scheduling.manager as manager_mod

        restart_dt = datetime(2030, 1, 7, 23, 30, 0, tzinfo=UTC)
        fake_clock.set(restart_dt)
        _set_panel(hass, "armed_home")

        # First in insertion order, and it takes a *write* branch — its store
        # save is the suspension the edit below has to land in.
        elapsed = await manager.async_create(
            name="Elapsed", weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        elapsed.last_armed_at = restart_dt - timedelta(days=3)
        await manager._store.async_update(elapsed)

        # Second, still in window, and the one that gets edited.
        in_window = await manager.async_create(
            name="In window", weekdays=["mon"], arm_time="23:00", disarm_time="06:00"
        )
        in_window.last_armed_at = restart_dt
        await manager._store.async_update(in_window)

        # The store preserves insertion order, and the test depends on it: the
        # elapsed pair must be visited first so its write is what parks.  Stated
        # here so a reordering fails on this line rather than on a delay count.
        assert [p.id for p in await manager.async_get_all()] == [
            elapsed.id,
            in_window.id,
        ]

        original_save = manager._store.async_save
        save_parked = asyncio.Event()
        resume_save = asyncio.Event()
        park_next = {"pending": True}

        async def _parking_save() -> None:
            if park_next["pending"]:
                park_next["pending"] = False
                save_parked.set()
                await resume_save.wait()
            await original_save()

        manager._store.async_save = _parking_save  # type: ignore[method-assign]

        delays: list[float] = []
        real_call_later = manager_mod.async_call_later

        def _record(hass_: HomeAssistant, delay: float, action: Any) -> CancelHandle:
            delays.append(delay)
            return real_call_later(hass_, delay, action)  # type: ignore[no-any-return]

        with patch.object(manager_mod, "async_call_later", _record):
            task = hass.async_create_task(manager.async_reconcile_on_startup())
            async with asyncio.timeout(5):
                await save_parked.wait()

            await manager.async_update(in_window.id, disarm_time="06:30")

            resume_save.set()
            await task
            await hass.async_block_till_done()

        refreshed = await manager.async_get(in_window.id)
        assert refreshed is not None
        assert refreshed.disarm_time == "06:30"
        assert refreshed.last_armed_at is not None
        assert refreshed.last_armed_at == restart_dt

        tz = dt_util.DEFAULT_TIME_ZONE
        edited_boundary = expected_disarm_at(
            refreshed, last_armed_at=refreshed.last_armed_at, tz=tz
        )
        stale_boundary = expected_disarm_at(
            replace(refreshed, disarm_time="06:00"),
            last_armed_at=refreshed.last_armed_at,
            tz=tz,
        )
        assert edited_boundary - stale_boundary == timedelta(minutes=30)

        # Only the in-window pair gets a timer; the elapsed one is just marked.
        assert len(delays) == 1
        assert delays[0] == (edited_boundary - restart_dt).total_seconds()

    async def test_manual_override_rereads_each_pair_it_visits(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
        fake_clock: FakeClock,
    ) -> None:
        """Same loop shape, and here it is the guards that must see the edit.

        A pair disabled while an earlier iteration is writing must not be
        recorded as manually overridden — `async_update` owns `enabled`, and the
        snapshot's copy still says True.
        """
        now = datetime(2030, 1, 7, 23, 30, 0, tzinfo=UTC)
        fake_clock.set(now)
        _set_panel(hass, "armed_home")

        first = await manager.async_create(
            name="First", weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        first.last_armed_at = now
        await manager._store.async_update(first)

        second = await manager.async_create(
            name="Second", weekdays=["mon"], arm_time="23:00", disarm_time="06:00"
        )
        second.last_armed_at = now
        await manager._store.async_update(second)

        original_save = manager._store.async_save
        save_parked = asyncio.Event()
        resume_save = asyncio.Event()
        park_next = {"pending": True}

        async def _parking_save() -> None:
            if park_next["pending"]:
                park_next["pending"] = False
                save_parked.set()
                await resume_save.wait()
            await original_save()

        manager._store.async_save = _parking_save  # type: ignore[method-assign]

        skipped = _capture_events(hass, EVENT_SCHEDULE_SKIPPED)

        task = hass.async_create_task(manager._handle_manual_override())
        async with asyncio.timeout(5):
            await save_parked.wait()

        await manager.async_update(second.id, enabled=False)

        resume_save.set()
        await task
        await hass.async_block_till_done()

        refreshed = await manager.async_get(second.id)
        assert refreshed is not None
        assert refreshed.last_skip_reason != SkipReason.MANUAL_OVERRIDE
        assert [e["schedule_id"] for e in skipped] == [first.id]

    async def test_scheduling_a_disarm_cancels_the_handle_it_replaces(
        self,
        hass: HomeAssistant,
        manager: ScheduleManager,
    ) -> None:
        """Overwriting the dict entry leaked a live timer nobody could cancel.

        The orphan still fires; only `_disarm_impl`'s `derive_state` guard keeps
        that harmless, which is an accident rather than a design.
        """
        _set_panel(hass, "disarmed")
        pair = await manager.async_create(
            weekdays=["mon"], arm_time="22:00", disarm_time="06:00"
        )
        await manager.async_arm(pair.id)

        stored = await manager.async_get(pair.id)
        assert stored is not None

        # Stand a recorder in for the real handle, so replacing it is observable.
        manager._pending_handles[(pair.id, "disarm")]()
        cancelled = False

        def _recording_handle() -> None:
            nonlocal cancelled
            cancelled = True

        manager._pending_handles[(pair.id, "disarm")] = _recording_handle

        manager._schedule_disarm(stored)

        assert cancelled
        assert manager._pending_handles[(pair.id, "disarm")] is not _recording_handle
