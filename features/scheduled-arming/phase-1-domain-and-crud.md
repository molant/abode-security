---
status: done
---

# Phase 1: Domain & CRUD

Establish the domain types (`ScheduledPair`, `ChangeSource`, `SkipReason`), persistent storage (`SchedulesStore`) with corruption repair, and admin-gated WebSocket CRUD endpoints. After this phase, schedules can be created, listed, updated, deleted, and survive HA restarts — but **nothing fires them yet**. The runtime arrives in Phase 3.

## Context

This phase mirrors the existing `action_manager.py` precedent line-for-line so future readers see two parallel patterns. Storage lives at `.storage/abode_security_schedules.json`. WS endpoints follow the exact shape of the actions CRUD handlers in `websocket_api.py`.

No mode-change logic, no timer registration, no UI in this phase. The manager class introduced here exposes only CRUD + a `__contains__` style API; the runtime methods (`async_arm`, `async_disarm`, reconciliation) arrive in Phase 3 as additions to the same class.

Read [./README.md](./README.md) for overall feature context, especially the **Schedule pair**, **Overnight window**, and **Validation rules** sections.

## Structure

```
custom_components/abode_security/
  scheduling/
    __init__.py                  # new: package marker, exports public API
    models.py                    # new: ScheduledPair, ChangeSource enum, SkipReason enum
    store.py                     # new: SchedulesStore (HA Store wrapper + repair issue)
    manager.py                   # new: ScheduleManager CRUD (runtime methods deferred to Phase 3)
    repair.py                    # new: repair-issue helpers (corrupt_schedule_records)
  websocket_schedules.py         # new: 5 WS commands (list/get/create/update/delete)
  __init__.py                    # update: instantiate ScheduleManager, async_load on setup, store in hass.data[DOMAIN]
  websocket_api.py               # update: register schedules/* commands (re-export from websocket_schedules)
  const.py                       # update: STORAGE_KEY_SCHEDULES, REPAIR_ISSUE_CORRUPT_SCHEDULES, MAX_SCHEDULE_NAME_LENGTH
  strings.json                   # update: new repair issue translation entry
tests/
  test_schedule_models.py        # new: ScheduledPair to_dict/from_dict, validation
  test_schedule_store.py         # new: Store load/save, corruption repair, per-record drop
  test_schedule_manager.py       # new: CRUD, validation errors, manager dependency-injection wiring
  test_websocket_schedules.py    # new: WS handler tests (admin gating, schema validation, error codes)
```

## Implementation Checklist

> **Remember**: Update these checkboxes as you complete each task.

### Baseline Test Verification (before starting implementation)

- [ ] Run the full test suite: `uv run pytest -m ""` — all tests must pass.
- [ ] Run lint + types: `uv run ruff check . && uv run mypy custom_components && uv run pyright`.
- [ ] Run `cd frontend && npm test` — frontend tests pass.
- [ ] If anything is failing, fix it in a separate commit before starting this phase.

### Sub-Phase A: Domain models (`scheduling/models.py`)

Deployable unit: pure Python types that round-trip through JSON. No HA dependencies in this module (except `homeassistant.util.dt` for tz handling, which is permitted).

#### Types

- [ ] Create `custom_components/abode_security/scheduling/__init__.py` exporting the public API: `ScheduledPair`, `ChangeSource`, `SkipReason` (re-export from submodules).
- [ ] Create `custom_components/abode_security/scheduling/models.py` with:
  - `WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")` constant tuple (ISO order, Mon=0).
  - `class ChangeSource(StrEnum)`: `USER_WS = "user_ws"`, `SCHEDULE_ARM = "schedule_arm"`, `SCHEDULE_DISARM = "schedule_disarm"`, `RECONCILE_DISARM = "reconcile_disarm"`.
  - `class SkipReason(StrEnum)`: `AWAY_ACTIVE = "away_active"`, `ALREADY_HOME = "already_home"`, `PANEL_UNAVAILABLE = "panel_unavailable"`, `MANUAL_OVERRIDE = "manual_override"`, `RECONCILE_WINDOW_ELAPSED = "reconcile_window_elapsed"`, `RECONCILE_PANEL_NOT_HOME = "reconcile_panel_not_home"`. (Closed set — keep in sync with README "Skip reasons" and the Phase 3 event-payload TypeScript schema.)
  - `@dataclass class ScheduledPair` with fields as defined in README. Use `datetime | None` for nullable timestamps, `datetime` (non-null) for `created_at`, `list[str]` for weekdays, `str` (default `""`) for `name`. Default `enabled=True`, `last_armed_at=None`, `last_disarmed_at=None`, `last_skip_reason=None`, `last_error=None`. `created_at` has no default — it is set by the manager at `async_create` time using `clock.utcnow()` and is immutable thereafter. **No `__post_init__` validation** — validation lives in the manager (mirrors action_manager). `to_dict()` and `from_dict()` follow the action_manager pattern: ISO-format datetimes, per-field validation in `from_dict`, raise `ValueError` on bad records.
  - Helper: `is_overnight(pair) -> bool` returning `arm_time >= disarm_time`.
  - Helper: `weekday_index(name: str) -> int` and `weekday_name(idx: int) -> str` for ISO conversions.

