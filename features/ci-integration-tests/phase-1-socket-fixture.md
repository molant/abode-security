---
status: planned
phase: 1
feature: ci-integration-tests
title: Socket-enable fixture for integration tests
---

# Phase 1: Socket-Enable Fixture for Integration Tests

**Status**: planned

## Goal

Make `pytest -m integration` runnable in the same process that loads the pytest-HA-cc plugin, by introducing one autouse fixture in `tests/conftest.py` and removing the 94 dead `@pytest.mark.enable_socket` decorations.

## Why socket enabling is one fixture

The root cause is centralized: pytest-HA-cc disables sockets per-test, defeating per-test markers. The fix must be at the same scope (per-test, before the test body runs) and applied uniformly to anything carrying `@pytest.mark.integration`. An autouse fixture gated by `request.node.get_closest_marker("integration")` is exactly that shape.

The 10 test-file edits in Step 1.2 are mechanical cleanup only: they remove misleading no-op decorators after the central fixture owns the socket behavior.

## Pre-work — verify current failure

Before any code change:

```bash
./scripts/dev.sh                           # boot mock server
uv run pytest tests/ -m integration --tb=line 2>&1 | tail -40
```

Confirm:
- Roughly 100 tests `ERROR` with `HASocketBlockedError`.
- 2 tests `FAIL`: `test_action_validation_errors` and `test_coordinator_respects_enabled_state` (the bugs [Phase 2](phase-2-bug-fixes.md) owns).
- A small remainder pass.

Record the exact pass/error/fail counts in the PR description.

## Step 1.1 — Write the autouse fixture

**File**: `tests/conftest.py`

Append at the end of the existing fixtures (after the `abode_with_mock_server` fixture, around line 302):

```python
@pytest.fixture(autouse=True)
def _integration_socket_enabled(
    request: pytest.FixtureRequest,
) -> Generator[None, None, None]:
    """Enable sockets for `@pytest.mark.integration` tests.

    pytest-HA-cc's pytest_runtest_setup unconditionally calls
    pytest_socket.disable_socket(), defeating per-test `enable_socket`
    markers. Depending on the `socket_enabled` fixture runs *after* setup
    and undoes the disable. The HASocketBlockedError.instances list is
    cleared on entry and exit to neutralize the cleanup assertion at
    pytest_homeassistant_custom_component/plugins.py:468 if any blocked
    attempt slipped through during async teardown.
    """
    if request.node.get_closest_marker("integration") is None:
        yield
        return

    # Lazy import: only loaded when an integration test actually runs,
    # so the unit-test suite is unaffected.
    from pytest_homeassistant_custom_component.plugins import (
        HASocketBlockedError,
    )

    HASocketBlockedError.instances = []
    request.getfixturevalue("socket_enabled")
    try:
        yield
    finally:
        HASocketBlockedError.instances = []
```

**Why `request.getfixturevalue("socket_enabled")`** rather than declaring `socket_enabled` as a parameter: parameter-style requests participate in the fixture-resolution graph and would apply to every test (autouse). Demanding the fixture lazily inside the guard restricts the actual socket-enable side effect to integration tests.

**Why clear `instances` before *and* after**: a unit test running earlier in the session may have left an entry behind. The cleanup at plugins.py:475 already does this, but the assertion at plugins.py:468 runs *before* the cleanup, so we defensively start clean.

## Step 1.2 — Remove the 94 dead `@pytest.mark.enable_socket` decorations

These markers do nothing in this stack (per the README mechanism section). Leaving them in place misleads future contributors into thinking they're load-bearing.

Files to edit (run `rg -l "@pytest\.mark\.enable_socket" tests | sort` to confirm):

- `tests/test_actions_integration.py`
- `tests/test_alarm_control_panel.py`
- `tests/test_binary_sensor.py`
- `tests/test_camera.py`
- `tests/test_cms_settings_switches.py`
- `tests/test_cover.py`
- `tests/test_light.py`
- `tests/test_lock.py`
- `tests/test_sensor.py`
- `tests/test_switch.py`

For each, remove every line that is exactly `@pytest.mark.enable_socket` (preserve `@pytest.mark.integration` immediately above it).

Use a per-file edit rather than a project-wide replacement so each diff can be reviewed. Example:

```bash
# Dry run first
rg -n "@pytest\.mark\.enable_socket" tests/test_alarm_control_panel.py
# Then remove only those exact decorator lines in that file
```

Expected removal count by current file:

| File | Count |
|---|---:|
| `tests/test_actions_integration.py` | 2 |
| `tests/test_alarm_control_panel.py` | 5 |
| `tests/test_binary_sensor.py` | 2 |
| `tests/test_camera.py` | 5 |
| `tests/test_cms_settings_switches.py` | 42 |
| `tests/test_cover.py` | 4 |
| `tests/test_light.py` | 7 |
| `tests/test_lock.py` | 4 |
| `tests/test_sensor.py` | 2 |
| `tests/test_switch.py` | 21 |
| **Total** | **94** |

## Step 1.3 — Verify

```bash
./scripts/dev.sh
uv run pytest tests/ -m integration --tb=line 2>&1 | tail -20
```

Expected outcome:
- 0 `HASocketBlockedError` errors.
- 2 `FAIL`s remain (`test_action_validation_errors`, `test_coordinator_respects_enabled_state`) — handed off to Phase 2.
- All other tests `PASS`.

Then verify the unit suite is unaffected:

```bash
./scripts/check.sh
```

The fixture's `if` guard returns early for non-integration tests before importing pytest-HA-cc internals or requesting `socket_enabled`, so the existing 332 non-integration tests should keep the same behavior. If unit tests slow noticeably, inspect whether the guard is still returning before `request.getfixturevalue("socket_enabled")`.

## Step 1.4 — Commit

```bash
git add tests/conftest.py tests/test_*.py
git commit -m "test(integration): enable sockets via fixture for -m integration"
```

Commit message body should reference:
- The pytest-HA-cc mechanism (one paragraph)
- The number of `@pytest.mark.enable_socket` removals (94 across 10 files)
- Why this is split into its own commit ahead of the bug fixes in Phase 2

## Edge cases the fixture handles

| Scenario | Behavior |
|---|---|
| Test with no `integration` marker | Fixture is a no-op (early return) |
| Test with `integration` marker but no `hass` fixture | `socket_enabled` resolves harmlessly; teardown clears the counter |
| Test that uses both `hass_ws_client` (which already requests `socket_enabled`) and integration marker | `socket_enabled` is requested twice — pytest deduplicates session/function fixtures; no double-enable issue |
| Mock server unreachable | Test fails with `requests.ConnectionError` from the `reset_mock_server` fixture, *not* `HASocketBlockedError`. Clear signal vs. confusing one. |

## What this phase does NOT do

- Does not change `pyproject.toml`'s `addopts`. Local default still skips integration tests (correct).
- Does not touch `.github/workflows/`. That's [Phase 3](phase-3-ci-workflow.md).
- Does not fix the 2 real bugs. That's [Phase 2](phase-2-bug-fixes.md).

## Risk

The only failure mode is pytest-HA-cc changing the name of `HASocketBlockedError` or its `instances` attribute in a future bump. Mitigations:
- The import is lazy and explicit — a future `ImportError` will surface immediately, not as silent socket re-disable.
- Phase 3's CI gate means any pytest-HA-cc bump that breaks this fixture trips the integration job on the Dependabot PR, not on `main`.
