---
status: done
phase: 2
feature: ci-integration-tests
title: Fix integration test gating regressions
---

# Phase 2: Fix Integration Test Gating Regressions (#102, #103)

**Status**: done

## Goal

Turn the two remaining FAILs from Phase 1 green:
- **#102** — `test_action_validation_errors` line 342 expects `validation_error`, gets `invalid_format`.
- **#103** — `test_coordinator_respects_enabled_state` line 520-526 passes `enabled=False` to `ActionManager.async_create` which no longer accepts it.

Both failing integration tests live in `tests/test_actions_integration.py`, which [Phase 1](phase-1-socket-fixture.md) also edits to remove dead socket markers. Fixing them in sibling commits keeps a clean diff per concern.

## Bug #102: validation error code mismatch

### Diagnosis

`test_action_validation_errors` (tests/test_actions_integration.py:320) sends `"name": ""` to `abode_security/actions/create`. The test expects WS error `code == "validation_error"`.

The actual code path in `custom_components/abode_security/websocket_api.py`:
- Lines 214, 279, 682 all call `connection.send_error(msg["id"], "validation_error", str(err))` from `ValueError` handlers — i.e. they wrap **runtime** validation errors raised by `ActionManager._validate_action`.
- But the WS command has a voluptuous schema at the registration site. If `name=""` fails the schema (e.g. `vol.Length(min=1)`), pytest-HA-cc / the WS handler returns `code = "invalid_format"` *before* the runtime path is reached.

### Step 2.1 — Locate the schema

```bash
rg -n "abode_security/actions/create|vol.Schema|vol.Required" custom_components/abode_security/websocket_api.py
```

Identify the voluptuous schema for the `create` command. Find the `name` field's constraint.

### Step 2.2 — Use runtime validation for empty names

If `vol.Length(min=1)` rejects empty names at schema time, the test is hitting the schema, not `_validate_action`. Do not loosen the test to accept both `validation_error` and `invalid_format`; that would hide the boundary this spec is trying to preserve.

Remove only the minimum-length constraint from the voluptuous name schemas, and keep the maximum-length guard. Voluptuous should validate *shape* and payload bounds (types, required fields, allowed enums, maximum list/string sizes); business rules like "name must not be empty" belong in `_validate_action` so error messages can be richer ("Action name cannot be empty" vs `expected str with length >= 1`).

### Step 2.3 — Apply the fix

**File**: `custom_components/abode_security/websocket_api.py`

Adjust the voluptuous schema for `abode_security/actions/create` so `name` keeps the maximum-length guard but no longer has a minimum-length guard:

```python
vol.Required("name"): vol.All(str, vol.Length(max=MAX_NAME_LENGTH))
```

Do the same for `abode_security/actions/update`:

```python
vol.Optional("name"): vol.All(str, vol.Length(max=MAX_NAME_LENGTH))
```

The runtime `_validate_action` in `action_manager.py` already raises `ValueError("Action name cannot be empty")` (verify by reading the function body once before editing).

**File**: `tests/test_websocket_api.py`

Keep the existing oversize-payload tests intact. Add or adjust targeted assertions so the contract is explicit:

- `actions/create` with `name=""` returns `validation_error`.
- `actions/update` with `name=""` returns `validation_error`.
- `actions/create` and `actions/update` with names longer than `MAX_NAME_LENGTH` still fail schema validation before the manager path and return `invalid_format`.

Current baseline note: `test_ws_actions_create_validation_error` uses `"   "` because `vol.Length(min=1)` rejects `""` at schema time. After removing the minimum-length schema guard, change that test to use `""`; add the matching update-path empty-name assertion near the existing update validation tests.

### Step 2.4 — Verify

```bash
./scripts/dev.sh
uv run pytest tests/test_actions_integration.py::TestActionsIntegration::test_action_validation_errors -v
```

Must pass. Then run the full file:

```bash
uv run pytest tests/test_actions_integration.py -m integration -v
```

Look for collateral damage. Tests that intentionally cover too-long names should continue to expect schema-level rejection; tests for empty or whitespace-only names should expect `validation_error`.

### Acceptance

- `test_action_validation_errors` passes.
- All `actions/*` WS commands return `validation_error` for business-rule violations and `invalid_format` *only* for shape violations (missing field, wrong type).
- The focused `tests/test_websocket_api.py` coverage includes empty-name create/update cases and too-long-name create/update cases, so the schema/runtime boundary is locked down without needing the integration suite.

## Bug #103: `async_create` dropped the `enabled` kwarg

### Diagnosis