#### Tests

- [ ] `tests/test_schedule_models.py`:
  - `ScheduledPair` round-trips through `to_dict`/`from_dict` with all field combinations (including with and without `name`, with and without `last_*_at` timestamps).
  - `created_at` round-trips as ISO-8601 UTC with timezone info preserved.
  - `from_dict` raises `ValueError` on: missing id, missing created_at, name > 100 chars, name not a string, weekdays not list, weekdays empty, weekdays with unknown name, weekdays with duplicates, arm_time not regex match, disarm_time not regex match, arm_time == disarm_time, enabled not bool (use the explicit `isinstance(enabled, bool)` check, mirroring `action_manager.py:119`), unknown extra field.
  - `from_dict` accepts a missing `name` key and treats it as `""` (name is optional per README).
  - `is_overnight` returns true for `arm="22:00", disarm="06:00"`, false for `arm="08:00", disarm="17:00"`.
  - `ChangeSource` and `SkipReason` are `StrEnum` (string equality with their values).

### Sub-Phase B: Storage (`scheduling/store.py`) + repair (`scheduling/repair.py`)

Deployable unit: persistent storage that loads/saves schedules, mirrors `ActionStore` behavior for corruption handling.

#### Constants

- [ ] In `const.py` add:
  ```python
  STORAGE_KEY_SCHEDULES = "abode_security_schedules"
  STORAGE_VERSION_SCHEDULES = 1
  REPAIR_ISSUE_CORRUPT_SCHEDULES = "corrupt_schedule_records"
  MAX_SCHEDULE_NAME_LENGTH = 100
  MAX_SCHEDULES = 50  # sanity cap; UI optimizes for 1–10
  ```
- [ ] In `strings.json` add an `issues.corrupt_schedule_records` entry mirroring `corrupt_action_records`: `title` + `description` with `{count}` placeholder.

#### Repair helper

- [ ] Create `scheduling/repair.py` with two helpers:
  - `async_raise_corrupt_issue(hass, count: int | None)` — wraps `homeassistant.helpers.issue_registry.async_create_issue` mirroring the `ActionStore._raise_corrupt_issue` call at `action_manager.py:263-273`: `is_fixable=False`, `severity=ir.IssueSeverity.ERROR`, `translation_key=REPAIR_ISSUE_CORRUPT_SCHEDULES`, `translation_placeholders={"count": str(count) if count is not None else "unknown"}`. `count=None` indicates whole-file corruption (rendered as `"unknown"`).
  - `async_clear_corrupt_issue(hass)` — wraps `async_delete_issue`. Called on every clean load.

#### Store

