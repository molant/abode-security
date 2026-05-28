---
status: pending
---

# Phase 3: Runtime — fire, skip, reconcile, retry

Bring the schedules to life. Add the pure `derive_state` function, the `RetryPolicy` helper, and the runtime methods on `ScheduleManager` that register timers, fire arm/disarm at the right time, skip when Away is active, cancel pending disarms on manual override, reconcile after restart, retry on failure, and fire HA events.

After this phase, the feature is **fully functional headlessly** — a user could exercise the entire flow via the WS API. The frontend (Phase 4) is the discoverability layer.

## Context

Phases 1 and 2 set up the static surface:
- Storage and CRUD work.
- `Clock`, `ScheduleClock`, `ModeChanger` protocols exist with HA impls.
- `ScheduleManager` is constructed with all dependencies, but the runtime methods are stubs.

This phase is the **highest-risk, highest-value** phase. The user explicitly named "unexpected arming/disarming during ambiguous states" as the top risk. Every decision here should err on the side of **not changing the panel state**.

Read [./README.md](./README.md) — especially the **Skip rule**, **Overlapping pairs**, **State machine**, **Restart reconciliation**, and **Retry policy** sections. Re-read [phase-1-domain-and-crud.md](./phase-1-domain-and-crud.md) and [phase-2-mode-dispatcher.md](./phase-2-mode-dispatcher.md) for context — Phase 3 strictly extends them.

## Structure

```
custom_components/abode_security/
  scheduling/
    state_machine.py             # new: derive_state pure function + helpers
    retry.py                     # new: RetryPolicy.async_run(coro_factory) -> result
    manager.py                   # update: runtime methods (async_arm, async_disarm, reconciliation, listener)
  __init__.py                    # update: call async_reconcile_on_startup, register listeners, cancel on unload
  const.py                       # update: EVENT_SCHEDULE_FIRED, EVENT_SCHEDULE_SKIPPED, EVENT_SCHEDULE_FAILED, retry constants
  diagnostics.py                 # update: include schedule manager stats in diagnostics dump
  strings.json                   # update: schedule_fire_failed repair issue translation
tests/
  test_state_machine.py          # new: derive_state matrix
  test_retry.py                  # new: backoff sequence, success-on-retry-2, exhaustion
  test_schedule_runtime.py       # new: arm/disarm fire, skip rules, manual override, reconciliation, retries
  test_schedule_integration.py   # new: integration test with mock-abode
```

## Implementation Checklist

### Baseline Test Verification

- [ ] `uv run pytest -m ""` — all tests pass after Phases 1 and 2.
- [ ] `uv run pytest -m integration` against `./scripts/dev.sh` stack — passes.
- [ ] `./scripts/check.sh` — green.

### Sub-Phase A: State machine (`scheduling/state_machine.py`)

Deployable unit: a pure function. No side effects. Comprehensively unit tested.

#### Implementation

- [ ] Create `scheduling/state_machine.py`:
  ```python
  from datetime import datetime, time, timedelta, tzinfo
  from enum import Enum, auto
  from .models import ScheduledPair, weekday_index, is_overnight

  class PairState(Enum):
      IDLE = auto()
      ARMED = auto()  # we armed it; disarm pending

  def derive_state(pair: ScheduledPair, *, now: datetime, tz: tzinfo) -> PairState:
      """Pure: pair is ARMED iff last_armed_at > last_disarmed_at AND we're still
      within the pair's window from that arm time. Otherwise IDLE.

      Window is computed from the arm timestamp + the pair's disarm_time:
      next disarm time at or after last_armed_at in HA's local tz.

      `tz` MUST be passed in explicitly (typically `dt_util.DEFAULT_TIME_ZONE`)
      and is forwarded to `expected_disarm_at`. See that function's docstring
      for why an implicit default is unsafe.
      """
      if pair.last_armed_at is None:
          return PairState.IDLE
      if pair.last_disarmed_at is not None and pair.last_disarmed_at >= pair.last_armed_at:
          return PairState.IDLE
      expected_disarm = expected_disarm_at(pair, last_armed_at=pair.last_armed_at, tz=tz)
      if now >= expected_disarm:
          return PairState.IDLE  # window has elapsed; treat as IDLE
      return PairState.ARMED

  def expected_disarm_at(
      pair: ScheduledPair, *, last_armed_at: datetime, tz: tzinfo
  ) -> datetime:
      """Next occurrence of pair.disarm_time at or after last_armed_at, in HA tz.

      `tz` MUST be passed in explicitly — typically `dt_util.DEFAULT_TIME_ZONE`
      (which HA sets to `hass.config.time_zone`). Do NOT use bare `.astimezone()`
      with no argument: that defaults to the system local tz, which is UTC in
      Docker containers and will silently produce wrong wall-clock times.
      """
      local = last_armed_at.astimezone(tz)
      disarm_t = parse_hhmm(pair.disarm_time)
      candidate = local.replace(hour=disarm_t.hour, minute=disarm_t.minute, second=0, microsecond=0)
      if candidate <= local:
          candidate += timedelta(days=1)
      return candidate

  def parse_hhmm(s: str) -> time: ...  # "22:00" -> time(22, 0)
  ```
