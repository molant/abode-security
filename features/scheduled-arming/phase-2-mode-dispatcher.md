---
status: pending
---

# Phase 2: Mode dispatcher + scheduler clock

Extract the mode-change call into a typed `ModeChanger` boundary, introduce a `Clock` and `ScheduleClock` protocol around `async_track_time_change`, and refactor `websocket_modes_set` to use the new helper. Source-tagging via HA `Context.id` is implemented here so Phase 3 can detect manual mid-window mode changes.

After this phase, **mode switching from the UI still works exactly as before** — the change is purely internal plumbing. No schedule fires yet (Phase 3).

## Context

Phase 1 established storage and CRUD. Phase 3 will need to:

1. Call `_set_mode` from the schedule manager (must distinguish schedule-initiated vs user calls).
2. Register timers via `async_track_time_change` (must be mockable in tests).
3. Read `now()` (must be mockable for reconciliation tests).

This phase extracts those three boundaries into protocols so Phase 3 is testable without HA. The protocols are tiny (one method each); the only production impls call HA directly. This matches the Clean Architecture choice the user picked.

Read [./README.md](./README.md) — especially **Change source**, **Mode dispatch**, and **Retry policy**.

## Structure

```
custom_components/abode_security/
  scheduling/
    clock.py                     # new: Clock protocol + HAClock impl
    scheduler.py                 # new: ScheduleClock protocol + HAScheduleClock impl
    mode_changer.py              # new: ModeChanger protocol + HAModeChanger impl
  websocket_api.py               # update: refactor websocket_modes_set to delegate to HAModeChanger
  __init__.py                    # update: instantiate Clock, ScheduleClock, ModeChanger; inject into ScheduleManager
  const.py                       # update: CONTEXT_ID_PREFIX = "abode_sched_"
tests/
  test_clock.py                  # new: HAClock returns local-tz datetime
  test_scheduler.py              # new: ScheduleClock register/cancel with fake HA time
  test_mode_changer.py           # new: HAModeChanger stamps Context, calls right service
  test_websocket_api.py          # update: existing modes/set tests still pass; add Context-id assertion
```

## Implementation Checklist

### Baseline Test Verification

- [ ] `uv run pytest -m ""` — all tests pass.
- [ ] `./scripts/check.sh` — green.
- [ ] Existing `tests/test_websocket_api.py` modes/set tests pass — they will be the regression net for the refactor.

### Sub-Phase A: Clock protocol (`scheduling/clock.py`)

Deployable unit: a 30-line module wrapping `dt_util.now()` for tz-aware "now" queries. Other code may already call `dt_util.now()` — that stays untouched.

#### Implementation

- [ ] Create `scheduling/clock.py`:
  ```python
  from typing import Protocol
  from datetime import datetime
  from homeassistant.util import dt as dt_util

  class Clock(Protocol):
      def now(self) -> datetime: ...  # tz-aware, in HA timezone
      def utcnow(self) -> datetime: ...  # tz-aware UTC

  class HAClock:
      def __init__(self, hass) -> None:
          self._hass = hass
      def now(self) -> datetime:
          return dt_util.now()
      def utcnow(self) -> datetime:
          return dt_util.utcnow()
  ```
- [ ] Export `Clock` and `HAClock` from `scheduling/__init__.py`.

#### Tests

- [ ] `tests/test_clock.py`:
  - `HAClock(hass).now()` returns aware datetime in `hass.config.time_zone`.
  - `HAClock(hass).utcnow()` returns aware UTC datetime.
  - Both methods return values within 1s of each other when called back-to-back (sanity).

### Sub-Phase B: ScheduleClock protocol (`scheduling/scheduler.py`)

Deployable unit: a thin wrapper around `async_track_time_change` that returns a cancel handle and lets tests register fake handles.

#### Implementation