- [ ] Create `scheduling/store.py` with `class SchedulesStore`:
  - `__init__(hass)` — `self._store = Store(hass, STORAGE_VERSION_SCHEDULES, STORAGE_KEY_SCHEDULES)`, `self._schedules: dict[str, ScheduledPair] = {}`.
  - `async_load()` — load data, iterate records, call `ScheduledPair.from_dict()` on each, count drops, raise/clear repair issue. **On whole-file corruption** (root not dict or `"schedules"` key not dict): keep `_schedules` empty, raise repair issue with `count=None`.
  - `async_save()` — wrap as `{"schedules": {id: pair.to_dict() for id, pair in self._schedules.items()}}`.
  - `async_add(pair)`, `async_update(pair)`, `async_remove(pair_id) -> bool`, `get(pair_id) -> ScheduledPair | None`, `get_all() -> list[ScheduledPair]`.
  - Save behavior: **mirror `action_manager.py:275-299` exactly** — each mutation calls a synchronous `async_save()` that wraps `await self._store.async_save(data)`. The existing precedent does NOT use `async_delay_save` despite HA convention; stay consistent with that file so reviewers can diff side-by-side. (If you want debouncing, file a follow-up; do not introduce it asymmetrically here.)

#### Tests

- [ ] `tests/test_schedule_store.py`:
  - Save → reload → state preserved.
  - Whole-file corruption (root is a list) → empty store + repair issue raised with `count=None`.
  - Per-record corruption (one bad record in a 3-record file) → 2 records loaded, repair issue raised with `count=1`.
  - Clean load after corrupt load → repair issue deleted.
  - `MAX_SCHEDULES` cap enforced in `async_add` — raises `ValueError`.
  - Cap edge: at exactly `MAX_SCHEDULES`, the next `async_add` raises; updating an existing record at capacity succeeds.

### Sub-Phase C: Manager CRUD (`scheduling/manager.py`)

Deployable unit: validated CRUD over the store with the public API the WS layer needs. Runtime methods (`async_arm`, `async_disarm`, `async_reconcile_on_startup`) are **not** in this sub-phase — they arrive in Phase 3 as additions to the same class.

#### Manager skeleton

