# Abode Security Integration - Development Guide

This guide covers local development, testing, and contribution workflows for the Abode Security Home Assistant integration.

## Table of Contents
- [Quick Start](#quick-start)
- [Development Workflows](#development-workflows)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Mock Abode API Server](#mock-abode-api-server)
- [Environment Variables](#environment-variables)
- [Git Workflow](#git-workflow)
- [CI/CD](#cicd)
- [Troubleshooting](#troubleshooting)
- [Production Deployment](#production-deployment)

## Quick Start

### Prerequisites
- **Docker** and Docker Compose (or Colima on macOS)
- **Node.js 20+** (see `frontend/.nvmrc`)
- **Python 3.14.2+** (pinned by `pytest-homeassistant-custom-component`'s
  bundled `homeassistant` release; `uv` will install a matching interpreter
  automatically if your system Python is older)
- **uv** (https://docs.astral.sh/uv/getting-started/installation/) — manages
  Python, the project venv, and all dev dependencies via `uv.lock`
- **Git** for version control

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/molant/abode-security.git
   cd abode-security
   ```

2. **Install dev dependencies**
   ```bash
   ./scripts/setup-dev.sh
   # or, equivalently:
   uv sync --extra dev
   ```
   `uv` creates and manages `.venv/` for you — no separate `python -m venv`
   step. Run all dev tools through `uv run …` (or activate `.venv` manually).

3. **Start Docker** (if using Colima on macOS)
   ```bash
   colima start
   ```

4. **Start the development environment**
   ```bash
   ./scripts/dev.sh
   ```

   This starts:
   - **Home Assistant** on http://localhost:8123
   - **Mock Abode API server** on http://localhost:8000

5. **Access Home Assistant**
   - URL: http://localhost:8123
   - Username: `admin`
   - Password: `admin`

6. **Configure Abode Integration**
   - Go to Settings → Devices & Services → Add Integration → Abode Security
   - Use test credentials:
     - Email: `test@example.com`
     - Password: `testpassword`

7. **Verify integration loaded**
   - Check sidebar for "Abode" panel (shield icon)
   - Go to Settings → Devices & Services → Abode Security

## Development Workflows

### Backend Development

**Location**: `custom_components/abode_security/`

The integration code runs inside the Home Assistant Docker container with live file mounting.

#### Make Changes
1. Edit Python files in `custom_components/abode_security/`
2. Reload the integration in HA (Settings → Devices & Services → Abode Security → Reload)

#### View Logs
```bash
docker logs -f abode-dev-ha
```

Or use HA's built-in logs:
- Settings → System → Logs

#### Run Tests
```bash
# Fast unit tests (mocked HTTP)
uv run pytest tests/ -v

# Integration tests (requires mock server)
docker-compose up -d mock-abode
uv run pytest -m integration -v

# Run specific test file
uv run pytest tests/test_config_flow.py -v

# Run all tests with the script
./scripts/run_all_tests.sh
```

#### Linting and Type Checking
```bash
# Check code style
uv run ruff check .

# Format code
uv run ruff format .

# Type check (both run in CI; mypy + pyright catch different classes of issue)
uv run mypy custom_components/abode_security/
uv run pyright custom_components/abode_security/
```

**Pre-commit Hook**: All checks run automatically before commit. Never use `--no-verify`.

### Frontend Development

**Location**: `frontend/`

#### Setup
```bash
cd frontend
npm install
```

#### Development Build (with watch mode)
```bash
npm run watch
```

This:
- Watches `frontend/src/` for changes
- Auto-rebuilds on save
- Outputs to `custom_components/abode_security/www/`
- Includes source maps for debugging

#### Make Changes
1. Edit TypeScript files in `frontend/src/`
2. Save (Rollup auto-rebuilds)
3. Refresh browser to see changes (Ctrl+Shift+R for hard refresh)

#### Production Build
```bash
npm run build
```

Outputs minified bundle without source maps.

#### Development Workflow
**Terminal 1** - Docker environment:
```bash
./scripts/dev.sh
```

**Terminal 2** - Frontend watcher:
```bash
cd frontend
npm run watch
```

**Browser** - http://localhost:8123
- Navigate to Abode panel in sidebar
- Make changes in `frontend/src/abode-panel.ts`
- Refresh browser to see updates

### End-to-End Testing

**Run all E2E tests**:
```bash
./scripts/test-e2e.sh
```

**Run with UI** (for debugging):
```bash
docker-compose up -d
npm run test:e2e:ui
```

**Run specific test**:
```bash
npx playwright test abode-panel.spec.ts
```

**Debug mode**:
```bash
npm run test:e2e:debug
```

**View test report**:
```bash
npm run test:e2e:report
```

## Testing

### Test Types

#### Unit Tests (`tests/test_*.py`)
- **Speed**: Very fast (no network)
- **Mocking**: Uses `aioresponses` to mock HTTP
- **Use**: TDD, quick feedback during development

```bash
uv run pytest tests/test_config_flow.py -v
```

#### Integration Tests (`tests/test_*.py` with `@pytest.mark.integration`)
- **Speed**: Moderate (uses mock server)
- **Mocking**: Real HTTP to mock Abode API server
- **Use**: Realistic API interaction testing

```bash
docker-compose up -d mock-abode
uv run pytest -m integration -v
```

#### E2E Tests (`tests/e2e/`)
- **Speed**: Slow (full browser automation)
- **Mocking**: Real browser, real HA, mock API
- **Use**: End-to-end verification before release

```bash
./scripts/test-e2e.sh
```

### Test Markers

Run specific test types:
```bash
# Unit tests only (fast, default)
uv run pytest

# Integration tests only
uv run pytest -m integration

# All tests
uv run pytest -m ""
```

## Project Structure

```
abode-security/
├── custom_components/
│   └── abode_security/              # Integration code
│       ├── abode/                   # Vendored Abode client library
│       ├── www/                     # Frontend build output
│       ├── __init__.py              # Integration setup
│       ├── config_flow.py           # Configuration UI
│       ├── alarm_control_panel.py   # Alarm entity platform
│       ├── sensor.py                # Sensor entity platform
│       ├── switch.py                # Switch entity platform
│       └── ...                      # Other platforms
│
├── frontend/                        # Frontend source code
│   ├── src/                         # TypeScript source files
│   │   ├── abode-panel.ts           # Main panel component
│   │   └── types.ts                 # Type definitions
│   ├── package.json                 # Build scripts
│   ├── rollup.config.js             # Bundler configuration
│   └── tsconfig.json                # TypeScript configuration
│
├── tests/                           # Tests
│   ├── mock_server/                 # FastAPI mock Abode API
│   │   ├── main.py                  # Mock server implementation
│   │   ├── Dockerfile               # Container build
│   │   └── README.md                # API documentation
│   ├── e2e/                         # Playwright E2E tests
│   │   ├── fixtures/                # Test utilities
│   │   └── *.spec.ts                # Test files
│   └── test_*.py                    # Unit and integration tests
│
├── config/                          # Test HA instance configuration
│   ├── configuration.yaml           # HA configuration
│   └── .storage/                    # Pre-configured user/settings
│
├── scripts/                         # Development scripts
│   ├── dev.sh                       # Start dev environment
│   ├── test-e2e.sh                  # Run E2E tests
│   └── run_all_tests.sh             # Run all test suites
│
├── .github/workflows/               # CI/CD
│   ├── tests.yaml                   # Python + Frontend CI
│   ├── e2e-tests.yaml               # E2E tests (manual)
│   └── validate.yaml                # HACS validation
│
├── features/                        # Feature documentation
│   └── better-development/          # Dev infrastructure feature
│
├── docker-compose.yml               # Dev environment
├── playwright.config.ts             # E2E test configuration
└── pyproject.toml                   # Python project configuration
```

## Mock Abode API Server

The mock server simulates Abode's API for local testing without hitting production.

**URL**: http://localhost:8000
**Docs**: http://localhost:8000/docs (FastAPI auto-generated)

### Key Endpoints
- `POST /api/auth2/login` - Authentication
- `GET /api/auth2/claims` - OAuth token
- `GET /api/v1/panel` - Panel status
- `PUT /api/v1/panel/mode/{area}/{mode}` - Set alarm mode
- `GET /api/v1/devices` - Device list
- `GET /api/v1/timeline` - Event timeline
- `GET /integrations/v1/cms/settings` - Monitoring settings
- `POST /api/test/reset` - Reset state (testing)

### Test Credentials
- **Email**: `test@example.com`
- **Password**: `testpassword`

### Example Usage
```bash
# Login
curl -X POST http://localhost:8000/api/auth2/login \
  -H "Content-Type: application/json" \
  -d '{"id":"test@example.com","password":"testpassword"}'

# Set panel mode
curl -X PUT http://localhost:8000/api/v1/panel/mode/area_1/away

# Get devices
curl http://localhost:8000/api/v1/devices

# Reset state (between tests)
curl -X POST http://localhost:8000/api/test/reset
```

## Environment Variables

### Development
- **`ABODE_BASE_URL`**: Override Abode API base URL
  - Default: `https://my.goabode.com` (production)
  - Dev: `http://mock-abode:8000` (set in docker-compose.yml)
  - Production: Do not set (uses default)

Set in `docker-compose.yml`:
```yaml
environment:
  - ABODE_BASE_URL=http://mock-abode:8000
```

## Git Workflow

### Branching
- `main` - Stable releases
- `develop` - Development branch
- `feature/*` - Feature branches
- `fix/*` - Bug fix branches

### Commit Messages
Use conventional commit format:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `test:` - Test updates
- `chore:` - Maintenance tasks
- `ci:` - CI/CD changes
- `refactor:` - Code refactoring

Example:
```
feat: Add support for wireless door locks

- Implement lock entity platform
- Add lock/unlock service calls
- Add tests for lock operations

Closes #123
```

### Pre-commit Hooks
Located at `.githooks/pre-commit`. Automatically runs (via `uv run`):
- `ruff check` and `ruff format` (linting)
- `mypy` and `pyright` (type checking)
- `pytest` (tests)

**All checks must pass**. Never use `--no-verify`.

## CI/CD

### GitHub Actions Workflows

#### tests.yaml (Active)
Runs on every push/PR to main or develop:
- **Python**: dependencies via `uv sync --extra dev`, then linting (ruff),
  type checking (mypy + pyright), unit tests (pytest) — all through `uv run`
- **Frontend**: build verification, bundle output check

#### e2e-tests.yaml (Manual)
Triggered manually via workflow_dispatch:
- Starts Docker environment
- Runs Playwright browser tests
- Uploads reports/videos on failure

**Currently disabled** (`if: false`). To enable:
1. Remove `if: false` from workflow
2. Optionally enable on PR trigger

#### validate.yaml (Active)
Validates HACS manifest, strings, icons.

### Running CI Checks Locally

**All Python checks**:
```bash
./scripts/check.sh
# or, individually:
uv run ruff check . && uv run ruff format --check .
uv run mypy custom_components/abode_security/
uv run pyright custom_components/abode_security/
uv run pytest tests/
```

**Frontend build**:
```bash
cd frontend
npm ci
npm run build
```

**Full local CI**:
```bash
./scripts/dev.sh
./scripts/check.sh
cd frontend && npm run build && cd ..
npm run test:e2e
```

## Troubleshooting

### Docker won't start
```bash
# Check if Docker is running
docker ps

# On macOS with Colima
colima status
colima start
```

### Port 8123 already in use
```bash
# Find and kill the process
lsof -i :8123
kill -9 <PID>
```

### Integration not loading
**Check HA logs**:
```bash
docker logs -f abode-dev-ha
```

**Common issues**:
- Mock server not running: `docker-compose ps` (check both containers)
- Wrong API URL: `docker exec abode-dev-ha env | grep ABODE`
- Syntax error in code: Check logs for Python tracebacks

**Solution**:
```bash
docker-compose restart
docker logs -f abode-dev-ha
```

### Frontend changes not appearing
**Check build output**:
```bash
ls -lh custom_components/abode_security/www/
```

**Common issues**:
- Rollup not watching: Restart `npm run watch`
- Browser cache: Hard refresh (Ctrl+Shift+R)
- Wrong file path: Check rollup.config.js output path

**Solution**:
```bash
cd frontend
npm run build
# Then hard refresh browser
```

### Tests failing
**Reset mock server**:
```bash
curl -X POST http://localhost:8000/api/test/reset
```

**Common issues**:
- Mock server not running: `docker-compose up -d mock-abode`
- Stale test state: Reset mock server between tests
- Python version mismatch: `python --version` (should be 3.14.2+; `uv` can
  install a matching interpreter automatically — see `uv python install`)

**Solution**:
```bash
docker-compose restart mock-abode
uv run pytest tests/ --tb=short
```

### E2E tests flaky
**Increase timeouts** in `playwright.config.ts`:
```typescript
timeout: 30000,  // 30 seconds per test
```

**Run in headed mode** to see what's happening:
```bash
npm run test:e2e:headed
```

**Check HA is ready**:
```bash
curl http://localhost:8123
```

### Docker issues
**Containers won't start**:
```bash
docker-compose down
docker-compose up --build
```

**Port conflicts**:
```bash
lsof -i :8123  # Check what's using port 8123
lsof -i :8000  # Check what's using port 8000
```

**Clean everything**:
```bash
docker-compose down -v  # Remove volumes too
docker-compose up --build
```

## Production Deployment

### SSH Access
```bash
ssh molant@192.168.1.60
```

### Deploy Integration
```bash
# From local machine
scp -r custom_components/abode_security molant@192.168.1.60:/homeassistant/custom_components/
```

### Restart Home Assistant
```bash
# On remote machine
ssh molant@192.168.1.60 'ha core restart'
```

### View Logs
```bash
ssh molant@192.168.1.60 'ha core logs'
```

### Production Checklist
- [ ] All tests passing locally
- [ ] CI checks passing on GitHub
- [ ] Frontend built with production config
- [ ] Version updated in `manifest.json`
- [ ] CHANGELOG updated
- [ ] Tested in dev environment
- [ ] `ABODE_BASE_URL` NOT set in production

## Additional Resources

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Integration Structure](https://developers.home-assistant.io/docs/creating_integration_file_structure)
- [Config Flow](https://developers.home-assistant.io/docs/config_entries_config_flow_handler)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

Quick start:
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes
4. Run tests: `uv run pytest tests/ && npm run test:e2e`
5. Commit: `git commit -m "feat: Add my feature"`
6. Push: `git push origin feature/my-feature`
7. Create Pull Request

## Support

- GitHub Issues: https://github.com/molant/abode-security/issues
- Original Library: https://github.com/molant/jaraco.abode
