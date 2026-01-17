# Abode Security Integration - Better Development Environment Plan

**Status**: ✅ Complete (2025-01-16)

## Phase 1: Docker Dev Environment Setup (2025-12-17)

- [x] Create docker-compose.yml at repo root with:
- [x] Home Assistant container (stable image)
- [x] Volume mount for custom_components/abode_security
- [x] Volume mount for test HA config
- [x] Network configuration for mock server communication
- [x] Create config/ directory for test HA instance:
- [x] configuration.yaml with abode_security integration configured
- [x] Pre-configured test user in .storage/auth
- [x] Pre-configured dashboard in .storage/lovelace
- [x] Onboarding marked complete in .storage/onboarding
- [x] Create scripts/dev.sh for starting dev environment
- [x] Verify integration loads and hot reload works (restart integration on file change)

## Phase 2: Mock Abode API Server (2025-12-17)

- [x] Create tests/mock_server/ directory
- [x] Implement FastAPI mock server with:
- [x] Auth endpoint (username/password → token)
- [x] Panel status endpoint (get/set alarm mode)
- [x] Devices endpoint returning fixture data:
- [x] Motion sensors (2-3)
- [x] Contact/door sensors (2-3)
- [x] Smoke sensor (1)
- [x] Device status update endpoints
- [x] State reset endpoint for test cleanup
- [x] Create tests/mock_server/Dockerfile
- [x] Add mock server to docker-compose.yml
- [x] Document mock server endpoints in tests/mock_server/README.md

## Phase 3: Integration URL Configuration (2025-12-17)

- [x] Add base_url parameter to abode/ client
- [x] Thread base_url through integration setup (env var ABODE_BASE_URL)
- [x] Update config flow if needed (optional override for advanced users?)
- [x] Test integration connects to mock server successfully
- [x] Ensure production default remains unchanged

## Phase 4: Migrate/Update Existing Tests (2025-12-17)

- [x] Audit current tests in tests/ - identify what exists
- [x] Update pytest fixtures to use mock server where applicable
- [x] Add conftest.py fixtures for:
- [x] Mock server URL configuration
- [x] HA test instance helpers (if using HA test framework)
- [x] Common test data/fixtures
- [x] Ensure all existing tests pass with new setup
- [x] Update requirements_dev.txt if new dependencies needed

**Note:** Test infrastructure expanded in phases 4.5.x with 101 tests passing, 125 skipped (integration tests require mock server).

## Phase 5: Frontend Dev Workflow (2025-01-16)

**Note:** Created new frontend infrastructure from scratch. Initial implementation is a sidebar panel showing "Abode Configuration" text.

- [x] Create frontend/ source structure:
  - [x] src/ directory for TypeScript source files
  - [x] package.json with build scripts and dependencies
  - [x] rollup.config.js with cache busting configuration
  - [x] tsconfig.json for TypeScript compilation
  - [x] .nvmrc for Node version consistency
- [x] Implement initial panel component:
  - [x] Simple Lit component showing "Abode Configuration"
  - [x] Proper Home Assistant panel registration
  - [x] Basic styling with HA design system
- [x] Add package.json scripts:
  - [x] build - production build to custom_components/abode_security/www/
  - [x] watch - rebuild on changes for development
  - [x] dev - watch with source maps for debugging
- [x] Test hot reload workflow:
  - [x] Change TS source → auto rebuild → refresh dashboard → see changes
- [x] Document local frontend development workflow

**Implementation notes:**
- Panel registration uses `async_register_static_paths` with `StaticPathConfig`
- Panel registered via `async_register_built_in_panel` from `homeassistant.components.frontend`
- Cache busting deferred (using fixed filename for now)

## Phase 6: Playwright Testing Setup (2025-01-16)

- [x] Initialize Playwright in repo:
    - [x] playwright.config.ts
    - [x] tests/e2e/ directory
- [x] Create test utilities:
    - [x] tests/e2e/fixtures/auth.ts - HA login helper
    - [x] tests/e2e/fixtures/mock-api.ts - mock server state control
- [x] Implement core e2e tests:
    - [x] Abode panel appears in sidebar
    - [x] Panel shows correct content ("Abode Configuration" text initially)
    - [ ] Dashboard loads with sensor data (deferred - panel currently minimal)
    - [ ] Alarm mode display is correct (deferred - panel currently minimal)
    - [ ] Arm/disarm interactions work (deferred - panel currently minimal)
    - [ ] Sensor state changes reflect in UI (deferred - panel currently minimal)
- [x] Add to package.json:
    - [x] test:e2e - run Playwright tests
    - [x] test:e2e:ui - run with Playwright UI for debugging
- [x] Create scripts/test-e2e.sh that:
    - [x] Starts docker-compose
    - [x] Waits for HA ready
    - [x] Runs Playwright
    - [x] Tears down

**Note:** 4 E2E tests implemented and passing. Additional tests for alarm/sensor UI deferred until panel functionality is expanded.

## Phase 7: CI Integration (2025-01-16)

- [x] Update .github/workflows/ to add:
    - [x] Frontend build step (ensure www/ is buildable)
    - [x] Playwright test job (disabled with if: false, can be enabled later)
- [x] Add CI-specific docker-compose override if needed (not needed)
- [x] Document in README which tests run in CI vs locally

**Implementation:**
- `tests.yaml` - Python linting/tests + Frontend build verification
- `e2e-tests.yaml` - E2E tests (manual trigger, disabled by default)
- `.github/workflows/README.md` - CI documentation

## Phase 8: Documentation Updates (2025-01-16)

- [x] Update DEVELOPMENT.md:
- [x] Dev environment setup instructions
- [x] How to run mock server
- [x] Frontend development workflow
- [x] Running tests (pytest + playwright)
- [x] Update README.md: (already had CI badges and dev section)
    - [x] Badge for CI status
    - [x] Link to development docs
- [x] Update CLAUDE.md with:
    - [x] New project structure
    - [x] Key commands
    - [x] Testing approach
- [x] Create CONTRIBUTING.md
- [x] Update .gitignore with ruff cache

## File Structure After Implementation

```
abode-security/
├── custom_components/abode_security/
│   ├── www/                         # Frontend build output
│   │   └── abode-security-panel.js
│   └── ... (existing)
├── config/                          # Test HA config
│   ├── configuration.yaml
│   └── .storage/
│       ├── auth
│       ├── onboarding
│       └── lovelace
├── frontend/                        # Frontend source
│   ├── src/
│   │   ├── abode-panel.ts
│   │   └── types.ts
│   ├── package.json
│   ├── rollup.config.js
│   ├── tsconfig.json
│   └── .nvmrc
├── tests/
│   ├── mock_server/
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── README.md
│   ├── e2e/
│   │   ├── fixtures/
│   │   │   ├── auth.ts
│   │   │   └── mock-api.ts
│   │   └── abode-panel.spec.ts
│   └── ... (existing pytest tests)
├── scripts/
│   ├── dev.sh
│   ├── test-e2e.sh
│   └── run_all_tests.sh
├── .github/workflows/
│   ├── tests.yaml
│   ├── e2e-tests.yaml
│   ├── validate.yaml
│   └── README.md
├── docker-compose.yml
├── playwright.config.ts
├── DEVELOPMENT.md
├── CONTRIBUTING.md
└── ... (existing files)
```

## Execution Notes

- All phases complete
- 101 Python tests passing (9 unit + 92 integration)
- 4 E2E tests passing
- Frontend builds successfully
- CI pipeline validates Python + Frontend on every push/PR
- E2E tests available via manual workflow trigger