- [ ] Create `scheduling/scheduler.py`:
  ```python
  from typing import Protocol, Callable, Awaitable
  from homeassistant.helpers.event import async_track_time_change
  from homeassistant.core import HomeAssistant, CALLBACK_TYPE

  CancelHandle = CALLBACK_TYPE  # alias for clarity

  class ScheduleClock(Protocol):
      def async_track_daily(
          self,
          callback: Callable[[], Awaitable[None]],
          *,
          hour: int,
          minute: int,
          weekdays: frozenset[int],  # ISO 0=Mon
      ) -> CancelHandle: ...
      # weekdays is a hint; production impl filters inside the callback because
      # async_track_time_change has no weekday param.

  class HAScheduleClock:
      def __init__(self, hass: HomeAssistant) -> None:
          self._hass = hass
      def async_track_daily(self, callback, *, hour, minute, weekdays):
          async def _wrapper(fire_time):
              # datetime.weekday(): Monday=0..Sunday=6 (Python stdlib, matches our WEEKDAYS tuple order).
              if fire_time.weekday() in weekdays:
                  await callback()
          return async_track_time_change(self._hass, _wrapper, hour=hour, minute=minute, second=0)
  ```
- [ ] Verify HA `async_track_time_change` calls the callback in local tz (it does — see HA source). Document this in a comment because it's the crux of "wall-clock local" semantics from the README.
- [ ] Export `ScheduleClock`, `HAScheduleClock`, `CancelHandle` from `scheduling/__init__.py`.

#### Tests

