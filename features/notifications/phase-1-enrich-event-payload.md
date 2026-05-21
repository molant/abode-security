---
status: in_progress
phase: 1
feature: notifications
title: Enrich event payload
---

# Phase 1: Enrich event payload

Add six new keys (sensor friendly name, device class, previous/new state, area id/name) to the existing `abode_security.action_triggered` event payload. No new event type, no camera work, no UI changes. Pure data plumbing: capture the sensor's state-changed context at the entry point in `_handle_state_change` and thread it through the call chain so `_execute_action` has it available when it builds the event payload.

## Context

The integration already fires `abode_security.action_triggered` from `custom_components/abode_security/action_trigger.py:307`. Today the payload only includes `triggered_by` (an `entity_id` string). A user writing a `notify.mobile_app_*` automation has to template-look-up `states[trigger.event.data.triggered_by].name` just to say "Front Door opened" — and they have no way at all to know the previous → new state transition.

**Why thread context instead of re-fetching at execute time**: actions can be configured with a delay (`AbodeAction.delay_seconds`, 0–60s). During that delay the sensor state can flip back. Re-reading `hass.states.get(triggered_by)` at execute time would give the *current* state, not the state that *caused* the trigger. We must capture the state at event time and carry it through.

**Dependencies / what must be true before starting**:
- `dashboard-configuration` feature is fully implemented (it is — status `IMPLEMENTED`). The trigger coordinator, `AbodeAction`, and the existing event firing are all in place.
- `./scripts/check.sh` passes on a clean checkout of the current branch.

Read [./README.md](./README.md) for overall feature context.

## Structure

```
custom_components/abode_security/
  action_trigger.py             # modify: extend trigger context, enrich payload

tests/
  test_action_trigger.py        # modify: extend existing test_coordinator_fires_event;
                                #         add tests for new fields incl. null cases
  test_actions_integration.py   # modify: assert enriched payload in integration flow
```

No new files in this phase.

## Implementation Checklist

> **Remember**: Update these checkboxes as you complete each task!

### Baseline Test Verification (before starting implementation)

- [x] Run `./scripts/check.sh` and confirm it passes (ruff, mypy, pyright, pytest unit suite).
- [x] Run `uv run pytest -m ""` and confirm the full suite (including integration markers) passes against the running mock server (`./scripts/dev.sh`).
- [x] If any test fails, **fix and commit separately** before starting Phase 1. Do not bundle baseline fixes with this phase's commit.

### Sub-Phase A: Thread sensor state and registry context through the trigger chain

Deployable on its own: at the end of this sub-phase the existing event payload is **unchanged**, but `_execute_action` has the new context available as parameters. All existing tests still pass.

#### Code changes — `action_trigger.py`

- [x] Introduce a private frozen dataclass `_SensorTriggerContext` at the top of the module (after the existing imports). Fields, all immutable:
  - `entity_id: str`
  - `friendly_name: str | None`
  - `device_class: str | None`
  - `previous_state: str | None`
  - `new_state: str | None`
  - `area_id: str | None`
  - `area_name: str | None`
- [x] In `_handle_state_change` (currently at lines 91–119), after the existing `off → on` guards, build a `_SensorTriggerContext`:
  - `friendly_name` ← `new_state.attributes.get("friendly_name")`
  - `device_class` ← `new_state.attributes.get("device_class")`
  - `previous_state` ← `old_state.state` (always populated here because of the `old_state.state != "off"` guard above, but type-annotate as `str | None` for symmetry)
  - `new_state` ← `new_state.state` (literal `"on"`, but keep the field nullable)
  - `area_id` ← `entity_registry.async_get(hass).async_get(entity_id)` → `.area_id` if the registry entry exists; fall back to `device_registry.async_get(hass).async_get(entry.device_id).area_id` when the entity has no direct area but its device does; else `None`
  - `area_name` ← `area_registry.async_get(hass).async_get_area(area_id).name` if `area_id` is non-null and the area exists; else `None`
- [x] Pass this `_SensorTriggerContext` object into `_process_sensor_activation` (currently takes `entity_id: str`). Update its signature to take the context. Internally it still uses `context.entity_id` for the membership check against `action.sensor_entity_ids`.
- [x] Update `_trigger_action` to take and forward the context to `_execute_action`. Update its docstring.
- [x] In the delayed-execution branch inside `_trigger_action` (lines 193–215), capture the context in the `delayed_callback` closure so `_delayed_execute` receives it intact even though the user may have edited the action in the meantime.
- [x] Update `_delayed_execute` to accept and forward the context.
- [x] Update `_execute_action` to take the context. **Decision (do not deviate)**: replace the `triggered_by: str` parameter with `context: _SensorTriggerContext` on all four methods (`_process_sensor_activation`, `_trigger_action`, `_delayed_execute`, `_execute_action`). Inside `_execute_action`, the existing `event_data["triggered_by"]` continues to be a string — populate it from `context.entity_id`. Do **not** keep both a `triggered_by` arg and a `context` arg in parallel; that is the "mixed" path that this checklist forbids.

