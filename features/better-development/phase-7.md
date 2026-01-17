# Phase 7: CI Integration

**Status**: ✅ Complete (2025-01-16)

## Goal
Add frontend build verification to the CI pipeline and create an optional workflow for E2E tests.

## Context
Currently, CI only tests Python code (lint, type check, pytest). With the new frontend infrastructure, we need to:
1. **Verify frontend builds** - Ensure TypeScript compiles and bundle is created
2. **Optionally run E2E tests** - Create workflow that can be enabled when ready

This prevents broken frontend deployments and catches issues before merging.

## Prerequisites
- Phase 5 completed (frontend exists)
- Phase 6 completed (Playwright tests exist)
- Existing `.github/workflows/tests.yaml` workflow
- GitHub repository with Actions enabled

## Steps

### 7.1 Update existing tests.yaml workflow

**File**: `.github/workflows/tests.yaml`

Current structure (from exploration):
```yaml
name: Tests
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      # Python tests...
```

**Add frontend build job** after the Python tests job:

```yaml
  frontend-build:
    name: Build Frontend
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version-file: 'frontend/.nvmrc'
          cache: 'npm'
          cache-dependency-path: 'frontend/package-lock.json'

      - name: Install dependencies
        run: npm ci

      - name: Build frontend
        run: npm run build

      - name: Verify build output exists
        run: |
          if [ ! -f "../custom_components/abode_security/www/abode-security-panel.js" ]; then
            echo "❌ Build output not found!"
            echo "Expected: custom_components/abode_security/www/abode-security-panel.js"
            exit 1
          fi
          echo "✅ Frontend build successful"
          ls -lh ../custom_components/abode_security/www/

      - name: Check bundle size
        run: |
          SIZE=$(stat -f%z "../custom_components/abode_security/www/abode-security-panel.js" 2>/dev/null || stat -c%s "../custom_components/abode_security/www/abode-security-panel.js")
          echo "Bundle size: $(numfmt --to=iec-i --suffix=B $SIZE)"
          # Warn if bundle is larger than 500KB
          if [ $SIZE -gt 512000 ]; then
            echo "⚠️  Warning: Bundle size exceeds 500KB"
          fi
```

**Full updated workflow**:

```yaml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint-and-test:
    name: Lint and Test Python
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements_dev.txt

      - name: Lint with ruff
        run: |
          ruff check .
          ruff format --check .

      - name: Type check with mypy
        run: mypy custom_components/abode_security/

      - name: Test with pytest
        run: pytest tests/ -v

  frontend-build:
    name: Build Frontend
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version-file: 'frontend/.nvmrc'
          cache: 'npm'
          cache-dependency-path: 'frontend/package-lock.json'

      - name: Install dependencies
        run: npm ci

      - name: Build frontend
        run: npm run build

      - name: Verify build output
        run: |
          if [ ! -f "../custom_components/abode_security/www/abode-security-panel.js" ]; then
            echo "❌ Build output not found!"
            exit 1
          fi
          echo "✅ Frontend build successful"
          ls -lh ../custom_components/abode_security/www/
```

### 7.2 Create E2E tests workflow (disabled by default)

**File**: `.github/workflows/e2e-tests.yaml`

```yaml
name: E2E Tests

on:
  # Manual trigger only - enable when ready for automated E2E testing
  workflow_dispatch:
    inputs:
      headed:
        description: 'Run in headed mode (visible browser)'
        required: false
        default: 'false'

  # Uncomment to run on pull requests:
  # pull_request:
  #   branches: [main, develop]

jobs:
  playwright-tests:
    name: Playwright E2E Tests
    runs-on: ubuntu-latest

    # Disabled by default - remove this line to enable
    if: false

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version-file: '.nvmrc'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Install Playwright browsers
        run: npx playwright install --with-deps chromium

      - name: Start Docker services
        run: docker-compose up -d

      - name: Wait for Home Assistant
        run: |
          echo "Waiting for Home Assistant to start..."
          timeout 120 bash -c 'until curl -f http://localhost:8123 > /dev/null 2>&1; do sleep 2; echo -n "."; done'
          echo " Ready!"

      - name: Wait for Mock Server
        run: |
          echo "Waiting for Mock Server..."
          timeout 30 bash -c 'until curl -f http://localhost:8000 > /dev/null 2>&1; do sleep 1; done'
          echo "Mock Server ready!"

      - name: Run Playwright tests
        run: npm run test:e2e
        env:
          CI: true

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 30

      - name: Upload test videos
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-videos
          path: test-results/
          retention-days: 7

      - name: Stop Docker services
        if: always()
        run: docker-compose down

      - name: Show logs on failure
        if: failure()
        run: |
          echo "::group::Home Assistant Logs"
          docker-compose logs homeassistant || true
          echo "::endgroup::"
          echo "::group::Mock Server Logs"
          docker-compose logs mock-abode || true
          echo "::endgroup::"
```

**To enable this workflow later**:
1. Remove the `if: false` line
2. Uncomment the `pull_request` trigger if desired
3. Commit and push

### 7.3 Add workflow status badges to README

**File**: `README.md`

At the top of the README, add:

```markdown
# Abode Security - Home Assistant Integration

[![Tests](https://github.com/USERNAME/REPO/workflows/Tests/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/tests.yaml)
[![E2E Tests](https://github.com/USERNAME/REPO/workflows/E2E%20Tests/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/e2e-tests.yaml)
[![HACS Validation](https://github.com/USERNAME/REPO/workflows/Validate/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/validate.yaml)

<!-- Rest of README... -->
```

Replace `USERNAME/REPO` with your actual GitHub username/repository.

### 7.4 Create CI documentation

**File**: `.github/workflows/README.md`