- [ ] Document that `derive_state` collapses PENDING_ARM/PENDING_DISARM into IDLE/ARMED — the "pending" states from the README are conceptual; the runtime tracks pending timers separately as `dict[(pair_id, edge)] -> CancelHandle`.

#### Tests

- [ ] `tests/test_state_machine.py` (no HA needed):
  - Empty pair (`last_armed_at=None`) → `IDLE`.
  - `last_armed_at < last_disarmed_at` → `IDLE`.
  - `last_armed_at > last_disarmed_at`, `now` within window → `ARMED`.
  - `last_armed_at > last_disarmed_at`, `now` past expected disarm → `IDLE`.
  - Overnight pair: arm Sat 22:00, disarm 06:00 Sun, `now` Sat 23:30 → `ARMED`.
  - Overnight pair: arm Sat 22:00, disarm 06:00 Sun, `now` Sun 06:30 → `IDLE`.
  - Same-day pair: arm 13:00, disarm 17:00, `now` 14:00 → `ARMED`.
  - DST forward edge: arm 22:00 on a day where 02:30 doesn't exist — `derive_state` is unaffected because it works on the actual `last_armed_at` timestamp.
  - `expected_disarm_at` correctness for all four time orderings.

### Sub-Phase B: Retry policy (`scheduling/retry.py`)

