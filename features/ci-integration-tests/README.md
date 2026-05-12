---
status: done
feature: ci-integration-tests
title: CI integration test gating
phases: 4
---

# CI Integration Test Gating (PR-8, closes #77)

## Status

**Done** — implemented across PR #108 (closes #77, #102, #103) on
2026-05-11. Follow-ups tracked as #105 (Engine.IO v3/v4 mismatch),
#106 (intermittent integration-test flakes), #107 (`tests/integration/`
placeholder cleanup).

## Goal

Make the 108 collected pytest items selected by `-m integration` run on every PR and block merges when they regress. The repository currently has 98 integration-marked test definitions; parametrization expands those to 108 collected items. They are currently silently deselected by `pyproject.toml`'s default `addopts = "-m 'not integration'"`, which CI inherits.

Closes:
- **#77** — CI gating (root issue)
- **#102** — `test_action_validation_errors` expects `validation_error`, prod returns `invalid_format`
- **#103** — `ActionManager.async_create()` no longer accepts `enabled` kwarg

#102 and #103 are bundled because they live in `tests/test_actions_integration.py`, which Phase 1 also edits to remove dead socket markers; fixing them separately would mean re-editing the same file.

## Prior attempt (closed PR #101)

PR #101 added the `integration-tests` job to `tests.yaml` and stopped there. The CI run surfaced that the suite was not actually green — ~100 tests `ERROR` with `HASocketBlockedError`, plus the two real bugs above. The 51-line workflow change itself is sound (commit `21d595de97db` in local history) and is re-used verbatim in Phase 3.

## Why option (a) — socket-enable via autouse fixture

Three architectures were considered before writing this spec (see issue #77 comment):

| | (a) socket-enable fixture | (b) split tests by surface | (c) respx in HA-fixture tests |
|---|---|---|---|
| Tests touched | conftest + cosmetic marker removal in 10 test files | ~95 entity tests rewritten | ~95 entity tests rewritten |
| Real-HTTP integration value | preserved | lost | lost |
| Effort | ~1 hour | multi-session | multi-session |
| Fragility | depends on pytest-HA-cc internals (stable for years) | none | none |

(a) was chosen. The ~95 entity tests are *the* place where "HA boots against an Abode-shaped HTTP server" is actually exercised; (b)/(c) would convert them into surface tests that aren't measurably stronger than the existing unit suite.

## The actual mechanism (why `@pytest.mark.enable_socket` didn't work)

`pytest-HA-cc/plugins.py:199` declares `pytest_runtest_setup` which unconditionally calls `pytest_socket.disable_socket(allow_unix_socket=True)` — overriding pytest-socket's `enable_socket` marker because the marker is checked earlier in the hook ordering. The 94 existing `@pytest.mark.enable_socket` decorations in the integration test files are effectively dead.

What *does* work is depending on the **`socket_enabled` fixture** (also from pytest-socket). pytest-HA-cc's own `hass_client` / `hass_ws_client` fixtures (plugins.py:906, 923, 963) already use it — fixtures run after `pytest_runtest_setup` and undo the disable.

A second gate at plugins.py:468 asserts `HASocketBlockedError.instances` is empty. Even with sockets functionally enabled, any blocked attempt during teardown (e.g. asyncio cleanup) will populate that list. The fixture must defensively clear it.

## Implementation Phases

| Phase | File | Description | Status |
|-------|------|-------------|--------|
| 1 | [phase-1-socket-fixture.md](phase-1-socket-fixture.md) | Autouse `_integration_socket_enabled` fixture in conftest; remove the 94 dead `@pytest.mark.enable_socket` decorations | planned |
| 2 | [phase-2-bug-fixes.md](phase-2-bug-fixes.md) | Fix #102 (validation error code) and #103 (async_create enabled kwarg) | planned |
| 3 | [phase-3-ci-workflow.md](phase-3-ci-workflow.md) | Re-add the `integration-tests` job in `.github/workflows/tests.yaml` from PR #101 | planned |
| 4 | [phase-4-verification.md](phase-4-verification.md) | Full local run, PR, CI monitoring, and Copilot feedback follow-up | planned |

## Acceptance criteria (from issue #77, still hold)

- CI runs the 108 collected `-m integration` pytest items on every PR.
- A regression in production code that's only covered by integration tests fails a PR check, not just a quiet local run.
- `pyproject.toml` `addopts` left unchanged (the local-default exclusion still makes sense — the CI job opts in via `-m integration`).

## Out of scope

- Re-enabling `e2e-tests.yaml` — tracked separately (issue #100).
- Re-running `pip-audit` post-`#79` cleanup — separate PR.
- Replacing the dockerized mock server with respx/aioresponses anywhere — explicitly rejected (option b/c).

## TDD approach

Phases 1 and 2 each start from a reproducible failing test signal. The fixture itself is the most ironic: the test that demonstrates the fix is the full `pytest -m integration` run going from ~100 ERROR to 0. That run replaces the usual unit-test red/green cycle for Phase 1.

For Phase 2 (#102/#103), the failing integration tests already exist in `tests/test_actions_integration.py`. The phase also adds focused WebSocket API assertions in `tests/test_websocket_api.py` so the intended error-code and `enabled` contracts are covered outside the integration suite.

Phases 3 and 4 are wiring and release phases. Their gates are YAML parsing, integration-test collection count, full local verification, and GitHub Actions status rather than new failing tests.
