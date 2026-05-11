# Project: Abode Security Home Assistant Integration

Home Assistant custom integration for Abode security systems. Merges `jaraco.abode` (embedded under `custom_components/abode_security/abode/`, modernized with async patterns) with the official HA integration, and adds manual alarm triggering plus a custom actions system.

Design and data flow: [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md).

## Development environment

```bash
./scripts/dev.sh    # HA + mock Abode API in Docker
./scripts/check.sh  # lint + typecheck + unit tests (same as pre-commit hook)
```

- HA: http://localhost:8123 (admin/admin)
- Mock API docs: http://localhost:8000/docs
- Mock creds: test@example.com / testpassword

Quality gates (`ruff`, `mypy`, `pyright`, `pytest`) are enforced by `.githooks/pre-commit`. Don't bypass with `--no-verify`; fix the underlying issue. `check.sh` runs the same set locally. All tools run through `uv run` against `pyproject.toml [project.optional-dependencies].dev`.

## Testing tiers

- Unit (`tests/test_*.py`) — default `uv run pytest` run, HTTP mocked with `aioresponses`
- Integration (`uv run pytest -m integration`) — needs the mock server (`./scripts/dev.sh`)
- E2E (`./scripts/test-e2e.sh`) — Playwright against the live Docker stack

`uv run pytest -m ""` runs everything.

### Testing gotchas

- **Frontend tests** — `cd frontend && npm test` runs `web-test-runner` against `frontend/src/__tests__/*.test.ts` (Playwright-backed, `@open-wc/testing`). CI runs them via `npm test` in `tests.yaml` alongside lint, format, typecheck, and build.

## Abode API quirks

- Polling endpoints (panel status, CMS settings) rate-limit aggressively with 429s — be conservative with request frequency
- Real-time updates come through SocketIO, not polling — most state changes should be event-driven
- Session timeout is ~1.5h; the client proactively recreates sessions every 30 min

## Environment variables

- `ABODE_BASE_URL` — override API URL
  - Default: `https://my.goabode.com` (production)
  - Dev: `http://mock-abode:8000` (set in `docker-compose.yml`)
  - Never set in production

## Production deployment

Host details (IP, user, paths) are in `DEPLOY.local.md` (gitignored). Deploy pattern:

```bash
scp -r custom_components/abode_security <user>@<host>:/homeassistant/custom_components/
ssh <user>@<host> 'ha core logs'
```

## Feature workflow

- Specs live in `features/<feature-name>/` with phased markdown files
- `features/pending.md` tracks deferred work

## Git conventions

- Branches: `main` (stable), `develop`, `feature/*`, `fix/*`
- Commit prefix: `feat:` / `fix:` / `docs:` / `test:` / `chore:` / `ci:` / `refactor:`
- Commit messages: brief, factual, no marketing language
- Before committing non-trivial changes, run `/pre-commit-review`

## CI/CD

- `.github/workflows/tests.yaml` — Python + frontend (every push/PR)
- `.github/workflows/e2e-tests.yaml` — E2E (manual trigger, currently disabled)
- `.github/workflows/validate.yaml` — HACS validation