```markdown
# GitHub Actions Workflows

## Active Workflows

### tests.yaml
**Runs on**: Every push/PR to main or develop

**Jobs**:
1. **lint-and-test** - Python code quality
   - Ruff linting and formatting
   - MyPy type checking
   - Pytest unit/integration tests

2. **frontend-build** - Frontend build verification
   - Install npm dependencies
   - Build TypeScript with Rollup
   - Verify bundle output exists
   - Check bundle size

**Status**: ✅ Active

### validate.yaml
**Runs on**: Every push/PR to main or develop

**Jobs**:
- Validate HACS manifest
- Validate Home Assistant manifest.json
- Validate strings and icons

**Status**: ✅ Active

### e2e-tests.yaml
**Runs on**: Manual trigger via workflow_dispatch

**Jobs**:
- Start Docker environment (HA + Mock Server)
- Install Playwright
- Run browser-based E2E tests
- Upload test reports and videos on failure

**Status**: ⏸️ Disabled (if: false)

**To enable**:
1. Edit `.github/workflows/e2e-tests.yaml`
2. Remove `if: false` line
3. Optional: Uncomment `pull_request` trigger
4. Commit and push

## Running Locally

**Python tests**:
```bash
ruff check . && ruff format .
mypy custom_components/abode_security/
pytest tests/
```

**Frontend build**:
```bash
cd frontend
npm ci
npm run build
```

**E2E tests**:
```bash
./scripts/test-e2e.sh
```

## Debugging CI Failures

**Frontend build failures**:
- Check Node.js version matches `.nvmrc`
- Verify `package-lock.json` is committed
- Check TypeScript errors locally: `cd frontend && npx tsc --noEmit`

**E2E test failures**:
- Download artifacts from failed workflow
- View Playwright report and videos
- Run locally: `npm run test:e2e:ui`
- Check docker-compose logs for HA/mock server issues
```

### 7.5 Add CI-specific configuration

**File**: `frontend/.npmrc` (optional)

```
# CI-specific npm configuration
audit=false
fund=false
loglevel=error
```

Reduces noise in CI logs.

### 7.6 Test CI locally with act (optional)

Install `act` to run GitHub Actions locally:

```bash
# macOS
brew install act

# Test the workflow
act -j frontend-build
```

This helps debug CI issues before pushing.

### 7.7 Verify CI runs

**Push changes**:
```bash
git add .github/workflows/tests.yaml
git add .github/workflows/e2e-tests.yaml
git commit -m "ci: Add frontend build verification

- Add frontend-build job to tests.yaml workflow
- Verify TypeScript builds successfully
- Check bundle output and size
- Create e2e-tests.yaml workflow (disabled by default)
- Add workflow documentation

Phase 7/8 of better-development feature"
git push
```

**Check GitHub Actions**:
1. Go to repository → Actions tab
2. Find the workflow run
3. Verify both jobs pass:
   - ✅ lint-and-test
   - ✅ frontend-build

**Expected output** in frontend-build job:
```
✅ Frontend build successful
-rw-r--r-- 1 runner docker 45K abode-security-panel.js
Bundle size: 45KiB
```

### 7.8 Document CI behavior in DEVELOPMENT.md

Add section to `DEVELOPMENT.md` (will be created in Phase 8):

```markdown
## CI/CD

### GitHub Actions Workflows

#### tests.yaml (Active)
Runs on every push/PR:
- **Python**: linting (ruff), type checking (mypy), unit tests (pytest)
- **Frontend**: build verification, bundle size check

#### e2e-tests.yaml (Disabled)
Manual trigger only. To enable:
1. Remove `if: false` from workflow
2. Optionally enable on PR by uncommenting `pull_request` trigger

Runs:
- Docker environment (HA + Mock Server)
- Playwright browser tests
- Uploads reports/videos on failure

### Local CI Simulation

**Run Python checks**:
```bash
ruff check . && ruff format .
mypy custom_components/abode_security/
pytest tests/
```

**Run frontend build**:
```bash
cd frontend && npm ci && npm run build
```

**Run everything**:
```bash
./scripts/dev.sh
pytest tests/
cd frontend && npm run build
npm run test:e2e
```
```

## Success Criteria
- ✅ Frontend build job added to `tests.yaml`
- ✅ Frontend build succeeds in CI
- ✅ Bundle output verified in CI
- ✅ E2E workflow created (disabled by default)
- ✅ Workflow badges added to README
- ✅ CI documentation created
- ✅ All CI checks passing on push/PR

## Troubleshooting

**Frontend build fails in CI but works locally**:
- Check Node version: CI uses `.nvmrc`, ensure it matches local
- Verify `package-lock.json` is committed
- Check for hardcoded paths (use relative paths)
- Review CI logs for specific error

**Workflow not appearing**:
- Ensure file is in `.github/workflows/` (exact path)
- Ensure valid YAML (use yamllint or online validator)
- Push to main/develop branch
- Refresh Actions tab

**E2E workflow stuck**:
- Increase timeouts for HA startup
- Check Docker availability in CI environment
- May need GitHub-hosted runners with Docker support
- Consider using docker-compose v2 syntax

**Badge not updating**:
- Clear browser cache
- Check badge URL matches workflow name
- Verify workflow has run at least once

## Commit Message
```
ci: Add frontend build verification to CI pipeline

- Add frontend-build job to tests.yaml workflow
- Verify frontend builds successfully in CI
- Check bundle exists and report size
- Create e2e-tests.yaml workflow (disabled by default)
- Add workflow status badges to README
- Document CI workflows in .github/workflows/README.md
- Add CI section to development docs

Phase 7/8 of better-development feature
```

## Next Steps
After completing this phase:
- Move to [Phase 8: Documentation Updates](phase-8.md)
- Create comprehensive developer documentation
- Update project README
- Complete the better-development feature!
