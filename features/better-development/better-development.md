# Abode Security Integration - Better Development Environment Plan

## Phase 1: Docker Dev Environment Setup

- [ ] Create docker-compose.yml at repo root with:
- [ ]  Home Assistant container (stable image)
- [ ] Volume mount for custom_components/abode_security
- [ ] Volume mount for test HA config
- [ ]  Network configuration for mock server communication
- [ ] Create config/ directory for test HA instance:
- [ ] configuration.yaml with abode_security integration configured
- [ ] Pre-configured test user in .storage/auth
- [ ] Pre-configured dashboard in .storage/lovelace
- [ ] Onboarding marked complete in .storage/onboarding
- [ ]  Create scripts/dev.sh for starting dev environment
- [ ]  Verify integration loads and hot reload works (restart integration on file change)

## Phase 2: Mock Abode API Server

- [ ]  Create tests/mock_server/ directory
- [ ]  Implement FastAPI mock server with:
- [ ] Auth endpoint (username/password → token)
- [ ] Panel status endpoint (get/set alarm mode)
- [ ] Devices endpoint returning fixture data:
- [ ] Motion sensors (2-3)
- [ ] Contact/door sensors (2-3)
- [ ] Smoke sensor (1)
- [ ] Device status update endpoints
- [ ] State reset endpoint for test cleanup
- [ ] Create tests/mock_server/Dockerfile
- [ ] Add mock server to docker-compose.yml
- [ ] Document mock server endpoints in tests/mock_server/README.md

## Phase 3: Integration URL Configuration

- [ ] Add base_url parameter to abode/ client
- [ ] Thread base_url through integration setup (env var ABODE_API_URL)
- [ ] Update config flow if needed (optional override for advanced users?)
- [ ] Test integration connects to mock server successfully
- [ ] Ensure production default remains unchanged

## Phase 4: Migrate/Update Existing Tests

- [ ] Audit current tests in tests/ - identify what exists
- [ ] Update pytest fixtures to use mock server where applicable
- [ ] Add conftest.py fixtures for:
- [ ] Mock server URL configuration
- [ ] HA test instance helpers (if using HA test framework)
- [ ] Common test data/fixtures
- [ ] Ensure all existing tests pass with new setup
- [ ] Update requirements_dev.txt if new dependencies needed

## Phase 5: Frontend Dev Workflow

- [ ] Evaluate current rollup setup in frontend/
- [ ] Add/update package.json scripts:
- [ ] build - production build to www/
- [ ] watch - rebuild on changes
- [ ] dev - watch with source maps
- [ ] Add frontend dev container to docker-compose.yml (or document local workflow)
- [ ] Test hot reload: change TS → rebuild → refresh dashboard → see changes
- [ ] Add .nvmrc or engines field for Node version consistency

## Phase 6: Playwright Testing Setup

- [ ] Initialize Playwright in repo:
    - [ ] playwright.config.ts
    - [ ] tests/e2e/ directory
- [ ] Create test utilities:
    - [ ] tests/e2e/fixtures/auth.ts - HA login helper
    - [ ] tests/e2e/fixtures/mock-api.ts - mock server state control
- [ ] Implement core e2e tests:
    - [ ] Dashboard loads with sensor data
    - [ ] Alarm mode display is correct
    - [ ] Arm/disarm interactions work
    - [ ] Sensor state changes reflect in UI
- [ ] Add to package.json:
    - [ ] test:e2e - run Playwright tests
    - [ ] test:e2e:ui - run with Playwright UI for debugging
- [ ] Create scripts/test-e2e.sh that:
    - [ ] Starts docker-compose
    - [ ] Waits for HA ready
    - [ ] Runs Playwright
    - [ ] Tears down

## Phase 7: CI Integration

- [ ] Update .github/workflows/ to add:
    - [ ] Frontend build step (ensure www/ is buildable)
    - [ ] Playwright test job (local only for now - add if: false or separate workflow)
- [ ] Add CI-specific docker-compose override if needed
- [ ] Document in README which tests run in CI vs locally

## Phase 8: Documentation Updates

- [ ] Update DEVELOPMENT.md:
- [ ] Dev environment setup instructions
- [ ] How to run mock server
- [ ] Frontend development workflow
- [ ] Running tests (pytest + playwright)
- [ ] Update README.md:
    - [ ] Badge for CI status
    - [ ] Link to development docs
- [ ] Update CLAUDE.md with:
    - [ ] New project structure
    - [ ] Key commands
    - [ ] Testing approach

## File Structure After Implementation

```
abode-security/
├── custom_components/abode_security/
│   └── ... (existing)
├── config/                          # NEW: Test HA config
│   ├── configuration.yaml
│   └── .storage/
│       ├── auth
│       ├── onboarding
│       └── lovelace
├── tests/
│   ├── mock_server/                 # NEW
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── README.md
│   ├── e2e/                         # NEW
│   │   ├── fixtures/
│   │   ├── dashboard.spec.ts
│   │   └── ...
│   └── ... (existing pytest tests)
├── scripts/                         # NEW
│   ├── dev.sh
│   └── test-e2e.sh
├── docker-compose.yml               # NEW
├── playwright.config.ts             # NEW
└── ... (existing files)
```

Execution Notes for Claude Code

Work through phases sequentially - each builds on the previous
Test each phase before moving on
Keep commits atomic and well-described
If stuck on HA-specific quirks (auth storage format, etc.), search HA core repo for examples
Mock server should be minimal - only implement endpoints the integration actually calls
For Abode API structure, reference custom_components/abode_security/abode/ client code