Deployable unit: a `RetryPolicy` class that runs an async factory with backoff. Pure-async; takes a `Clock` so backoff is mockable via `asyncio.sleep` (which `freezegun` does not freeze, but HA's `async_fire_time_changed` does).

#### Implementation

- [ ] In `const.py` add:
  ```python
  SCHEDULE_RETRY_DELAYS_SECONDS = (1, 4, 16)  # 3 retries
  SCHEDULE_RETRY_TOTAL_ATTEMPTS = 4  # 1 initial + 3 retries — must equal len(SCHEDULE_RETRY_DELAYS_SECONDS) + 1
  ```
  Total attempts = 1 initial + 3 retries = 4 calls maximum. Sleeps run between attempts: sleep 1s after attempt 1, sleep 4s after attempt 2, sleep 16s after attempt 3. Match the README "Retry policy" section exactly.
- [ ] Create `scheduling/retry.py`:
  ```python
  import asyncio
  from typing import Awaitable, Callable, TypeVar, Iterable
  from .const import SCHEDULE_RETRY_DELAYS_SECONDS

  T = TypeVar("T")

  class RetryExhausted(Exception):
      def __init__(self, last_error: BaseException, attempts: int):
          super().__init__(f"Exhausted after {attempts} attempts: {last_error}")
          self.last_error = last_error
          self.attempts = attempts

  async def async_retry(
      factory: Callable[[], Awaitable[T]],
      *,
      delays: Iterable[int] = SCHEDULE_RETRY_DELAYS_SECONDS,
      catch: type[BaseException] | tuple[type[BaseException], ...] = Exception,
  ) -> T:
      delays_list = list(delays)
      last_error: BaseException | None = None
      total_attempts = len(delays_list) + 1
      for attempt in range(total_attempts):
          try:
              return await factory()
          except catch as err:
              last_error = err
              if attempt < total_attempts - 1:
                  await asyncio.sleep(delays_list[attempt])
      assert last_error is not None
      raise RetryExhausted(last_error, total_attempts)
  ```

#### Tests

- [ ] `tests/test_retry.py`:
  - Happy path: factory succeeds on first try → returns value, no sleeps.
  - Succeeds on attempt 2 → sleeps 1s, returns value.
  - Succeeds on attempt 4 → sleeps 1s, 4s, 16s, returns value.
  - Fails all 4 attempts → raises `RetryExhausted` with `attempts == SCHEDULE_RETRY_TOTAL_ATTEMPTS` (= 4).
  - Non-caught exception type propagates immediately without retry.
  - Keep tests fast: pass `delays=(0, 0, 0)` (the `delays` parameter is the supported injection point — `asyncio.sleep(0)` yields to the loop without wall-clock waits) **or** monkeypatch `asyncio.sleep` on the `scheduling.retry` module. Do NOT call `freezegun.freeze_time` here — freezegun does not patch `asyncio.sleep`, so the test would still wait 21 real seconds.

### Sub-Phase C: Manager runtime — arm/disarm flows

Deployable unit: `ScheduleManager.async_arm(pair_id)` and `async_disarm(pair_id)` methods, plus the timer-registration loop that calls them.

#### Implementation

- [ ] Add to `scheduling/manager.py`:
  - `_pending_handles: dict[tuple[str, str], CancelHandle]` — keyed by `(pair_id, "arm" | "disarm")`. The `"arm"` entry is the daily `ScheduleClock` handle registered at setup. The `"disarm"` entry is the one-shot `async_call_later` handle registered after a successful arm (or restored by reconciliation); absent until then.
  - `_panel_entity_id() -> str | None` helper — calls `find_abode_alarm_panel(self._hass)` (from `helpers.py`) and returns `state.entity_id` or `None`. Use this everywhere the manager needs to read the live panel state, and re-resolve on every call (do **not** cache — the entity can be re-registered).
  - `_panel_state() -> str | None` helper — combines the entity lookup with `hass.states.get(...).state`, returning the string state or `None` if either the entity is missing or its state is `None`. Use this in `async_arm`, `async_disarm`, the listener, and reconciliation so the "panel unavailable" branch is exercised through one code path.
  - `async_setup()` (extended): after `store.async_load()`, call `_register_all_timers()`, `_start_panel_listener()` (defined in Sub-Phase E), and `await async_reconcile_on_startup()`.
  - `_register_pair_timers(pair_id)` — register the **arm** callback for ONE enabled pair via `scheduler_clock.async_track_daily(...)`. Store the cancel handle under `(pair.id, "arm")`. No-op if the pair is missing, disabled, or already has an arm handle. Disarm handles are NOT registered here — they're created on-demand by a successful arm (or by reconciliation).
  - `_register_all_timers()` — iterate every pair in the store and call `_register_pair_timers(pair.id)`. Used by `async_setup()` only.
  - `_unregister_timers(pair_id)` — cancel and remove BOTH the `(pair_id, "arm")` daily handle and the `(pair_id, "disarm")` one-shot handle if present.
  - `async_create` / `async_update` / `async_delete` (from Phase 1): now also `_unregister_timers(pair_id)` and (for create/update only) `_register_pair_timers(pair_id)` after the storage mutation. This is the **only** way live timer registration changes after startup.
  - `async_shutdown()` (extended): cancel all handles in `_pending_handles`, then cancel `self._listener_handle` (the state-change listener registered by `_start_panel_listener` in Sub-Phase E) if set.
  - `async_arm(pair_id)`:
    1. Fetch the pair. If not enabled or not found: return.
    2. Read the live panel state via `panel_str = self._panel_state()` (the helper defined above — do NOT call `hass.states.get(...)` directly here; the helper is the single code path for panel-state reads). Evaluate the skip rule against `panel_str`. Always assign `last_skip_reason` from the `SkipReason` enum (never a bare string literal) — the field is typed `SkipReason | None`, the enum values match the storage strings (`StrEnum`), and using the enum keeps mypy/pyright honest:
       - `armed_away` → fire `schedule_skipped` (`reason=SkipReason.AWAY_ACTIVE`), set `pair.last_skip_reason = SkipReason.AWAY_ACTIVE`, set `pair.last_disarmed_at = clock.utcnow()` (so the window is closed), persist, return.
       - `armed_home` → fire `schedule_skipped` (`reason=SkipReason.ALREADY_HOME`), set `pair.last_skip_reason = SkipReason.ALREADY_HOME`, but **also** set `pair.last_armed_at = clock.utcnow()` (we "take ownership" so our disarm fires later). Persist. Schedule the disarm timer (one-shot — see below). Return.
       - `disarmed` → proceed with arm.
       - Intermediate (`arming`, `pending`, `triggered`, `unavailable`, `unknown`, `None`) → fire `schedule_skipped` (`reason=SkipReason.PANEL_UNAVAILABLE`), set `pair.last_skip_reason = SkipReason.PANEL_UNAVAILABLE`, set `pair.last_disarmed_at = clock.utcnow()`, persist, return.
    3. Call `await async_retry(lambda: mode_changer.async_set_mode("home", SCHEDULE_ARM, pair_id=pair.id))`.
    4. On success: set `pair.last_armed_at = clock.utcnow()`, clear `last_error`, clear `last_skip_reason`, persist. Fire `schedule_fired` (`action=arm`). Register the one-shot disarm timer for this window's expected disarm time.
    5. On `RetryExhausted`: set `pair.last_error = str(err.last_error)[:200]`, persist. Fire `schedule_failed` event. Raise repair issue. **Do not** update `last_armed_at` (the pair stays IDLE).
  - `async_disarm(pair_id, *, source=ChangeSource.SCHEDULE_DISARM)`:
    1. Fetch pair. If not enabled, missing, or `derive_state(pair, now=clock.utcnow(), tz=dt_util.DEFAULT_TIME_ZONE) != ARMED`: return (the matching arm did not fire, or window elapsed).
    2. Re-evaluate panel state via `panel_str = self._panel_state()` (same helper as `async_arm`). As in `async_arm`, always assign `last_skip_reason` from the `SkipReason` enum:
       - `armed_away` → fire `schedule_skipped` (`reason=SkipReason.MANUAL_OVERRIDE`), set `pair.last_skip_reason = SkipReason.MANUAL_OVERRIDE`, set `pair.last_disarmed_at = clock.utcnow()`, persist, return.
       - `disarmed` → already disarmed (manual or external) → fire `schedule_skipped` (`reason=SkipReason.MANUAL_OVERRIDE`), set `pair.last_skip_reason = SkipReason.MANUAL_OVERRIDE`, set `pair.last_disarmed_at = clock.utcnow()`, persist, return.
       - `armed_home` → proceed.
       - Intermediate (`arming`, `pending`, `triggered`, `unavailable`, `unknown`, `None`) → fire `schedule_skipped` (`reason=SkipReason.PANEL_UNAVAILABLE`), set `pair.last_skip_reason = SkipReason.PANEL_UNAVAILABLE`, set `pair.last_disarmed_at = clock.utcnow()`, persist, return.
    3. Call `await async_retry(lambda: mode_changer.async_set_mode("standby", source, pair_id=pair.id))`.
    4. On success: set `pair.last_disarmed_at = clock.utcnow()`, persist. Fire `schedule_fired` (`action=disarm`).
    5. On `RetryExhausted`: same as arm — set `last_error`, fire `schedule_failed`, repair issue. Do NOT update `last_disarmed_at` — the pair stays ARMED, and we'll try again next time someone calls `async_disarm` (e.g. via manual override path or via next-day scheduled re-arm's window closure).
  - **Disarm scheduling — one-shot only**: after a successful arm, register a single-fire `async_call_later(hass, seconds_until_expected_disarm, lambda _now: hass.async_create_task(async_disarm(pair_id)))`. Compute the delay precisely from `expected_disarm_at(pair, last_armed_at=clock.utcnow(), tz=dt_util.DEFAULT_TIME_ZONE)` — the `tz` kwarg is mandatory (see Sub-Phase A). Do **not** register a daily `ScheduleClock` handle for disarm — the daily handle's weekday filter would be wrong for overnight pairs (the disarm fires the day after the arm weekday), and reconciliation re-creates the `async_call_later` on restart. Only the **arm** edge uses the daily `ScheduleClock` handle.

