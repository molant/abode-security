---
status: planned
phase: 4
feature: ci-integration-tests
title: Full verification, PR, and Copilot review
---

# Phase 4: Full Verification, PR, and Copilot Review

**Status**: planned

## Goal

Land the work as a PR that closes #77, #102, #103. Follow the project's standard PR Copilot review flow.

## Step 4.1 — Full local verification

Branch should now have:
- [Phase 1](phase-1-socket-fixture.md): conftest fixture + 94 marker removals (1 commit)
- [Phase 2](phase-2-bug-fixes.md): 2 commits, one per bug
- [Phase 3](phase-3-ci-workflow.md): 1 commit, CI workflow

Run the Python local quality gate used by `.githooks/pre-commit`:

```bash
./scripts/check.sh
```

This mirrors the Python lint, typecheck, and non-integration pytest gates. The hook runs frontend gates only when frontend files are staged; this phase runs them explicitly below so the PR body can report the result.

Then the integration suite:

```bash
./scripts/dev.sh
uv run pytest tests/ -m integration -v --tb=short 2>&1 | tail -10
```

Then the *combined* run (everything):

```bash
uv run pytest tests/ -m "" -v --tb=short 2>&1 | tail -10
```

Expected: 332 non-integration items + 108 integration items = **440 pytest items pass**, 0 fail, 0 error.

Frontend, for completeness (Phase 3 changes don't touch frontend, but a green frontend run rules out unrelated rot):

```bash
npm --prefix frontend test
```

## Step 4.2 — Pre-commit review

Per `CLAUDE.md`: "Before committing non-trivial changes, run `/pre-commit-review`."

Run this after staging the intended commits and before push. Address anything flagged before continuing. If the slash command is not available in the current environment, perform the same review manually against `git diff --cached`, checking especially for unrelated file churn, stale line-number references in these spec docs, and accidental changes to `pyproject.toml`'s default `addopts`.

## Step 4.3 — Push branch

Branch name suggestion: `feature/ci-integration-tests` (matches the `feature/*` convention in CLAUDE.md). If the user prefers `fix/77-integration-tests-ci` to highlight the issue, that's equally valid.

```bash
git push -u origin feature/ci-integration-tests
```

## Step 4.4 — Open the PR

```bash
gh pr create --title "ci: gate integration tests + fix #102/#103" --body "$(cat <<'EOF'
## Summary

- Adds an `integration-tests` job to `tests.yaml` that runs the 108 collected `-m integration` pytest items against a dockerized mock Abode server.
- Adds `tests/conftest.py::_integration_socket_enabled` autouse fixture so integration tests can open sockets despite pytest-HA-cc's per-test `disable_socket` call (the dead `@pytest.mark.enable_socket` markers were removed).
- Fixes the two real bugs that the gating attempt surfaced: `actions/create` returns inconsistent validation error codes (#102), and `ActionManager.async_create` lost its `enabled` kwarg (#103).

## Context

Second attempt at #77 — supersedes closed PR #101. The first attempt added the workflow YAML but the test surface beneath it wasn't green; ~100 tests errored with `HASocketBlockedError` and 2 had real bugs. This PR addresses both.

Architecture choice (3 options weighed in #77 comment thread): the per-marker fixture, not a test-surface split. Preserves the real-HTTP integration value of the 95 entity tests at the cost of a one-fixture dependency on a stable pytest-HA-cc internal.

## Test plan

- [x] `./scripts/check.sh` — 332 non-integration pytest items + lint + typecheck pass
- [x] `uv run pytest tests/ -m integration` — 108 pytest items pass
- [x] `uv run pytest tests/ -m ""` — full 440 pytest items pass
- [x] `npm --prefix frontend test` — frontend tests pass
- [ ] CI `Integration Tests` job goes green on this PR

Closes #77.
Closes #102.
Closes #103.
EOF
)"
```

## Step 4.5 — Request Copilot review

Per the project feedback flow: after `gh pr create`, request `Copilot` as reviewer, wait about 10 minutes, then run `/address-pr-feedback`.

```bash
gh pr edit --add-reviewer Copilot
```

Then wait ~10 minutes, then:

```
/address-pr-feedback
```

If the slash command is unavailable, inspect unresolved PR review threads and top-level comments manually with `gh pr view --comments` plus the GitHub UI, then address only actionable feedback.

## Step 4.6 — Monitor CI

After push, watch the `Integration Tests` job specifically:

```bash
gh pr checks --watch
```

If it goes red, the failure mode is one of:
- **Mock-server container fails to boot** → `docker compose logs mock-abode` step shows why. Likely a dependency change in `tests/mock_server/`.
- **Tests fail in CI but pass locally** → almost certainly an environment difference. Suspect `MOCK_SERVER_URL`, Docker network DNS, or a fixture that's session-scoped and order-dependent.
- **The `_integration_socket_enabled` fixture's `HASocketBlockedError` import fails** → pytest-HA-cc upgraded mid-flight and renamed the symbol. Pin or adapt.

## Step 4.7 — Merge

Once green and Copilot is satisfied:

```bash
gh pr merge --squash --delete-branch
```

(Or `--merge` if the user prefers per-commit history — current `git log` on `main` shows squash-merge style is the project default.)

## Post-merge checklist

- [ ] Issue #77 closes automatically (via `Closes #77` footer).
- [ ] Issues #102 and #103 close automatically.
- [ ] Confirm the `Integration Tests` job runs on the *next* PR.
- [ ] Update `features/pending.md` if it tracks #77 / #102 / #103 — remove the entries.
- [ ] Per PR-8 in the original plan: this closes the last project-plan CI item. Mention in any project-status update.

## What's deliberately not done

- No retroactive cleanup of `verify_cleanup` warnings if any non-integration unit tests open sockets and never trip the assert today — those would need their own investigation and are out of scope.
- No `socket_allow_hosts` widening for the integration tests. They only need `localhost`/`127.0.0.1`, which is already allowed by pytest-HA-cc's defaults.
- No reorganization of `tests/integration/` — keeping `tests/test_*.py` integration tests adjacent to their unit counterparts is intentional (per the option (a) rationale).
