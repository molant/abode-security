---
status: done
phase: 3
feature: ci-integration-tests
title: Add integration-tests CI job
---

# Phase 3: Add `integration-tests` Job to tests.yaml

**Status**: done

## Goal

Wire the 104 collected `-m integration` pytest items into `tests.yaml` so
every PR runs them. Reuse the workflow change from closed PR #101 — the
YAML itself was sound; only the test surface beneath it wasn't (fixed in
Phase 1 and Phase 2).

## Deviations from the original plan

The original Phase 3 spec expected 108 collected integration items.
Reality after Phases 1–2:

- **104 collected, not 108.** Phase 1 deleted `tests/integration/test_auth.py`
  (4 dead tests using removed Client API), so the new total is 104. The
  number is informational; the workflow doesn't hard-code it.
- **No `--reruns` flag in the final shape.** An earlier draft of this
  phase added `pytest-rerunfailures` and `--reruns=2`/`--reruns-delay=1`
  to paper over async-timing flakes; the first CI run pushed the budget
  to `--reruns=3 --reruns-delay=2` because two CI-deterministic alarm
  tests still failed. The proper fix landed in Phase 1's
  `_integration_neutralize_socketio` autouse fixture (neutralises the
  vendored Abode SocketIO client whose `EIO=3` handshake gets 403 from
  the mock's python-socketio v4 server). With the fixture in place the
  suite is fully deterministic; both the dev-dep and the CLI flags were
  dropped in commit-cleanup, so the workflow ends up applying PR #101's
  diff almost verbatim.

## Source of truth: PR #101 commit

Recover the workflow diff with:

```bash
git show 21d595de97db -- .github/workflows/tests.yaml
```

The design decisions baked into it are still correct:

- **Second job in tests.yaml**, not a new workflow file. Jobs parallelize
  within the workflow; failure attribution is by job name, not by file
  path.
- **Required check** (no `continue-on-error`). Phase 2 fixed the only two
  deterministic failures; Phase 1's SocketIO-neutralisation fixture
  eliminates the residual async-timing flakes.
- **Workflow owns the mock-server container lifecycle**.
  `tests/conftest.py`'s session-scope `mock_server` fixture detects an
  already-running server at `MOCK_SERVER_URL` and skips its own
  `docker-compose` call — so the workflow can start/stop the container
  in dedicated steps, giving clear failure attribution between "server
  failed to boot" and "tests failed against running server".
- **`-o addopts="--cov=... --cov-report=..."` explicitly overrides
  `pyproject.toml`'s `addopts`** which contains `-m 'not integration'`.
  Without this override, the CI invocation would rely on pytest's
  rightmost-`-m`-wins semantics — fragile across pytest versions, and
  silent if it ever regresses (zero tests would "pass", reintroducing the
  #77 bug exactly as it was).

## Step 3.1 — Apply the YAML change

**File**: `.github/workflows/tests.yaml`

Insert immediately after the existing Python unit-test job, before the
`frontend-build` job. The block is in `tests.yaml` lines 43–101 of the
committed version:

```yaml
  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build and start mock Abode server
        run: docker compose up -d --build mock-abode

      - name: Wait for mock server health
        run: |
          for i in {1..60}; do
            if curl -sf http://localhost:8000/health > /dev/null; then
              echo "Mock server ready"
              exit 0
            fi
            sleep 1
          done
          echo "Mock server failed to become ready within 60s"
          docker compose logs mock-abode
          exit 1

      - name: Install uv
        uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Run integration tests
        run: |
          uv run pytest tests/ \
            -o addopts="--cov=custom_components/abode_security --cov-report=term-missing" \
            -m integration -v --tb=short

      - name: Show mock server logs on failure
        if: failure()
        run: docker compose logs mock-abode

      - name: Stop mock server
        if: always()
        run: docker compose down
```

## Step 3.2 — Verify the YAML parses

```bash
uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/tests.yaml'))" && echo VALID
```

If `actionlint` is available locally:

```bash
actionlint .github/workflows/tests.yaml
```

## Step 3.3 — Confirm the docker-compose service name

The job references `mock-abode` in the `docker compose up -d --build mock-abode`
and `logs` commands. Confirm the service name hasn't drifted:

```bash
grep -E "^  [a-z][a-z-]*:" docker-compose.yml
```

Must include `mock-abode`. The final `docker compose down` stops the
project, not an individual service.

## Step 3.4 — Confirm pytest can be invoked with the override

```bash
uv run pytest tests/ \
  -o addopts="--cov=custom_components/abode_security --cov-report=term-missing" \
  -m integration --collect-only -q 2>&1 | tail -5
```

Must show 104 selected integration items and 333 deselected non-integration
items, for 437 total collected items. If it prints anything other than 104
selected items, Phase 1 or Phase 2 changed the marker set or parametrisation
by accident.

## Step 3.5 — Smoke-test the suite locally

```bash
uv run pytest tests/ \
  -o addopts="--cov=custom_components/abode_security --cov-report=term-missing" \
  -m integration -v --tb=short 2>&1 | tail -3
```

Expect `104 passed`. If you see any `failed` lines, that's a real
regression — Phase 2 didn't close all the gaps, or a new commit on
`main` broke something.

## Step 3.6 — Commit

```bash
git add .github/workflows/tests.yaml \
        features/ci-integration-tests/phase-3-ci-workflow.md
~/.claude/scripts/commit.sh -m "ci: gate integration tests on every PR"
```

Commit body should explain:

- What the job does (104 integration items, dockerized mock server).
- Why `-o addopts=...` is mandatory (rightmost-`-m`-wins fragility).
- Reference closed PR #101 as prior art.

## Open follow-ups (NOT this PR)

- Re-enabling `e2e-tests.yaml` (Playwright) — tracked in #100.
- Splitting Python + integration into separate workflows for parallelism
  — not needed at current test volume.
- Engine.IO v3↔v4 mismatch between the vendored Abode SocketIO client
  and python-socketio 5.x. Eliminating this would let us drop Phase 1's
  `_integration_neutralize_socketio` fixture and exercise the SocketIO
  push path against the mock too. Tracked as #105.

## What success looks like

After pushing the branch:

- The `Integration Tests` check appears alongside `tests` and
  `Build Frontend`.
- It goes red on the first push of a PR that breaks an integration test
  in a deterministic way (no test passes twice after two retries).
- It goes green on the first push of this PR.