#### Tests

- [ ] `tests/test_schedule_runtime.py` (use HA test harness, fake `Clock` + fake `ScheduleClock` + fake `ModeChanger`):
  - **Happy path arm + disarm**: register a Mon 22:00 → 06:00 pair. Advance fake time. Verify `mode_changer.async_set_mode("home", SCHEDULE_ARM, pair_id=...)` called. Advance to 06:00 next day. Verify `mode_changer.async_set_mode("standby", SCHEDULE_DISARM, pair_id=...)` called. Verify `schedule_fired` events.
  - **Skip when Away active**: panel state `armed_away` at arm time → no `mode_changer` call; `schedule_skipped` fired with `reason="away_active"`; `last_disarmed_at` set so disarm doesn't fire.
  - **Already Home — extends pair**: panel state `armed_home` at arm time → no `mode_changer` call for arm; but `last_armed_at` set and one-shot disarm scheduled. At disarm time, panel still `armed_home`, disarm fires.
  - **Panel unavailable**: panel state `unavailable` at arm time → no `mode_changer` call; `schedule_skipped` with `reason="panel_unavailable"`.
  - **Manual override mid-window**: pair armed normally. Fire an `EVENT_STATE_CHANGED` event with `context.id=` something not starting with `abode_sched_` (simulating user-WS or external) changing panel to `disarmed`. Verify the one-shot disarm timer is cancelled and `schedule_skipped` fired with `reason="manual_override"`.
  - **Self-driven state change ignored**: manager arms the pair. Then the EVENT_STATE_CHANGED arrives with `context.id` starting with `abode_sched_` — manager must NOT treat it as manual override (no cancel).
  - **Disabled pair**: `enabled=False` → no timers registered, `_pending_handles` empty.
  - **Update re-registers timers**: update a pair's arm_time → old handles cancelled, new ones registered.
  - **Delete cancels timers**: delete a pair with pending disarm → `async_call_later` cancel handle is invoked.
  - **Retry succeeds on attempt 2**: mode_changer raises `ModeChangeFailed` once then succeeds → arm completes, no `schedule_failed` event.
  - **Retry exhaustion**: mode_changer always fails → `schedule_failed` fired with `attempts=4`; repair issue raised; `last_armed_at` NOT updated; pair stays IDLE.
  - **Overlapping pairs**: A arms 22:00 → 06:00; B arms 23:00 → 08:00. Trace to assert step-by-step:
    1. At 22:00 A's `async_arm` runs: panel `disarmed` → `mode_changer.async_set_mode("home", SCHEDULE_ARM, pair_id=A)` called; A's `last_armed_at` set; A's one-shot disarm scheduled for 06:00.
    2. At 23:00 B's `async_arm` runs: panel is now `armed_home` → `already_home` branch → `mode_changer` NOT called; B's `last_armed_at` set to now (take ownership); `schedule_skipped` fired with `reason="already_home"`; B's one-shot disarm scheduled for 08:00.
    3. At 06:00 A's disarm fires: panel `armed_home` → `mode_changer.async_set_mode("standby", SCHEDULE_DISARM, pair_id=A)` called; A's `last_disarmed_at` set.
    4. The panel transition `armed_home → disarmed` is **self-driven** (Context.id starts with `abode_sched_`) so the manual-override listener does NOT fire and B's one-shot disarm is NOT cancelled here. Assert this explicitly — it is the key correctness point.
    5. At 08:00 B's one-shot disarm fires: `derive_state(B, now=08:00, tz=...)` is still `ARMED` (B.last_armed_at > B.last_disarmed_at and 08:00 is at the expected disarm time, not past it). `async_disarm` re-evaluates the live panel state: panel is `disarmed` → `schedule_skipped` fired with `reason="manual_override"`; B's `last_disarmed_at` set; `mode_changer` NOT called.

