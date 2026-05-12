---
status: done
phase: 1
feature: ci-integration-tests
title: Enable sockets for integration tests
---

# Phase 1: Enable Sockets for Integration Tests

**Status**: done

## Goal

Make `pytest -m integration` runnable in the same process that loads the
pytest-HA-cc plugin, so the suite can be CI-gated. Remove the 94 misleading
no-op `@pytest.mark.enable_socket` decorations once the central socket gate
is in place.

## Why a fixture wasn't enough (deviation from the original plan)

The first draft of this phase proposed an autouse fixture that depends on
pytest-socket's `socket_enabled` fixture for `@pytest.mark.integration` tests.
That works in isolation, but it doesn't work in this codebase for two reasons:

1. **Session-scope `mock_server` runs first.** `tests/conftest.py` defines
   `mock_server` (and its dependency chain `mock_server_client` →
   `reset_mock_server`) as session-scope. pytest initialises session-scope
   fixtures *before* function-scope autouse fixtures during the same test's
   setup phase. So when the *first* integration test runs, the dependency
   chain triggers `mock_server`'s `requests.get(/health)` while sockets are
   still disabled — long before the function-scope `socket_enabled` fixture
   gets a chance to run.
2. **HA-cc also installs a host-allowlist guard.** Beyond `disable_socket`,
   `pytest-HA-cc/plugins.py::pytest_runtest_setup` calls
   `pytest_socket.socket_allow_hosts(["127.0.0.1"])`. On macOS the mock
   server's `http://localhost:8000` resolves to `::1` first, which the
   allowlist blocks with `SocketConnectBlockedError`. Even after socket
   creation is re-enabled, the connect would still fail.

So the fix has to short-circuit both calls *before* any fixture sees them.

## The actual mechanism

In `tests/conftest.py`:

- Monkey-patch `pytest_socket.disable_socket` and
  `pytest_socket.socket_allow_hosts` so both are no-ops while
  `_in_integration_test` is `True`. The hostname guard already in place
  from a prior unit test's call gets cleared by restoring
  `socket.socket.connect = pytest_socket._true_connect` for the integration
  test's lifetime.