- [ ] Create `scheduling/manager.py` with `class ScheduleManager`:
  - `__init__(hass, store: SchedulesStore)` — store injection (DI pattern; tests pass an in-memory fake). **Phase 2 widens this signature** to also accept `clock`, `scheduler_clock`, `mode_changer`; this phase only needs `hass` and `store`, but implementers should anticipate the widening (don't construct the manager in a way that resists it).
  - `async_setup()` — `await store.async_load()`. **No timers are registered in this phase** (Phase 3 adds the timer-registration loop).
  - `async_shutdown()` — no-op in this phase (Phase 3 cancels timers).
  - `async_create(*, name="", weekdays, arm_time, disarm_time, enabled=True) -> ScheduledPair` — generates UUID, stamps `created_at` with `dt_util.utcnow()` (Phase 2 will switch this to the injected `Clock.utcnow()` once the manager accepts a clock), validates via `_validate(pair)`, calls `store.async_add`, returns pair. `name` defaults to `""` (optional per README).
  - `async_update(pair_id, **kwargs) -> ScheduledPair | None` — fetch, apply partial update (only the writable subset: `name, weekdays, arm_time, disarm_time, enabled`), re-validate, persist. Raise `ValueError` on validation failure.
  - `async_delete(pair_id) -> bool` — delegates to store.
  - `async_get(pair_id) -> ScheduledPair | None`, `async_get_all() -> list[ScheduledPair]`.
  - `_validate(pair)` — applies the validation rules from README (name length, weekdays subset/non-empty/no-dupes, time regex, `arm != disarm`).
  - **Runtime hooks reserved for Phase 3**: leave a comment block listing `async_arm`, `async_disarm`, `async_reconcile_on_startup`, `async_handle_manual_change(new_state)` as "added in Phase 3". Do not implement.

#### Wiring

- [ ] In `__init__.py`, in `async_setup_entry` (next to where `ActionManager` is instantiated — currently around `__init__.py:218`):
  - Construct `SchedulesStore(hass)` and `ScheduleManager(hass, store)`.
  - `await manager.async_setup()`.
  - Stash on `hass.data[DOMAIN]["schedule_manager"]` — **domain-scoped, not entry-scoped**, mirroring `hass.data[DOMAIN]["action_manager"]` at `__init__.py:220`. The comment block at `__init__.py:206-211` explains why (single-config-entry guarantee). Do not introduce an entry-scoped key here.
  - In `async_unload_entry` (around `__init__.py:321-328`), add `await manager.async_shutdown()` and `hass.data[DOMAIN].pop("schedule_manager", None)` alongside the existing `action_manager` cleanup.

#### Tests

- [ ] `tests/test_schedule_manager.py`:
  - Create → returns `ScheduledPair` with generated UUID.
  - Create + validation fails → raises `ValueError` with specific message; nothing persisted.
  - Update with valid partial → re-validates, persists.
  - Update with invalid partial → raises `ValueError`; previous state preserved.
  - Delete returns `True` for existing, `False` for unknown.
  - Cap: 50th create succeeds, 51st raises `ValueError`.
  - Concurrency: two simultaneous creates yield two distinct UUIDs (not a real race test, just covers branch).

### Sub-Phase D: WebSocket endpoints (`websocket_schedules.py`)

Deployable unit: admin-gated CRUD endpoints. After this sub-phase, the feature is exercisable from a websocket client (or integration tests) end-to-end **for storage** — firing still doesn't happen.

#### Schemas (use `voluptuous` as in `websocket_api.py`)

- [ ] `schedules/list` — no extra fields; returns `{"schedules": [pair.to_dict(), ...]}` sorted ascending by `created_at` (stable order).
- [ ] `schedules/get` — `id: str`; returns the pair dict, or `not_found` error.
- [ ] `schedules/create` — `name: str (≤100, default "")`, `weekdays: list[str] (1–7, In(WEEKDAYS))`, `arm_time: str (regex)`, `disarm_time: str (regex)`, `enabled: bool (default True)`. Mirror the `_non_bool_int` pattern from `websocket_api.py:165` as `_non_bool_bool`.
- [ ] `schedules/update` — `id: str` + all create fields optional. At least one mutable field required (otherwise return `validation_error`).
- [ ] `schedules/delete` — `id: str`; returns `{"success": True, "id": ...}` or `not_found`.

#### Handler structure

- [ ] Create `websocket_schedules.py` with one handler per command.
- [ ] Each handler: `@websocket_command({...})`, `@require_admin` (except list/get), `@async_response`.
- [ ] On `ValueError`: `connection.send_error(msg["id"], "validation_error", str(err))`.
- [ ] On `not_found`: `connection.send_error(msg["id"], "not_found", "...")`.
- [ ] On success: `connection.send_result(msg["id"], pair.to_dict() or {...})`.
- [ ] `_get_schedule_manager(hass)` helper returns `None` if not initialized → `not_ready` error.
- [ ] In `websocket_api.py`, inside the existing `async_register_websocket_commands(hass)` function (defined at `websocket_api.py:188`), add five `websocket_api.async_register_command(hass, websocket_schedules_<verb>)` calls alongside the existing block (`websocket_api.py:217-233`). Import the handlers from the new `websocket_schedules` module at the top of `websocket_api.py`.

#### Tests

- [ ] `tests/test_websocket_schedules.py` (use `hass_ws_client` fixture from `pytest_homeassistant_custom_component`):
  - `schedules/list` empty → `{"schedules": []}`.
  - `schedules/list` after creating two pairs → returns both, sorted ascending by `created_at` (the earliest-created pair is first); order is stable across repeated calls.
  - `schedules/create` happy path → returns full pair dict; verify persisted via second list call.
  - `schedules/create` non-admin → `unauthorized` error (HA core's `@require_admin` enforces; see `tests/test_websocket_api.py:709-715` for the fixture pattern).
  - `schedules/create` with weekdays=[] → `validation_error`.
  - `schedules/create` with arm_time=="22:00", disarm_time=="22:00" → `validation_error`.
  - `schedules/update` partial (only `name`) → succeeds, other fields preserved.
  - `schedules/update` with only `id` (no mutable fields) → `validation_error`.
  - `schedules/update` of unknown id → `not_found`.
  - `schedules/delete` happy path → success; second delete → `not_found`.
  - Admin gating verified by `schedules/create` from non-admin user fixture.

### Documentation (End of Phase)

- [ ] `docs/ARCHITECTURE.md` — add a short "Schedule scheduling subsystem" section under "Outer integration layer" (1–2 paragraphs + 1 Mermaid update showing `scheduling/` package). Mention `ScheduleManager` is the public entry point and that runtime arrives in Phase 3.
- [ ] `CLAUDE.md` — no change in this phase (commands unchanged).

### Build Verification (required before marking phase complete)

- [ ] `uv run ruff check .` — zero issues.
- [ ] `uv run mypy custom_components` — zero errors.
- [ ] `uv run pyright` — zero errors.
- [ ] `uv run pytest -m ""` — all tests pass.
- [ ] Scan pytest output for `WARNING` / `ERROR` lines and uncaught exception tracebacks even though exit code is 0.
- [ ] Frontend untouched in this phase → `cd frontend && npm test` still passes.
- [ ] `./scripts/check.sh` — green.
- [ ] Storage migration check: deploy to dev HA via `./scripts/dev.sh`, verify `.storage/abode_security_schedules.json` is created on first WS `schedules/create` and is loaded on container restart.
- [ ] Mark phase `status: done` only after all verification steps pass.

### Manual Verification with MCP Tools

After unit tests pass, use the home-assistant MCP to exercise WS endpoints against the dev stack:

- [ ] Use `mcp__home-assistant__ha_get_logs` to confirm no errors during integration setup.
- [ ] Use a WS-capable HTTP client (or write a quick integration test) to create a schedule, list it, update it, delete it. Verify storage file at `.storage/abode_security_schedules.json` mutates accordingly.
- [ ] Manually corrupt the storage file (replace contents with `[1,2,3]`), restart HA, verify a repair issue surfaces in the UI at http://localhost:8123/config/repairs.

## Technical Details

### `ScheduledPair` JSON shape (storage + WS DTOs)

```json
{
  "id": "1a2b3c4d-...",
  "name": "Weeknights",
  "weekdays": ["mon", "tue", "wed", "thu", "fri"],
  "arm_time": "22:00",
  "disarm_time": "06:00",
  "enabled": true,
  "created_at": "2026-05-26T21:59:00.000000+00:00",
  "last_armed_at": "2026-05-26T22:00:01.234567+00:00",
  "last_disarmed_at": "2026-05-27T06:00:00.123456+00:00",
  "last_skip_reason": null,
  "last_error": null
}
```

### WS error codes used in this phase

| Code | When |
|---|---|
| `not_ready` | `ScheduleManager` not yet initialized (integration still loading) |
| `not_found` | `id` not in store |
| `validation_error` | Voluptuous schema failure, or `ValueError` raised by manager |
| `unauthorized` | (HA core) non-admin caller hit an admin-only endpoint |

### What this phase explicitly does NOT include

To prevent shortcuts (the implementer should NOT silently expand scope):

- ❌ No `async_arm`, `async_disarm`, `async_reconcile_on_startup` implementations on `ScheduleManager` — these are Phase 3.
- ❌ No `async_track_time_change` registrations — Phase 3.
- ❌ No HA event firing — Phase 3.
- ❌ No `mode_changer.py`, `clock.py`, `scheduler.py`, `state_machine.py`, `retry.py` — those are Phase 2 / 3.
- ❌ No frontend changes — Phase 4.
- ❌ No diagnostics.py updates yet — Phase 3 will surface fired/skipped counts.

## Constraints

- All new Python files must satisfy `ruff`, `mypy`, and `pyright` with zero issues. The project's tool config is in `pyproject.toml`; do not relax it.
- Mirror `action_manager.py` patterns exactly where parallels exist (per-field validation in `from_dict`, repair-issue lifecycle, immediate non-debounced save per the precedent at `action_manager.py:275-299`). Reviewers will compare side-by-side.
- The manager class must be constructed with explicit dependencies (`hass`, `store`) so Phase 3 can inject `Clock`, `ScheduleClock`, `ModeChanger`. Do **not** instantiate dependencies inside `__init__`.
- WS endpoints must reuse the existing `@require_admin` decorator and error-code conventions verbatim.
- `STORAGE_KEY_SCHEDULES` must be `"abode_security_schedules"` (not `"abode_schedules"` or similar) for consistency with `abode_security_actions`.
- Time strings in storage are `HH:MM` 24-hour. Do not allow `HH:MM:SS` (avoid sub-minute schedules — they're confusing and `async_track_time_change` rounds to seconds anyway).
- The dataclass uses `dataclass(slots=True)` if mypy/pyright cope; otherwise plain `@dataclass`. Match action_manager.