### Sub-Phase D: Restart reconciliation

Deployable unit: `async_reconcile_on_startup()` runs after `async_setup()` and ensures no stale pending state.

#### Implementation

- [ ] Add `async_reconcile_on_startup()` to `ScheduleManager`:
  ```python
  async def async_reconcile_on_startup(self) -> None:
      now = self._clock.utcnow()
      panel_str = self._panel_state()  # uses helper defined above
      tz = dt_util.DEFAULT_TIME_ZONE  # HA-configured tz; never bare astimezone()
      reconciled = 0
      for pair in self._store.get_all():
          if not pair.enabled:
              continue
          if pair.last_armed_at is None:
              continue
          if pair.last_disarmed_at is not None and pair.last_disarmed_at >= pair.last_armed_at:
              continue
          # Pair was armed and never disarmed — reconcile.
          expected_disarm = expected_disarm_at(pair, last_armed_at=pair.last_armed_at, tz=tz)
          if now >= expected_disarm:
              # Window elapsed. Mark as disarmed (externally).
              pair.last_disarmed_at = now
              pair.last_skip_reason = SkipReason.RECONCILE_WINDOW_ELAPSED
              await self._store.async_update(pair)
              continue
          if panel_str != "armed_home":
              # Panel no longer Home — manual disarm happened during downtime.
              pair.last_disarmed_at = now
              pair.last_skip_reason = SkipReason.RECONCILE_PANEL_NOT_HOME
              await self._store.async_update(pair)
              continue
          # Re-register the one-shot disarm timer.
          # IMPORTANT: bind `pair.id` via a default argument (`pid=pair.id`)
          # so the lambda captures the value, not the loop variable. Without
          # this, every registered callback would see the LAST pair's id by
          # the time it fires (Python's late-binding closure semantics).
          delay = (expected_disarm - now).total_seconds()
          handle = async_call_later(
              self._hass,
              delay,
              lambda _now, pid=pair.id: self._hass.async_create_task(
                  self.async_disarm(pid, source=ChangeSource.RECONCILE_DISARM)
              ),
          )
          self._pending_handles[(pair.id, "disarm")] = handle
          reconciled += 1
      _LOGGER.info("Reconciled %d schedules on startup", reconciled)
  ```
- [ ] In `__init__.py`, ensure `manager.async_setup()` (which now calls reconciliation internally) runs **after** the alarm panel entity is registered. If reconciliation runs before the panel entity is in `hass.states`, `panel_str` is `None` → we'd disarm everything. Add an explicit guard: if `panel_state is None`, defer reconciliation via `hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, ...)`.

#### Tests