#### Imports

- [x] Add at top of `action_trigger.py`:
  - `from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er`
  - (already-present imports for `Event`, `EventStateChangedData`, etc., stay)
- [x] Note: the HA convention is `async_get` returns the singleton registry synchronously despite the name — do not `await` these.

#### Type discipline

- [x] Run `uv run mypy custom_components/abode_security/action_trigger.py` and `uv run pyright custom_components/abode_security/action_trigger.py` — both must be clean.
- [x] Add `from __future__ import annotations` at the top of `action_trigger.py` if it's not already there (it is — verify).

#### Tests

- [x] Update existing `test_coordinator_fires_event` in `tests/test_action_trigger.py:331` to construct the `EventStateChangedData` with `friendly_name` and `device_class` attributes on the `new_state`. Assert the existing payload keys still appear and are unchanged — specifically, assert that the projection of captured `event_data` over the original 7 keys (`action_id`, `action_name`, `triggered_by`, `mode`, `alarms_triggered`, `alarms_failed`, `timestamp`) has the same types and values it had pre-Phase-1 (use `assert {k: event_data[k] for k in EXISTING_KEYS} == expected_existing` so a future regression that silently changes a value type — e.g. `triggered_by` from `str` to a context object — is caught). Do **not** assert `set(event_data) == EXISTING_KEYS` after Sub-Phase B, because the payload intentionally has 13 keys at that point.
- [x] Add a new test `test_trigger_context_threaded_through_delay`: configure an action with `delay_seconds=2`, fire the state change with a specific `friendly_name`, mutate the live `hass.states` mid-delay to remove the attribute, fire the timer, assert the captured `friendly_name` is preserved in the eventual event payload.
- [x] Add a new test `test_trigger_context_built_for_sensor_without_area`: register a sensor entity with no `area_id` and no `device_id`; trigger; assert the context is built with `area_id=None, area_name=None` and no exception.

### Sub-Phase B: Add the new payload keys

Deployable on its own: builds on Sub-Phase A. Now the event consumers see the new keys.

#### Code changes — `action_trigger.py`

- [ ] In `_execute_action`, modify the `event_data` dict construction (lines 298–306). Append (do not reorder existing keys):
  ```python
  event_data = {
      "action_id": action.id,
      "action_name": action.name,
      "triggered_by": context.entity_id,
      "mode": current_mode,
      "alarms_triggered": alarms_triggered,
      "alarms_failed": alarms_failed,
      "timestamp": datetime.now(UTC).isoformat(),
      # New in this phase:
      "sensor_friendly_name": context.friendly_name,
      "sensor_device_class": context.device_class,
      "previous_state": context.previous_state,
      "new_state": context.new_state,
      "sensor_area_id": context.area_id,
      "sensor_area_name": context.area_name,
  }
  ```
- [ ] Confirm payload key ordering: existing keys first (in their current order), new keys appended at the end. This is purely for diff readability and event-log scannability — HA event consumers should not depend on key order.

#### Tests

- [ ] Extend `test_coordinator_fires_event` to assert each new key is present with the exact expected value.
- [ ] Add `test_event_payload_null_when_attributes_missing`: trigger from a sensor whose `new_state.attributes` lacks `friendly_name` and `device_class`. Assert `sensor_friendly_name` and `sensor_device_class` are `None` (not missing, not empty string, not `"unknown"`).
- [ ] Add `test_event_payload_area_resolved_via_entity_registry`: register an entity in the entity registry with an explicit `area_id`. Confirm `sensor_area_id` and `sensor_area_name` propagate.
- [ ] Add `test_event_payload_area_resolved_via_device_fallback`: entity has no direct `area_id` but its `device_id` does. Confirm the fallback path populates both fields.
- [ ] Add `test_event_payload_preserves_existing_keys_exact_types`: fire an event and assert each of the original 7 keys has the exact pre-Phase-1 type (`action_id: str`, `action_name: str`, `triggered_by: str`, `mode: str`, `alarms_triggered: list[str]`, `alarms_failed: list[str]`, `timestamp: str`). This is the backwards-compatibility guardrail — if a future refactor changes any of these (e.g. embeds an object), the test fails loudly.
- [ ] Integration test in `tests/test_actions_integration.py`: register an `event_listener = []` on `abode_security.action_triggered`, fire a sensor activation, then `await hass.async_block_till_done()`, then assert the listener saw one event with all 13 keys (7 existing + 6 new) populated as expected.

#### Documentation (End of Sub-Phase B)

- [ ] `docs/ARCHITECTURE.md` (lines 127–145): add one paragraph after the existing action-trigger flow description noting that the event payload now includes sensor friendly name, device_class, prev/new state, and area context. Do **not** describe the camera snapshot yet — that lands in Phase 2 and would document a feature that doesn't exist yet.
- [ ] No README update yet — `README.md` ("Notifications" section) is written in Phase 3 once the user-facing docs and blueprint exist.
- [ ] `CLAUDE.md` — no update needed (no new commands, conventions, or AI-relevant context introduced in this phase).