- [ ] `tests/test_scheduler.py` (use HA's `async_fire_time_changed` from `pytest_homeassistant_custom_component`):
  - Register a daily 22:00 Mon-only callback. Advance HA time to a Monday 22:00 → callback fires.
  - Advance to a Tuesday 22:00 → callback does NOT fire.
  - Cancel the handle → subsequent 22:00 ticks don't fire.
  - DST forward (e.g. spring 2026 in `Europe/Madrid`): a 02:30 daily callback skipped that day (no 02:30 exists) is acceptable; document the behavior in the test name. **Do not** invent retroactive firing.
  - DST backward: a 01:30 daily callback fires once (HA's behavior). Document.

### Sub-Phase C: ModeChanger (`scheduling/mode_changer.py`)

Deployable unit: a single typed boundary around the existing `hass.services.async_call("alarm_control_panel", ...)` call. Stamps HA `Context.id` for source attribution.

#### Implementation

- [ ] In `const.py` add:
  ```python
  CONTEXT_ID_PREFIX = "abode_sched_"
  ```
- [ ] Create `scheduling/mode_changer.py`:
  ```python
  from typing import Protocol
  from homeassistant.core import Context, HomeAssistant
  from homeassistant.exceptions import HomeAssistantError, ServiceNotFound
  from .models import ChangeSource

  MODE_TO_SERVICE = {"standby": "alarm_disarm", "home": "alarm_arm_home", "away": "alarm_arm_away"}
  VALID_MODES = frozenset(MODE_TO_SERVICE)

  class ModeChangeFailed(HomeAssistantError):
      """Raised when the underlying alarm_control_panel service call fails."""

  class ModeChanger(Protocol):
      async def async_set_mode(
          self,
          target: str,
          source: ChangeSource,
          *,
          pair_id: str | None = None,
      ) -> None: ...

  class HAModeChanger:
      def __init__(self, hass: HomeAssistant) -> None:
          self._hass = hass

      def _build_context(self, source: ChangeSource, pair_id: str | None) -> Context | None:
          if source in (ChangeSource.SCHEDULE_ARM, ChangeSource.SCHEDULE_DISARM, ChangeSource.RECONCILE_DISARM):
              if pair_id is None:
                  raise ValueError(f"pair_id required for {source}")
              from .const import CONTEXT_ID_PREFIX
              import uuid
              return Context(id=f"{CONTEXT_ID_PREFIX}{pair_id}_{uuid.uuid4().hex[:8]}")
          return None  # USER_WS gets default Context()

      async def async_set_mode(self, target, source, *, pair_id=None):
          if target not in VALID_MODES:
              raise ValueError(f"Invalid mode: {target}")
          panel_state = find_abode_alarm_panel(self._hass)  # import from websocket_api or move helper
          if panel_state is None:
              raise ModeChangeFailed("No Abode alarm_control_panel entity registered")
          ctx = self._build_context(source, pair_id)
          try:
              await self._hass.services.async_call(
                  "alarm_control_panel",
                  MODE_TO_SERVICE[target],
                  {"entity_id": panel_state.entity_id},
                  blocking=True,
                  context=ctx,
              )
          except (HomeAssistantError, ServiceNotFound, ValueError) as err:
              raise ModeChangeFailed(str(err)) from err
  ```
- [ ] **Use the existing `find_abode_alarm_panel` helper** at `custom_components/abode_security/helpers.py:11`. Import via `from .helpers import find_abode_alarm_panel` (same import used today by `websocket_api.py:29` and `action_trigger.py`). Do NOT move it, do NOT duplicate it, do NOT re-implement.

#### Refactor `websocket_modes_set`

- [ ] In `websocket_api.py`, modify `websocket_modes_set` to delegate to `HAModeChanger`:
  ```python
  async def websocket_modes_set(hass, connection, msg):
      mode_id = msg["mode_id"]
      mode_changer = _get_mode_changer(hass)  # from hass.data[DOMAIN]
      try:
          await mode_changer.async_set_mode(mode_id, ChangeSource.USER_WS)
      except ValueError as err:
          connection.send_error(msg["id"], "validation_error", str(err))
          return
      except ModeChangeFailed as err:
          _LOGGER.warning("Failed to set mode %s: %s", mode_id, err)
          connection.send_error(msg["id"], "set_mode_failed", str(err))
          return
      _LOGGER.info("Mode set to %s by user %s", mode_id, connection.user.id)
      connection.send_result(msg["id"], {"success": True, "mode_id": mode_id})
  ```
- [ ] Old inline `hass.services.async_call(...)` call **must be removed** — `HAModeChanger` is the single mode-change call site. Reviewers should grep `alarm_control_panel.*alarm_(arm|disarm)` and find only one production hit.

#### Wiring

- [ ] In `__init__.py` (`async_setup_entry`), construct: `HAClock(hass)`, `HAScheduleClock(hass)`, `HAModeChanger(hass)`. Stash on `hass.data[DOMAIN]["clock"]`, `hass.data[DOMAIN]["schedule_clock"]`, `hass.data[DOMAIN]["mode_changer"]` — **domain-scoped, not entry-scoped**, matching the precedent at `__init__.py:218-231` (and the Phase 1 fix). Pop them in `async_unload_entry` next to the existing cleanup block.
- [ ] Update `ScheduleManager.__init__` signature (from Phase 1) to accept `clock: Clock`, `scheduler_clock: ScheduleClock`, `mode_changer: ModeChanger`. Store as attributes. **`clock` is used in this phase**: `async_create` (and `_validate`) need `clock.utcnow()` to stamp `created_at` — switch the Phase 1 implementation from a direct `dt_util.utcnow()` call to `self._clock.utcnow()` so tests can inject a fake clock. The other two attributes (`scheduler_clock`, `mode_changer`) stay unused until Phase 3.

#### Tests

- [ ] `tests/test_mode_changer.py`:
  - `async_set_mode("home", USER_WS)` calls `alarm_control_panel.alarm_arm_home` with `context=None` (default Context).
  - `async_set_mode("home", SCHEDULE_ARM, pair_id="abc-123")` calls the same service with `context.id` starting with `"abode_sched_abc-123_"`.
  - `async_set_mode("home", SCHEDULE_ARM)` (missing pair_id) → `ValueError`.
  - `async_set_mode("invalid", USER_WS)` → `ValueError`.
  - When alarm panel entity is missing → `ModeChangeFailed`.
  - When `hass.services.async_call` raises `HomeAssistantError` → `ModeChangeFailed` wraps it.
- [ ] Update `tests/test_websocket_api.py`:
  - Existing `modes/set` tests still pass — this is the regression net.
  - Add one assertion: when `modes/set` is called from a WS client, the resulting service call's `context.id` does **not** start with `CONTEXT_ID_PREFIX`. (Listen via `async_track_state_change_event` or capture via `hass.services.async_call` spy.)

### Documentation (End of Phase)

- [ ] `docs/ARCHITECTURE.md` — under the "Schedule scheduling subsystem" section added in Phase 1, add the Clock / ScheduleClock / ModeChanger protocols and their HA impls. Note the Context-id source-tagging convention.
- [ ] `docs/ASYNC_AWAIT_PATTERNS.md` — if it documents service-call patterns, add a note that all alarm-mode changes route through `HAModeChanger`.

### Build Verification

- [ ] `uv run ruff check .` — zero issues.
- [ ] `uv run mypy custom_components` — zero errors. Protocol classes type-check correctly.
- [ ] `uv run pyright` — zero errors.
- [ ] `uv run pytest -m ""` — all tests pass.
- [ ] Scan output for warnings/errors/uncaught exceptions even when exit code is 0.
- [ ] Existing modes/set behavior unchanged: deploy to dev HA via `./scripts/dev.sh`, verify the Modes tab still switches modes correctly (manual smoke test).
- [ ] `grep -rn "alarm_control_panel" custom_components/abode_security/` — exactly one production hit (in `mode_changer.py`), excluding constants and comments.

### Manual Verification with MCP Tools

- [ ] Use `mcp__home-assistant__ha_call_service` to call `alarm_control_panel.alarm_arm_home` directly against the dev HA — confirms baseline service call still works.
- [ ] Use the Modes tab in the browser at http://localhost:8123/abode_security — switch modes manually, verify state changes propagate. (E2E suite is the canonical check; this is a sanity smoke.)
- [ ] Use `mcp__home-assistant__ha_get_logs` to confirm logs show `Mode set to <mode> by user <id>` lines as before.

## Technical Details

### Context-id naming convention

```
abode_sched_<pair_id>_<8-hex-nonce>
```

Example: `abode_sched_1a2b3c4d-5e6f-7890-abcd-ef0123456789_a1b2c3d4`

The nonce is required because the same pair fires twice per window (arm + disarm), and two consecutive transitions with the same context id would be ambiguous to the state-change listener in Phase 3.

### Protocol type signatures (frozen for Phase 3)

```python
class Clock(Protocol):
    def now(self) -> datetime: ...
    def utcnow(self) -> datetime: ...

class ScheduleClock(Protocol):
    def async_track_daily(
        self,
        callback: Callable[[], Awaitable[None]],
        *,
        hour: int,
        minute: int,
        weekdays: frozenset[int],
    ) -> CancelHandle: ...

class ModeChanger(Protocol):
    async def async_set_mode(
        self,
        target: str,
        source: ChangeSource,
        *,
        pair_id: str | None = None,
    ) -> None: ...
```

Phase 3 will consume exactly this surface. Do not widen.

### What this phase explicitly does NOT include

- ❌ No timer registration logic — Phase 3.
- ❌ No `async_arm`, `async_disarm` on `ScheduleManager` — Phase 3.
- ❌ No event firing — Phase 3.
- ❌ No retry helper — Phase 3.
- ❌ No reconciliation — Phase 3.
- ❌ No state-change listener for manual-override detection — Phase 3 (the Context-id stamping is in place, but the listener is not).
- ❌ No frontend — Phase 4.

## Constraints

- After this phase, exactly **one** production code path may call `hass.services.async_call("alarm_control_panel", ...)`: `HAModeChanger.async_set_mode`. Grep enforces this.
- `Clock` and `ScheduleClock` must be `typing.Protocol` (not abstract base classes). Tests pass plain objects with matching methods (duck typing); no `@runtime_checkable` decorator is needed unless we use `isinstance` checks at runtime (we don't).
- `HAClock` and `HAScheduleClock` must hold a reference to `hass` and be safe to instantiate during `async_setup_entry`.
- The `ScheduleManager` constructor signature widens to accept `clock`, `scheduler_clock`, `mode_changer` — these MUST be stored unused in this phase (Phase 3 consumes them). This is a deliberate dependency injection step, not premature use.
- DST handling: documented as "HA's `async_track_time_change` skips non-existent local times on spring-forward and fires once on fall-back". Don't try to outsmart this — surface the behavior in tests and accept it.