- [ ] In `tests/test_schedule_runtime.py`, add reconciliation cases:
  - **Reconcile in-window, still Home**: pair armed yesterday 22:00, disarm 06:00; restart at 23:30 with panel `armed_home`. → re-register one-shot disarm; at 06:00 it fires.
  - **Reconcile in-window, panel not Home**: same pair, restart at 23:30 with panel `armed_away`. → set `last_disarmed_at = now`; no disarm timer; pair becomes IDLE.
  - **Reconcile out-of-window**: pair armed 2 days ago, never disarmed; restart now. → set `last_disarmed_at = now`; no disarm; pair becomes IDLE.
  - **Missed arm — no catch-up**: pair scheduled to arm at 22:00, restart at 22:30 with `last_armed_at=None`. → no arm fired (HA `async_track_time_change` doesn't backfill, and reconciliation only touches already-armed pairs).
  - **Reconciliation runs after EVENT_HOMEASSISTANT_STARTED if panel not yet available**: simulate by setting up integration without panel entity present, then firing the event with panel present → reconciliation runs.

### Sub-Phase E: Manual-override listener

Deployable unit: a single `EVENT_STATE_CHANGED` listener on the alarm panel entity that cancels pending disarms when a non-self-driven mode change is detected.

#### Implementation

- [ ] In `ScheduleManager`, add:
  ```python
  from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
  from homeassistant.core import callback

  def _start_panel_listener(self) -> None:
      panel = self._panel_entity_id()
      if panel is None:
          # Panel not yet registered. Defer once via EVENT_HOMEASSISTANT_STARTED.
          # If it's still missing after that event, log a warning and give up —
          # the user has no Abode panel configured and schedules cannot fire.
          @callback
          def _retry(_event):
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
          self._hass, [panel], self._on_panel_state_changed
      )

  @callback
  def _on_panel_state_changed(self, event: Event) -> None:
      ctx_id = event.context.id or ""
      if ctx_id.startswith(CONTEXT_ID_PREFIX):
          return  # our own change, ignore
      old_state = event.data.get("old_state")
      new_state = event.data.get("new_state")
      if new_state is None or new_state.state == "armed_home":
          return  # we only care about transitions leaving armed_home
      if old_state is None or old_state.state != "armed_home":
          return
      # Dispatch the async handler — the listener itself is @callback (sync) but
      # the work involves awaiting store.async_update, so hand off to a task.
      self._hass.async_create_task(self._handle_manual_override())

  async def _handle_manual_override(self) -> None:
      now = self._clock.utcnow()
      for pair in self._store.get_all():
          if not pair.enabled:
              continue
          if derive_state(pair, now=now, tz=dt_util.DEFAULT_TIME_ZONE) != PairState.ARMED:
              continue
          handle = self._pending_handles.pop((pair.id, "disarm"), None)
          if handle is not None:
              handle()  # cancel
          pair.last_disarmed_at = now
          pair.last_skip_reason = SkipReason.MANUAL_OVERRIDE
          # Persist BEFORE firing the event — see Constraints "Persist before
          # firing events". A crash between persist and fire is acceptable;
          # the reverse order would leak misleading events.
          await self._store.async_update(pair)
          self._fire_event(EVENT_SCHEDULE_SKIPPED, pair, action="disarm", reason=SkipReason.MANUAL_OVERRIDE)
  ```

#### Tests

- [ ] In `tests/test_schedule_runtime.py`:
  - **Manual disarm**: pair ARMED; user fires `alarm_control_panel.alarm_disarm` (via `hass.services.async_call(... context=Context())`). Listener cancels pending disarm; pair marked `last_skip_reason="manual_override"`.
  - **Manual to Away**: pair ARMED; panel goes `armed_away`. Listener cancels pending disarm; pair marked.
  - **Self-driven transition ignored**: pair ARMED; manager fires its own disarm (Context.id starts with `abode_sched_`). Listener sees the event but ignores it.
  - **No pairs ARMED → listener no-op**: panel disarms when no pairs are ARMED. No events, no errors.

### Sub-Phase F: HA events + repair issue + diagnostics

Deployable unit: observability.

#### Implementation

- [ ] In `const.py` add:
  ```python
  EVENT_SCHEDULE_FIRED = "abode_security.schedule_fired"
  EVENT_SCHEDULE_SKIPPED = "abode_security.schedule_skipped"
  EVENT_SCHEDULE_FAILED = "abode_security.schedule_failed"
  REPAIR_ISSUE_SCHEDULE_FIRE_FAILED = "schedule_fire_failed"
  ```
- [ ] Add `strings.json` entry for `issues.schedule_fire_failed` with `{schedule_name}` and `{error}` placeholders.
- [ ] Add `_fire_event(self, name, pair, **extra)` helper on the manager that builds a dict and calls `hass.bus.async_fire(name, payload)`.
- [ ] Payloads as defined in README:
  - `schedule_fired`: `{schedule_id, schedule_name, action, target_mode, fired_at}` (fired_at = ISO UTC string of `clock.utcnow()`).
  - `schedule_skipped`: `{schedule_id, schedule_name, action, reason, skipped_at}`.
  - `schedule_failed`: `{schedule_id, schedule_name, action, error, attempts, failed_at}`.
- [ ] Repair issue: use `homeassistant.helpers.issue_registry.async_create_issue` with `issue_id=f"schedule_fire_failed_{pair_id}"`, `is_fixable=False`, `severity=ir.IssueSeverity.ERROR`, `translation_key=REPAIR_ISSUE_SCHEDULE_FIRE_FAILED`, `translation_placeholders={"schedule_name": pair.name or pair.id, "error": str(err)[:200]}` — mirrors the `ActionStore._raise_corrupt_issue` call shape at `action_manager.py:263-273`. Clear via `async_delete_issue` (same `issue_id`) on the next successful arm/disarm for that pair.
- [ ] In `diagnostics.py`, add to the dump: `"schedules": {"count": N, "enabled_count": N, "last_fired_at": iso, "last_failed_at": iso}` — high-level stats only; do NOT include schedule contents (privacy).

#### Tests

- [ ] In `tests/test_schedule_runtime.py`:
  - Event payloads match the documented shape for arm/disarm/skip/fail.
  - Repair issue raised after retry exhaustion; cleared after next success.
  - Diagnostics dump includes schedule stats and does NOT include schedule names or times.

### Sub-Phase G: Integration test

Deployable unit: one end-to-end test against the mock Abode API verifying a complete flow.

#### Implementation

- [x] Create `tests/test_schedule_integration.py` with `@pytest.mark.integration`:
  - Boot the mock Abode stack (existing fixture from `conftest.py`; see `tests/test_*_integration.py` for the pattern).
  - Create a schedule via WS `schedules/create` for "today 22:00 → 06:00".
  - Advance HA's monotonic clock to 22:00 today using BOTH `freezegun.freeze_time` (for `dt_util.utcnow` / `dt_util.now`) AND `pytest_homeassistant_custom_component.async_fire_time_changed(hass, target_dt)` (so `async_track_time_change` callbacks fire). One without the other is insufficient — `async_track_time_change` schedules against HA's internal "next fire" computation, which only re-evaluates when `async_fire_time_changed` is called. See HA testing docs and the existing `test_action_trigger.py` patterns.
  - Verify the alarm_control_panel entity transitions to `armed_home`.
  - Repeat the advance pattern to 06:00 tomorrow.
  - Verify the entity transitions to `disarmed`.
  - Verify `schedule_fired` events on the bus (use `async_capture_events`).

### Documentation (End of Phase)

- [ ] `docs/ARCHITECTURE.md` — extend the schedule scheduling subsystem section: add a sequence diagram (Mermaid) of "user creates schedule → arm fires → context-id propagates → state change → manager handles".
- [ ] `docs/notifications.md` — append a section "Notifying on schedule events" with a small automation snippet listening on `abode_security.schedule_fired` / `schedule_failed` (parallel to the existing `action_triggered` pattern). Mention the bundled blueprint already covers the shape; users can copy and adapt.
- [ ] `CLAUDE.md` — no change needed.

### Build Verification

- [ ] `uv run ruff check .` — zero issues.
- [ ] `uv run mypy custom_components` — zero errors.
- [ ] `uv run pyright` — zero errors.
- [ ] `uv run pytest -m ""` — all tests pass.
- [ ] `uv run pytest -m integration` against `./scripts/dev.sh` stack — passes.
- [ ] Scan output for `WARNING` / `ERROR` lines; verify no unexpected stack traces.
- [ ] `./scripts/check.sh` — green.

### Manual Verification with MCP Tools

After the integration test passes, exercise the feature end-to-end on the dev HA stack:

- [ ] `./scripts/dev.sh` running; HA at http://localhost:8123.
- [ ] Use `mcp__home-assistant__ha_call_service` to call `abode_security/schedules/create` via WS (or `curl` against the WS endpoint) with a schedule firing in ~30s.
- [ ] Wait, then use `mcp__home-assistant__ha_get_state` on the alarm_control_panel entity → confirm it's `armed_home`.
- [ ] Use `mcp__home-assistant__ha_get_logs` and grep for `Schedule '...' fired arm` — confirm it appears.
- [ ] Trigger the manual-override path: use `ha_call_service` to call `alarm_control_panel.alarm_disarm` on the panel mid-window. Confirm the schedule's pending disarm is cancelled (log line `Schedule '...' skipped (manual_override)`).
- [ ] Trigger the failure path: stop the mock Abode container; create a schedule that fires in 30s; wait; confirm `schedule_failed` event fires after retries, and verify the repair issue appears in the HA Repairs UI (http://localhost:8123/config/repairs).
- [ ] Restart HA mid-window: arm a schedule, restart HA via `docker compose restart homeassistant`, verify reconciliation re-schedules the disarm by waiting for it to fire.

## Technical Details

### Reconciliation pseudocode

```
on startup, after panel entity is available:
    now = clock.utcnow()
    tz = dt_util.DEFAULT_TIME_ZONE
    for pair in store.get_all():
        if not enabled: continue
        if last_armed_at is None: continue
        if last_disarmed_at >= last_armed_at: continue
        # Pair has an open arm.
        expected_disarm = expected_disarm_at(pair, last_armed_at=last_armed_at, tz=tz)
        if now >= expected_disarm:
            pair.last_disarmed_at = now
            pair.last_skip_reason = "reconcile_window_elapsed"
            await store.async_update(pair)
            continue
        if panel_state != "armed_home":
            pair.last_disarmed_at = now
            pair.last_skip_reason = "reconcile_panel_not_home"
            await store.async_update(pair)
            continue
        # In window, still Home — re-register one-shot disarm.
        # Bind pair.id via default-arg (`pid=pair.id`) to dodge late-binding
        # closure semantics across the loop.
        async_call_later(hass, (expected_disarm - now).total_seconds(),
                         lambda _now, pid=pair.id: async_disarm(pid, source=RECONCILE_DISARM))
```

### Event payload schemas

```typescript
type ScheduleFiredEvent = {
  schedule_id: string;
  schedule_name: string;
  action: "arm" | "disarm";
  target_mode: "home" | "standby";
  fired_at: string;  // ISO-8601 UTC
};
type ScheduleSkippedEvent = {
  schedule_id: string;
  schedule_name: string;
  action: "arm" | "disarm";
  reason:
    | "away_active"
    | "already_home"
    | "panel_unavailable"
    | "manual_override"
    | "reconcile_window_elapsed"
    | "reconcile_panel_not_home";
  skipped_at: string;
};
type ScheduleFailedEvent = {
  schedule_id: string;
  schedule_name: string;
  action: "arm" | "disarm";
  error: string;  // truncated to 200 chars
  attempts: number;  // = 4 (1 initial + 3 retries) for current policy
  failed_at: string;
};
```

These match the TypeScript types Phase 4 will use to render schedule history (if any) — keep them in sync.

### Concurrency safety

- `ScheduleManager` is a singleton per config entry. All methods run on the HA event loop. No locking needed.
- `async_arm` for two pairs simultaneously fires two concurrent `mode_changer.async_set_mode` calls. The alarm_control_panel layer handles the underlying serialization. If both succeed (same target = "home"), the second is a no-op from the panel's perspective.
- The state-change listener and `async_arm`/`async_disarm` may both touch the same pair's `last_*_at` fields. Since all run on the single event loop, ordering is deterministic but interleaved. The semantics are: whoever sets `last_disarmed_at` last "wins" — this is correct because both paths intend to close the window.

### What this phase explicitly does NOT include

- ❌ No frontend changes — Phase 4.
- ❌ No catch-up of missed arms — `async_track_time_change` doesn't backfill, and reconciliation only touches pairs that ALREADY armed before HA went down.
- ❌ No "preview next fire time" computation — Phase 4 derives this client-side.
- ❌ No bulk operations (enable-all, disable-all) — Phase 4 may add these in the UI; this phase ignores them.

## Constraints

- **Conservative defaults**: when in doubt at evaluation time, **do not call `mode_changer`**. The top-named risk is "unexpected arming/disarming during ambiguous states". Every code path that could potentially fire a panel state change must have an explicit, tested justification.
- **Source-of-truth for panel state**: always route through `self._panel_state()` (which wraps `hass.states.get(panel_entity_id).state` and re-resolves the entity each call). Never cache, and never call `hass.states.get(...)` for the panel directly from `async_arm`/`async_disarm`/the listener/reconciliation — the helper is the single read path.
- **Pair state authority**: always derived from `last_armed_at` + `last_disarmed_at` + clock + mode. No separate `state` field anywhere.
- **Persist before firing events**: order of operations in arm/disarm is (1) call `mode_changer`, (2) on success, mutate pair and persist, (3) fire event. Never the other way around — if the persistence step fails, the event would be misleading.
- **Idempotency**: `async_disarm` called twice in a row must produce at most one panel change (the second sees `derive_state == IDLE`).
- **Listener defensiveness**: the state-change listener must handle `old_state=None`, `new_state=None`, and unknown `event.context` gracefully.
- **DST**: `async_track_time_change` is the source of truth for "next 22:00 in HA's timezone". Document, do not hand-roll.
- **Tests must mock time deterministically** via HA's `async_fire_time_changed` + `freezegun` for `clock.utcnow()` when needed. No `time.sleep`, no real wall-clock waits.
- **Retry total attempts**: 1 initial + 3 retries = 4 calls maximum. Delays: 1s, 4s, 16s (between attempts 1-2, 2-3, 3-4). Verify in tests.
