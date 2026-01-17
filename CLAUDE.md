# Project: Abode Security Home Assistant Integration

## Description

Home Assistant custom integration for Abode security systems. Merges jaraco.abode with the official integration, exposing manual alarms and code optimizations (async patterns).

## Development

### Local Development Setup

Use Docker environment for all development:
```bash
./scripts/dev.sh  # Starts HA + mock Abode API server
```

**Access**:
- **Home Assistant**: http://localhost:8123 (admin/admin)
- **Mock API docs**: http://localhost:8000/docs
- **Mock credentials**: test@example.com / testpassword

### Key Commands

**Backend (Python)**:
```bash
pytest tests/                    # Run unit tests
pytest -m integration            # Run integration tests (needs mock server)
ruff check . && ruff format .   # Lint and format
mypy custom_components/          # Type check
docker logs -f abode-dev-ha      # View HA logs
```

**Frontend (TypeScript)**:
```bash
cd frontend
npm run watch                   # Dev build with hot reload
npm run build                   # Production build
```

**E2E Tests (Playwright)**:
```bash
./scripts/test-e2e.sh           # Full E2E test suite
npm run test:e2e:ui             # Interactive debug mode
```

**Docker**:
```bash
docker-compose up               # Start environment
docker-compose restart          # Restart services
docker-compose down             # Stop and remove containers
```

### Project Structure

```
abode-security/
├── custom_components/abode_security/  # Integration code
├── frontend/                          # Frontend source (TypeScript + Lit)
├── tests/
│   ├── mock_server/                   # FastAPI mock Abode API
│   ├── e2e/                           # Playwright E2E tests
│   └── test_*.py                      # Unit and integration tests
├── config/                            # Test HA config (committed)
├── scripts/                           # Dev scripts
└── docker-compose.yml                 # Dev environment
```

### Testing Approach

- **Unit tests** (`tests/test_*.py`): Fast, mocked HTTP with aioresponses
- **Integration tests** (`@pytest.mark.integration`): Use mock server, realistic API
- **E2E tests** (`tests/e2e/`): Playwright, full browser automation

Run specific types:
```bash
pytest                          # Unit only (fast, default)
pytest -m integration           # Integration only
pytest -m ""                    # All tests
npm run test:e2e               # E2E browser tests
```

## Working on Features

Use the built-in spec skills for feature development:
- `/spec-write` - Create detailed feature specifications with phases
- `/spec-implement <spec-file>` - Implement specs using TDD with progress tracking

Specs are stored in `features/[feature-name]/` with phased markdown files.

## Abode API Details

- **Polling endpoints**: Panel status, CMS settings (can rate limit - 429 errors)
- **SocketIO**: Real-time sensor updates, timeline events
- **Rate limiting**: Abode is aggressive with 429s, be careful with request frequency

### Environment Variables

- **`ABODE_BASE_URL`**: Override API URL for development
  - **Default**: `https://my.goabode.com` (production)
  - **Dev**: `http://mock-abode:8000` (set in docker-compose.yml)
  - **Production**: Never set (uses default)

## Production Deployment

See `DEPLOY.local.md` for server details (IP, user, paths). This file is gitignored.

**Commands** (replace `<user>@<host>` with actual values):
```bash
# Deploy
scp -r custom_components/abode_security <user>@<host>:/homeassistant/custom_components/

# View logs
ssh <user>@<host> 'ha core logs'
```

## Git Workflow

- **Pre-commit hook**: `.githooks/pre-commit` runs ruff, mypy, pytest
  - **Never use** `--no-verify` - all tests must pass
- **Code review**: Run `/pre-commit-review` before committing to check for security, performance, and quality issues
- **Commit format**: Standard titles (feat:, fix:, docs:, test:, chore:, ci:, refactor:)
- **Commit messages**: Brief and concise, no marketing language, no "Co-Authored-By" or "Generated with" lines
- **Branches**:
  - `main` - Stable releases
  - `develop` - Development
  - `feature/*` - Features
  - `fix/*` - Bug fixes

## CI/CD

**GitHub Actions**:
- `.github/workflows/tests.yaml` - Python + Frontend (every push/PR)
- `.github/workflows/e2e-tests.yaml` - E2E tests (manual, currently disabled)
- `.github/workflows/validate.yaml` - HACS validation

## Better Development Feature

**Status**: Complete. See `features/better-development/` for details.
