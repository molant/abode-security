---
status: planned
phase: 3
feature: ci-integration-tests
title: Add integration-tests CI job
---

# Phase 3: Add `integration-tests` Job to tests.yaml

**Status**: planned

## Goal

Wire the 108 collected `-m integration` pytest items into `tests.yaml` so every PR runs them. Reuse the workflow change from closed PR #101 — the YAML itself was sound; only the test surface beneath it wasn't.

## Source of truth: PR #101 commit

The exact 51-line addition lives in local git as commit `21d595de97db` ("ci: gate 108 integration tests in CI"). Recover with:

```bash
git show 21d595de97db -- .github/workflows/tests.yaml
```

Apply that diff verbatim. The design decisions baked into it are still correct (validated during the architecture call in the README):

- **Second job in tests.yaml**, not a new workflow file. Jobs parallelize within the workflow; failure attribution is by job name, not by file path.
- **Required check** (no `continue-on-error`). The 2 bugs Phase 2 fixed were the only "flake" risks; tests pass now.
- **Workflow owns the mock-server container lifecycle**. `tests/conftest.py` `mock_server` fixture (lines 177-228) detects an already-running server at `MOCK_SERVER_URL` and skips its own `docker-compose` call — so the CI workflow can start/stop the container in dedicated steps, giving clear failure attribution between "server failed to boot" and "tests failed against running server".
- **`-o addopts="--cov=... --cov-report=..."` explicitly overrides `pyproject.toml`'s `addopts`** which contains `-m 'not integration'`. Without this override, the CI invocation would rely on pytest's rightmost-`-m`-wins semantics — fragile across pytest versions, and silent if it ever regresses (zero tests would "pass", reintroducing the #77 bug exactly as it was).

## Step 3.1 — Apply the YAML change

**File**: `.github/workflows/tests.yaml`

Insert immediately after the existing Python unit-test job, before the `frontend-build` job:

```yaml
  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build and start mock Abode server
        # The conftest mock_server fixture detects an already-running server
        # at MOCK_SERVER_URL and skips its own docker-compose call, so we
        # manage container lifecycle here for clearer failure attribution.
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
        # Override pyproject's `addopts = "... -m 'not integration'"` explicitly.
        # Without `-o addopts=...`, this job would rely on pytest's rightmost-`-m`-wins
        # CLI override semantics — fragile across pytest versions, and silent if it
        # ever regresses (zero tests would "pass", reintroducing the #77 bug).
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
python -c "import yaml; yaml.safe_load(open('.github/workflows/tests.yaml'))" && echo "valid"
```

If `actionlint` is available locally:

```bash
actionlint .github/workflows/tests.yaml
```

## Step 3.3 — Confirm the docker-compose service name

The job references `mock-abode` in the `docker compose up -d --build mock-abode` and log commands (matching the project's `docker-compose.yml`). Confirm the service name hasn't drifted:

```bash
rg -n "^  (mock-abode|[a-z-]+):" docker-compose.yml
```

Service name must match the `up -d` argument and the log step. The final `docker compose down` stops the project, not an individual service.

## Step 3.4 — Confirm pytest can be invoked with the override

This is the same check PR #101 did — re-run it on the current `main` (post-Phase-1-and-2) to be sure:

```bash
uv run pytest tests/ -o addopts="--cov=custom_components/abode_security --cov-report=term-missing" -m integration --collect-only -q 2>&1 | tail -10
```

Must show 108 selected integration items and 332 deselected non-integration items, for 440 total collected items. Pytest's exact wording varies by version; accept equivalent summaries such as `108/440 tests collected`, `108 selected, 332 deselected`, or a full node-id list followed by the same totals. If it prints anything other than 108 selected items, [Phase 1](phase-1-socket-fixture.md) or [Phase 2](phase-2-bug-fixes.md) changed the marker set or parametrization by accident.

## Step 3.5 — Commit

```bash
git add .github/workflows/tests.yaml
git commit -m "ci: gate 108 integration tests in CI"
```

Reuse the commit message body from `21d595de97db` (see `git show 21d595de97db`) — the rationale carries over unchanged.

## Open follow-ups (NOT this PR)

- Re-enabling `e2e-tests.yaml` (Playwright) — tracked in #100.
- Splitting Python+integration into separate workflows for parallelism — not needed at current test volume.
- Caching the mock-server Docker image build between runs — Docker layer cache is already on by default for `docker compose build`; revisit if the build step exceeds ~30s.

## What success looks like

After pushing the branch:
- The `Integration Tests` check appears alongside `tests` and `Build Frontend`.
- It goes red on the first push of a PR that breaks an integration test.
- It goes green on the first push of this PR.