`ActionManager.async_create` (action_manager.py:389-396) signature:

```python
async def async_create(
    self,
    name: str,
    modes: list[str],
    sensor_entity_ids: list[str],
    alarm_entity_ids: list[str],
    delay_seconds: int = 0,
) -> AbodeAction:
```

But `AbodeAction.enabled` exists (line 45, default `True`), `_validate_action` ignores it (already correct — enabled is a state field, not a validation field), `async_update` accepts it (line 460), and the test at line 525 passes `enabled=False`.

The drift is one-sided: `async_create` lost the kwarg in some prior refactor. The test is right — symmetry with `async_update` and consistency with the `AbodeAction` dataclass demand `async_create` accept it.

### Step 2.5 — Add the kwarg

**File**: `custom_components/abode_security/action_manager.py`

```python
async def async_create(
    self,
    name: str,
    modes: list[str],
    sensor_entity_ids: list[str],
    alarm_entity_ids: list[str],
    delay_seconds: int = 0,
    enabled: bool = True,
) -> AbodeAction:
    """Create a new action with validation.

    ...
    Args:
        ...
        delay_seconds: Delay before triggering (0-60)
        enabled: Whether the action starts enabled (default True)
    ...
    """
    self._validate_action(
        name, modes, sensor_entity_ids, alarm_entity_ids, delay_seconds
    )
    self._warn_missing_entities(sensor_entity_ids, alarm_entity_ids)

    action = AbodeAction(
        id=str(uuid.uuid4()),
        name=name,
        modes=modes,
        sensor_entity_ids=sensor_entity_ids,
        alarm_entity_ids=alarm_entity_ids,
        delay_seconds=delay_seconds,
        enabled=enabled,
    )
    await self._store.async_add(action)
    return action
```

Two edits in the same function: signature line + the `AbodeAction(...)` constructor call (around line 417-424).

### Step 2.6 — Audit call sites

```bash
rg -n "async_create\\(" custom_components/abode_security tests
```

Confirm no existing caller was *relying* on `enabled` always being `True` (it wouldn't break — the default preserves old behavior — but verify there's no commented-out "we should pass enabled here" TODO).

### Step 2.7 — Audit the WS handler

The `actions/create` WS command should also forward an optional `enabled` field if the frontend sends one. Check:

```bash
rg -n "async_create" custom_components/abode_security/websocket_api.py
```

If the WS handler currently only forwards `name`, `modes`, `sensor_entity_ids`, `alarm_entity_ids`, `delay_seconds`, forward `enabled` too for parity with `async_update`. Add `vol.Optional("enabled", default=True): bool` to the create schema and pass `enabled=msg.get("enabled", True)` to `action_manager.async_create`.

**File**: `tests/test_websocket_api.py`

Add or update a test that sends `enabled: False` to `abode_security/actions/create` and asserts the returned action has `"enabled": False`. This keeps the WS contract covered, not only the direct manager call in `tests/test_actions_integration.py`.

### Step 2.8 — Verify

```bash
./scripts/dev.sh
uv run pytest tests/test_actions_integration.py::TestActionTriggerIntegration::test_coordinator_respects_enabled_state -v
```

Then the full file:

```bash
uv run pytest tests/test_actions_integration.py -m integration -v
```

### Acceptance

- `test_coordinator_respects_enabled_state` passes.
- `ActionManager.async_create` accepts an optional `enabled: bool = True` kwarg.
- WS `actions/create` handler accepts and forwards optional `enabled`.
- Existing manager and WS create callers that omit `enabled` still create enabled actions by default.

## Step 2.9 — Final verify, all integration tests

```bash
./scripts/dev.sh
uv run pytest tests/ -m integration -v --tb=short 2>&1 | tail -30
```

Expected: 108 pytest items passed, 0 failed, 0 errors.

If anything still fails: STOP, do not commit. Diagnose. The whole point of [Phase 1](phase-1-socket-fixture.md) + Phase 2 is to leave the suite green before [Phase 3](phase-3-ci-workflow.md) wires up CI.

## Step 2.10 — Commit

Two commits, one per bug, for reviewability:

```bash
git add custom_components/abode_security/websocket_api.py
git add tests/test_websocket_api.py
git commit -m "fix(actions): align WS validation error code with runtime path (closes #102)"

git add custom_components/abode_security/action_manager.py custom_components/abode_security/websocket_api.py tests/test_websocket_api.py
git commit -m "fix(actions): async_create accepts enabled kwarg (closes #103)"
```

(Adjust paths per what each fix actually touches.)
