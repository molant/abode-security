# GitHub Actions Workflows

## Active Workflows

### tests.yaml
**Runs on**: Every push/PR to main or develop

**Jobs**:
1. **tests** - Python code quality
   - Ruff linting and formatting
   - MyPy type checking
   - Pytest unit/integration tests

2. **frontend-build** - Frontend build verification
   - Install npm dependencies
   - Build TypeScript with Rollup
   - Verify bundle output exists

**Status**: Active

### validate.yaml
**Runs on**: Every push/PR to main or develop

**Jobs**:
- Validate HACS manifest
- Validate Home Assistant manifest.json
- Validate strings and icons

**Status**: Active

### e2e-tests.yaml
**Runs on**: Manual trigger via workflow_dispatch

**Jobs**:
- Start Docker environment (HA + Mock Server)
- Install Playwright
- Run browser-based E2E tests
- Upload test reports and videos on failure

**Status**: Disabled (if: false)

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