- `pytest_runtest_setup(item)` hookimpl with `tryfirst=True` flips the flag
  based on `item.get_closest_marker("integration")`. Because both
  hookimpls (ours and HA-cc's) are default-position-or-tryfirst, pluggy
  runs ours first; by the time HA-cc's `pytest_runtest_setup` calls
  `disable_socket(...)` and `socket_allow_hosts(...)`, the flag is already
  set and the patched wrappers short-circuit.
- An autouse fixture (`_integration_socket_cleanup`) clears
  `HASocketBlockedError.instances` after each integration test so the
  cleanup assertion at `plugins.py:468` isn't tripped by stale entries.

> **Post-#105 update.** An earlier `_integration_neutralize_socketio`
> autouse fixture used to monkeypatch `EventController.start` to a no-op
> and force `EventController.connected` to `True` for integration tests,
> papering over a 403 handshake against the mock's `python-socketio==5.x`
> server (which only speaks Engine.IO v4 while the vendored Abode client
> speaks v3). Fixed properly in #105 by pinning the mock to SocketIO 4.x
> / Engine.IO 3.x — currently `python-socketio==4.6.1` +
> `python-engineio==3.14.2` — so the handshake succeeds and the fixture
> is gone.

The earlier `@pytest.mark.enable_socket` markers across 10 test files were
no-ops in this stack (HA-cc's `pytest_runtest_setup` re-disables sockets
*after* the marker is checked) and were removed for clarity.

## Other fixes Phase 1 needed (not in the original plan)

Enabling sockets surfaced four pre-existing issues that had been masked by
the `HASocketBlockedError` storm:

1. **Mock server's automations endpoint** — `tests/mock_server/main.py`'s
   `/integrations/v1/automations/` handler returned `[load_fixture(...)]`,
   wrapping an already-array fixture in another list. `Client._update_all`
   then errored on `state["id"]` because each `state` was a list, not a
   dict. Fixed by returning the fixture verbatim.
2. **Mock server fixtures path** — Outside Docker the volume mount that
   places fixtures at `tests/mock_server/fixtures/` doesn't exist. Added
   a fallback to `tests/fixtures/` (next to the mock_server directory)
   so the mock works for `uv run python tests/mock_server/main.py` too.
3. **`tests/test_light.py::test_light_set_color_temp`** — used `color_temp`
   in the `light.turn_on` service call; HA renamed that key to
   `color_temp_kelvin`. Test updated to the new key.
4. **`tests/integration/test_auth.py` was dead code** — its 4 tests used
   `abode.token`, `abode.user_id`, `abode.get_panel()` which no longer
   exist on `Client`. Deleted; the actual login/devices/panel paths are
   already covered by the entity tests that boot a full HA config entry.

## Step-by-step

### 1. Pre-work — verify current failure

Before any code change:

```bash
./scripts/dev.sh                           # or run the mock locally
uv run pytest tests/ -m integration --tb=line 2>&1 | tail -40
```

Expect ~100 `ERROR` results with `HASocketBlockedError`, plus the 2 known
bugs handed off to Phase 2 (`test_action_validation_errors`,
`test_coordinator_respects_enabled_state`).

### 2. Edit `tests/conftest.py`

Add the socket-gating block described above. The relevant section lives
at the bottom of the file:

- `_in_integration_test` module-level flag.
- Wrappers for `pytest_socket.disable_socket` and
  `pytest_socket.socket_allow_hosts` installed at module import time.
- `pytest_runtest_setup(item)` hookimpl with `tryfirst=True`.
- `_integration_socket_cleanup` autouse fixture for `HASocketBlockedError`
  list hygiene.

### 3. Edit `tests/mock_server/main.py`

- `/integrations/v1/automations/`: return `load_fixture("automation")` not
  `[load_fixture("automation")]`.
- `load_fixture(name)`: search both `tests/mock_server/fixtures/` (the
  Docker mount path) and `tests/fixtures/` (the layout when running
  outside Docker).

### 4. Edit `tests/test_light.py::test_light_set_color_temp`

Replace `"color_temp": 309` with `"color_temp_kelvin": 3236` in the
service call. The expected mock call still passes 3236.

### 5. Delete `tests/integration/test_auth.py`

The 4 tests in the file used dead Client API; the auth path is already
exercised by the entity integration tests. The directory's `README.md`
references sibling files (`test_panel.py`, `test_devices.py`,
`test_timeline.py`) that don't exist and never did.

### 6. Remove dead `@pytest.mark.enable_socket` decorations

Run the same edit across 10 files:

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

Remove only lines that are exactly `@pytest.mark.enable_socket`; keep
the `@pytest.mark.integration` decorator immediately above.

### 7. Verify

```bash
uv run pytest tests/ -m integration --tb=line --no-cov -q
```

Expected: 102 passed out of 104, with the 2 known bugs (#102, #103)
remaining as the only failures (handed off to Phase 2). Initially this
phase shipped an `_integration_neutralize_socketio` autouse fixture to
keep the SocketIO thread out of the loop and make the suite fully
deterministic; #105 fixed the underlying mock-server Engine.IO mismatch
and the fixture was removed.

```bash
uv run pytest tests/ -m "not integration" --no-cov -q
```

Unit suite stays at 332 passed.

### 8. Commit

```bash
git add tests/conftest.py tests/mock_server/main.py tests/test_*.py
git rm tests/integration/test_auth.py
~/.claude/scripts/commit.sh -m "test(integration): gate sockets for -m integration tests"
```

Commit body should explain the monkey-patch approach, the four
pre-existing fixes, and the marker-removal count.

## Known follow-ups (not Phase 1's job)

- **Engine.IO v3 ↔ v4 mismatch — resolved in #105.** Originally the
  vendored Abode SocketIO client spoke EIO=3 and the mock's
  `python-socketio==5.11.0` server rejected the handshake with 403.
  Phase 1 worked around it with an `_integration_neutralize_socketio`
  autouse fixture. #105 fixed it at the source by pinning the mock to
  SocketIO 4.x / Engine.IO 3.x — currently
  `python-socketio==4.6.1` + `python-engineio==3.14.2` in
  `tests/mock_server/requirements.txt`; the fixture was removed at the
  same time, and the SocketIO push path now works against the mock.

## Risk

The monkey-patch approach depends on:

- `pytest_socket.disable_socket` and `socket_allow_hosts` remaining the
  entry points HA-cc uses. They have been stable since pytest-socket 0.5.
- pluggy's `tryfirst=True` running our hookimpl before HA-cc's. Since
  pytest 7.x this has been the documented behavior.

A future pytest-socket / pytest-HA-cc bump that breaks either invariant
will surface immediately as the integration suite turning red, not as a
silent regression.
