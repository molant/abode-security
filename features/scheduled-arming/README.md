---
status: pending
issue: 142
feature: scheduled-arming
title: Scheduled Arming
phases: 4
---

# Scheduled Arming

> **Progress Tracking**: Update checkboxes in phase files as you complete tasks. Run `/spec-implement features/scheduled-arming/phase-1-domain-and-crud.md` to begin.

## Goal

Let the user configure recurring **Home-mode** schedules (e.g. "arm Home at 22:00, disarm at 06:00, Mon–Fri") from a section under the Modes tab — so they can replace a hand-rolled HA automation with a first-class UI that respects Away as a higher-priority state.

## Concepts

### Schedule pair
One row in the schedules list. Pair fields:

- `id` — UUID, server-generated.
- `name` — optional free-text label (e.g. "Weeknights"). Falls back to a derived summary in the UI when empty. Stored as a string (empty string when omitted), never `null`.
- `weekdays` — non-empty list from `{"mon","tue","wed","thu","fri","sat","sun"}`. ISO ordering (Mon=0…Sun=6) when an integer is needed internally; storage keeps the names.
- `arm_time` — `"HH:MM"` 24-hour, **local wall-clock** in `hass.config.time_zone`.
- `disarm_time` — `"HH:MM"` 24-hour, **local wall-clock**.
- `enabled` — bool. Defaults to `true`. When `false`, neither arm nor disarm fires; the row remains in the list.
- `created_at` — ISO-8601 UTC datetime, server-generated on create. Used as the stable sort key for `schedules/list`. Immutable after create.
- `last_armed_at` — ISO-8601 UTC datetime or `null`. Set when this pair's arm fires successfully, when the arm is skipped via the `already_home` "take ownership" branch, or when the override listener adopts a panel that entered `armed_home` mid-window (#212). Used for restart reconciliation and the disarm-only-if-armed rule.
- `last_disarmed_at` — ISO-8601 UTC datetime or `null`. Set when this pair's disarm fires, when the disarm edge finds the panel already changed (`manual_override`) or not actionable (`panel_unavailable`), when the override listener cancels a pending disarm, or when reconciliation clears it. Never set by a skipped *arm*: that edge disarms nothing (#213).
- `last_skip_reason` — optional short string (one of the `SkipReason` values, see below). UI hint only.
- `last_error` — optional short string. Set after retries are exhausted. UI hint only.

### Overnight window
A pair where `arm_time >= disarm_time` is **overnight**. The `weekdays` list applies to the **arm day**; the disarm fires the next calendar day. Example: `weekdays=["sat"]`, arm 22:00, disarm 06:00 → arm Saturday 22:00, disarm Sunday 06:00.

A pair where `arm_time < disarm_time` is **same-day**. Both fire on each selected weekday.

A pair with `arm_time == disarm_time` is **rejected** at validation time.

### Pair window
The interval from a pair's most recent scheduled arm-fire time to its matching disarm-fire time. Used by restart reconciliation: a pair is "in window" iff `now` lies in this interval.

### Change source
Every mode change has a `ChangeSource`: `USER_WS`, `SCHEDULE_ARM`, `SCHEDULE_DISARM`, `RECONCILE_DISARM`. Propagated through HA `Context.id` using the prefix `abode_sched_<pair_id>_<nonce>` for schedule-initiated changes; user/external changes get a vanilla `Context()` whose id does not start with `abode_sched_`. The runtime listens to `EVENT_STATE_CHANGED` on the alarm panel and filters by this prefix to distinguish self-driven transitions from manual ones (the cancel-pending-disarm rule).

### Skip rule
At arm time, the manager evaluates the **live** alarm panel state via `hass.states.get(panel_entity_id).state`:

- `armed_away` → skip the arm; fire `schedule_skipped` (`reason: "away_active"`); set `last_skip_reason` only — the anchors are left alone, since nothing was armed or disarmed (#213).
- `armed_home` → skip arm (already Home); but mark the pair as armed-by-us **only if no prior arm-by-us is currently pending** (so we don't extend someone else's pair). Pair extension semantics: see Overlapping pairs.
- `disarmed` → arm.
- Intermediate states (`arming`, `pending`, `triggered`, `unavailable`, `unknown`) — or the panel entity is unregistered (`hass.states.get(...)` returns `None`) → skip arm; fire `schedule_skipped` (`reason: "panel_unavailable"`).

The pair's matching disarm fires **only if** that pair set `last_armed_at` for this window. See State machine below.

### Overlapping pairs
Pairs are evaluated independently. Two overlapping pairs each track their own arm/disarm. A pair whose scheduled arm runs while the panel is already `armed_home` still records `last_armed_at = now()` (it "took ownership" for its own disarm), and its scheduled disarm later runs and disarms back to Standby — provided the skip-rule, manual-override, and away-active checks pass at disarm time too.

### State machine
Per-pair derived state (pure function of fields + current panel mode + current time):

```
IDLE             — last_armed_at is null OR last_disarmed_at >= last_armed_at
PENDING_ARM      — IDLE and current_time is within ±5s of next arm fire
ARMED            — last_armed_at > last_disarmed_at and current_time < pair's disarm time
PENDING_DISARM   — ARMED and current_time is within ±5s of disarm fire
```

State is **derived**, not stored. The two timestamps + current mode + clock are the canonical source. See `scheduling/state_machine.py:derive_state`.

### Restart reconciliation
On HA startup, for each enabled schedule with `last_armed_at > last_disarmed_at`:

1. Compute the pair's currently-active window: `[last_armed_at, expected_disarm_at)` where `expected_disarm_at` is the next occurrence of `disarm_time` ≥ `last_armed_at` in the HA timezone (handles overnight + DST).
2. If `now < expected_disarm_at` AND the panel state is `armed_home` → re-register the disarm timer at `expected_disarm_at`.
3. Otherwise (now past window, OR panel no longer Home) → set `last_disarmed_at = now()`, fire **no** disarm, log INFO, persist.

Missed arms are **never** caught up. If HA was offline at the scheduled arm and `last_armed_at` is unchanged, the pair stays IDLE on startup.

### Retry policy
On `ModeChanger.async_set_mode` failure (transient panel error, network blip), retry 3 times with backoff: **1s, 4s, 16s**. Total attempts = **4** (1 initial + 3 retries). After all 4 attempts fail, fire `abode_security.schedule_failed` (with `attempts: 4`), set `last_error` on the pair, and raise an HA repair issue (translation key `schedule_fire_failed`). The retry happens before any event/state mutation — if the call ultimately fails, `last_armed_at` is **not** updated and the pair stays IDLE; its scheduled disarm is also dropped.

### Skip reasons
The `SkipReason` enum (used in `last_skip_reason` and in the `schedule_skipped` event `reason` field) is the closed set:

- `away_active` — panel was `armed_away` at arm time.
- `already_home` — panel found in `armed_home`, either at arm time or when it is manually armed partway through the window (#212). Either way we "take ownership" for disarm.
- `panel_unavailable` — panel in `arming`, `pending`, `triggered`, `unavailable`, `unknown`, or unregistered at evaluation time.
- `manual_override` — panel left `armed_home` via a non-self-driven Context (cancel-pending-disarm rule).
- `reconcile_window_elapsed` — restart reconciliation found the pair's window had already passed.
- `reconcile_panel_not_home` — restart reconciliation found the panel was no longer Home.

## Requirements

### Schedule CRUD (WS API)
- `abode_security/schedules/list` — open to any panel viewer. Returns all schedules, sorted by created_at.
- `abode_security/schedules/get` — open. Returns one schedule by id.
- `abode_security/schedules/create` — admin only. Validates fields. Returns the created schedule.
- `abode_security/schedules/update` — admin only. Partial updates. Re-validates and re-wires timers.
- `abode_security/schedules/delete` — admin only. Cancels pending timers for that pair.

### Validation rules (enforced by manager, surfaced via `validation_error`)
- `name` ≤ 100 chars; whitespace allowed; empty allowed (UI renders summary).
- `weekdays` non-empty subset of the seven names; duplicates rejected.
- `arm_time` and `disarm_time` match `^([01]\d|2[0-3]):[0-5]\d$`.
- `arm_time != disarm_time` (no zero-length window).
- `enabled` is bool.
- Reject any unknown field.

### Mode dispatch
- Single shared helper `scheduling.mode_changer.HAModeChanger.async_set_mode(target, source)` is the **only** place that calls `hass.services.async_call("alarm_control_panel", ...)`. Both `websocket_modes_set` and the schedule manager go through it.
- `HAModeChanger` stamps the HA `Context` with id `f"abode_sched_{pair_id}_{nonce}"` for schedule-initiated calls; user/external calls get `Context()` (default id).

### Runtime behavior
- Manager registers one daily `async_track_time_change` callback per pair for the **arm** edge only, restricted to the pair's `weekdays`. The **disarm** edge is scheduled as a one-shot `async_call_later` by any of four things: a successful arm, the `already_home` skip, restart reconciliation, or the override listener adopting a panel that entered `armed_home` mid-window (#212). This avoids the day-after-arm weekday ambiguity for overnight pairs. See phase-3 for details.
- Skip rule applied at arm fire time (see Concepts).
- Pending-disarm cancellation: listen `EVENT_STATE_CHANGED` for the alarm panel entity; if `event.context.id` does **not** start with `abode_sched_` and the transition leaves `armed_home`, cancel any pending disarm timers belonging to pairs currently in `ARMED` state, set their `last_disarmed_at = now()`, fire `schedule_skipped` with `reason: "manual_override"`. The listener is bidirectional (#212): a transition *into* `armed_home` from a non-schedule context, inside an enabled pair's window, adopts the panel and registers the one-shot disarm — reported as `schedule_skipped` with `reason: "already_home"`. It never calls `mode_changer`, so it can only ever schedule a release, never arm anything.
- HA events fired (always via `hass.bus.async_fire`):
  - `abode_security.schedule_fired` — payload: `{schedule_id, schedule_name, action: "arm"|"disarm", target_mode, fired_at}`
  - `abode_security.schedule_skipped` — payload: `{schedule_id, schedule_name, action: "arm"|"disarm", reason, skipped_at}`
  - `abode_security.schedule_failed` — payload: `{schedule_id, schedule_name, action, error, attempts, failed_at}`

### Authorization
- Mutations (`schedules/create`, `schedules/update`, `schedules/delete`) require `connection.user.is_admin`. Reuse the `@require_admin` decorator from `websocket_api.py`. **Enforcement is at the WebSocket layer; the frontend admin check is UX only and not relied on for security.**
- List/get are open to any authenticated panel viewer.

### Frontend
- New section "Home schedules" rendered **always** beneath the modes grid in `modes-tab.ts`. Empty state copy: "No schedules yet. Add one to arm Home automatically."
- Inline-edit rows: collapsed row shows `[day chips] [arm → disarm] [enable toggle] [edit] [delete]`. Edit mode replaces with editable controls + per-row Save/Cancel. Save commits one row at a time and surfaces inline validation errors.
- "Add schedule" button below the list inserts a new row in edit mode.
- Day-chip widget is a reusable Lit component (`day-chip-picker`); times use native `<input type=time>`.
- Mode cards themselves get no schedule hint (cards remain clean).

### Logging
- INFO: `"Schedule '<name>' fired arm"`, `"Schedule '<name>' fired disarm"`, `"Schedule '<name>' skipped (reason)"`, `"Schedule '<name>' failed after 4 attempts"` (1 initial + 3 retries — match the `attempts` field in the `schedule_failed` event), `"Reconciled <n> schedules on startup"`.
- DEBUG: per-tick evaluation, context-id filtering decisions.

## Phases

| Phase | Title | Description |
|-------|-------|-------------|
| 1 | Domain & CRUD | Models, store with repair issue, WS CRUD endpoints, manager skeleton. Headless: schedules can be persisted and listed; nothing fires yet. |
| 2 | Mode dispatcher + scheduler clock | Extract `mode_changer.py` (refactors `websocket_modes_set`), introduce `ScheduleClock` wrapping `async_track_time_change`, source-tagging via Context.id. Existing mode switching continues to work. |
| 3 | Runtime — fire, skip, reconcile, retry | `state_machine.py`, `manager.py` orchestrator wiring Clock + ScheduleClock + ModeChanger + Store; arm/disarm timers, skip rule, manual-override cancellation, restart reconciliation, retries, HA events. After this phase the feature works end-to-end via WS API. |
| 4 | Frontend UI | `day-chip-picker.ts`, `schedule-row.ts`, `schedules-section.ts`, `api.ts` wrappers, mount under modes grid. Web-test-runner unit tests + one Playwright E2E. |

## Related Documentation

- [Phase 1: Domain & CRUD](./phase-1-domain-and-crud.md)
- [Phase 2: Mode dispatcher + scheduler clock](./phase-2-mode-dispatcher.md)
- [Phase 3: Runtime — fire, skip, reconcile, retry](./phase-3-runtime.md)
- [Phase 4: Frontend UI](./phase-4-frontend.md)
- [Architecture overview](../../docs/ARCHITECTURE.md)
- [Notifications blueprint pattern](../../docs/notifications.md) — schedules will fit the same shape.

## Testing Tools

> Discovered during spec creation. Use these for verification after automated tests pass.

| MCP Server | Tool Prefix | Use For |
|---|---|---|
| home-assistant | `mcp__home-assistant__*` | Live debugging against the dev HA stack: `ha_get_logs` to inspect schedule fire logs, `ha_call_service` to fire `alarm_control_panel.*` directly during integration testing, `ha_eval_template` to inspect entity states. |

> **Note on browser MCP**: at the time this spec was written, the `mcp__browsermcp__*` server was offline. **Do not rely on it.** Use the existing Playwright E2E suite under `tests/e2e/` for any visual verification — it runs against the live Docker stack via `./scripts/test-e2e.sh`.

## Logging & Diagnostics

> A zero exit code does not mean clean output. Check the following after every test run and build.

| Log Source | Location | Format | What to Check |
|---|---|---|---|
| Test run output | stdout via `uv run pytest -m ""` | text | `WARNING`, `ERROR`, raised but caught exception tracebacks |
| Pyright output | stdout via `uv run pyright` | text | `error:` and `warning:` lines |
| Ruff output | stdout via `uv run ruff check .` | text | any line matching `^[A-Z]\d+\b` (rule codes) |
| Frontend test | `cd frontend && npm test` | text | console errors / unhandled promise rejections during Lit component tests |
| HA logs (integration tests via mock-abode) | `docker compose logs homeassistant` | text | `[abode_security] WARNING`, `ERROR`, stack traces, `Schedule '...' failed` lines |
| HA Repairs UI | http://localhost:8123/config/repairs | UI | Verify `schedule_fire_failed` repair issue appears after Phase 3 retry-exhaustion test. |

## Access Control

> Not applicable — the integration is a Home Assistant custom component. Access control is handled entirely in application code via the `@require_admin` decorator on WebSocket commands (see `websocket_api.py`). There are no Firebase rules, RLS policies, or external IAM systems.

- **Mutation gating**: All `schedules/create|update|delete` WS commands use the existing `@require_admin` decorator from `websocket_api.py`.
- **Read gating**: `schedules/list|get` are open to any authenticated HA user with panel access (parity with `modes/list`).