### Build Verification (required before marking phase complete)

- [ ] `./scripts/check.sh` — exits zero, output ends with "All checks passed" (or equivalent).
- [ ] `uv run pytest -m ""` — full suite passes, including integration markers (with `./scripts/dev.sh` running).
- [ ] Scan pytest stdout for `PytestUnraisableExceptionWarning`, `RuntimeWarning: coroutine '...' was never awaited`, and any other warnings. A zero exit code from pytest does **not** catch unraisable warnings. If any new warnings appear, fix or explicitly silence with justification before marking the phase complete.
- [ ] If `frontend/` was somehow touched (it should not be in this phase), run `cd frontend && npm test` as well.
- [ ] Mark `status: done` in this file's frontmatter only after all the above pass.

### Manual Verification with MCP Tools

> Use the `mcp__home-assistant__*` tools listed in [Testing Tools](./README.md#testing-tools).

- [ ] Start the dev stack: `./scripts/dev.sh`.
- [ ] In HA UI: create an action mapping a single mock binary_sensor to a single alarm switch, modes = `[home]`.
- [ ] Set the alarm to `home` mode.
- [ ] Trigger the sensor activation. The HA event bus (`ha_call_event` / `bus.async_fire`) does **not** synthesize an `EVENT_STATE_CHANGED` — the coordinator listens for state-change events, not arbitrary bus events. Instead, hit the mock Abode API endpoint to flip a binary_sensor state (`http://localhost:8000/docs` lists the sensor-trip routes), or `POST /api/states/binary_sensor.<id>` against HA's REST API with state `"on"`. After triggering, use the MCP tools (discover names via `mcp__home-assistant__ha_list_resources`) to read state/history/logs and confirm the event payload.
- [ ] Open HA Developer Tools → Events → "Listen to events" → enter `abode_security.action_triggered` and start listening.
- [ ] Re-trigger the sensor. Confirm the captured event has all 6 new keys with reasonable values (friendly_name = the sensor's HA friendly name; device_class = the class set on the binary_sensor or `null`; previous_state = `"off"`; new_state = `"on"`; area = the area you assigned in HA UI, or `null` if unassigned).
- [ ] Repeat with a binary_sensor that has **no** area, **no** device_class, **no** friendly_name override. Confirm those fields come through as `null` (not `"unknown"`, not missing).

## Technical Details

### Why `_SensorTriggerContext` is a dataclass, not kwargs

The state-changed context is read once in `_handle_state_change` and passed unchanged through three more methods (`_process_sensor_activation`, `_trigger_action`, `_execute_action`). With a delayed-execution branch the context also has to survive in a closure for up to 60 seconds. A frozen dataclass:

1. Makes the propagation explicit at every function signature — easy to grep for.
2. Lets mypy/pyright catch a forgotten field.
3. Is immutable, so a delayed callback cannot accidentally mutate it.

A `dict[str, Any]` would also work but defeats type checking. Don't use one.

### Why we use `entity_registry` + `area_registry`, not `hass.states.get(entity_id).attributes`

`State.attributes` sometimes carries the resolved area (especially for HA Core 2024.6+) but it's not guaranteed across all platforms — third-party integrations may omit it. The registries are the source of truth, and the helpers are O(1) lookups. Use them. The fallback chain — entity registry's `area_id` → device registry's `area_id` — matches the precedence the HA frontend uses.

### Edge: sensor not in entity_registry at all

A binary_sensor created at runtime by a script (rare in HA but possible) may not appear in the entity registry. `er.async_get(hass).async_get(entity_id)` returns `None`. The context is built with `area_id=None, area_name=None`. Do not raise.

### Edge: action delete during delay

Existing code at `action_trigger.py:230–237` already handles "action deleted/disabled during delay" by returning early **before** `_execute_action` runs. The context still gets constructed and captured in the closure — that's wasted work but harmless. Do not optimize this case; it would entangle the new context plumbing with the existing delete-during-delay path and add a code path with little payoff.

## Constraints

- **Backwards compatibility (hard)**: the existing 7 payload keys remain unchanged in name, type, and value. Existing user automations and the `dashboard-configuration` test suite must keep passing without modification.
- **No re-fetching the sensor state at execute time** — the captured state at trigger time is the source of truth.
- **No state mutation in the context**: `_SensorTriggerContext` is frozen.
- **Type-clean**: `uv run mypy ...` and `uv run pyright ...` must remain green. The codebase enforces both via `.githooks/pre-commit`; do not bypass with `--no-verify`.
- **No new dependencies**: everything used in this phase (`entity_registry`, `area_registry`, `device_registry`, `dataclasses.dataclass(frozen=True)`) already ships with HA + the stdlib.
