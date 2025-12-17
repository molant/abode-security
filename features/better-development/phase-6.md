# Phase 6: Playwright Testing Setup

**Status**: ⏳ Not Started

## Goal
Set up Playwright for end-to-end testing with focus on verifying the Abode panel appears in the sidebar and displays correct content.

## Context
With the frontend now built (Phase 5) and mock server running (Phase 2), we can implement browser-based E2E tests to verify:
- Panel registration works correctly
- Panel appears in HA sidebar
- Panel content renders properly ("Abode Configuration" text)
- No JavaScript errors in console
- Integration works end-to-end

This gives confidence that deployments work correctly in a real browser environment.

## Prerequisites
- Phase 1-5 completed
- Node.js 20+ installed
- Docker environment running (HA + mock server)
- HA accessible at http://localhost:8123

## Steps

### 6.1 Install Playwright

**Initialize Playwright** (from project root):
```bash
npm init playwright@latest
```

**Interactive prompts** - choose:
- TypeScript: Yes
- Test directory: `tests/e2e`
- GitHub Actions workflow: No (we'll create custom in Phase 7)
- Install browsers: Yes

This creates:
- `playwright.config.ts` - Configuration
- `tests/e2e/` - Test directory
- `package.json` - If not exists at root
- `.gitignore` updates

**If package.json already exists at root**, manually add:
```bash
npm install -D @playwright/test
npx playwright install chromium
```

### 6.2 Configure Playwright

**File**: `playwright.config.ts` (at project root)

```typescript
import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for Abode Security E2E tests.
 *
 * Tests Home Assistant integration with mock Abode API server.
 */
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html'],
    ['list'],
  ],
  use: {
    baseURL: 'http://localhost:8123',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Start dev server before tests (optional - can start manually) */
  webServer: {
    command: 'docker-compose up',
    url: 'http://localhost:8123',
    timeout: 120 * 1000,
    reuseExistingServer: !process.env.CI,
    stdout: 'ignore',
    stderr: 'pipe',
  },
});
```

**Key settings**:
- `testDir`: E2E tests in `tests/e2e/`
- `baseURL`: Home Assistant at localhost:8123
- `webServer`: Automatically starts docker-compose before tests
- `reuseExistingServer`: Reuses running server (faster for local dev)
- `trace/screenshot/video`: Debugging aids for failures

### 6.3 Create test fixtures

Test fixtures provide common setup logic for HA authentication and mock server interaction.

**File**: `tests/e2e/fixtures/auth.ts`

```typescript
import { test as base, Page } from '@playwright/test';

/**
 * Login to Home Assistant.
 *
 * Handles both fresh login and already-authenticated state.
 */
export async function loginToHomeAssistant(page: Page) {
  await page.goto('/');

  // Check if already logged in (sidebar visible)
  const sidebar = page.locator('ha-sidebar');
  const sidebarVisible = await sidebar.isVisible().catch(() => false);

  if (sidebarVisible) {
    console.log('Already logged in');
    return;
  }

  // Look for login form
  const usernameField = page.locator('input[name="username"]');
  if (await usernameField.isVisible().catch(() => false)) {
    // Login with test credentials
    // Note: Adjust username/password based on your config/.storage/auth setup
    await usernameField.fill('test');
    await page.locator('input[name="password"]').fill('test');
    await page.locator('button[type="submit"]').click();

    // Wait for sidebar to appear (login successful)
    await page.waitForSelector('ha-sidebar', { timeout: 10000 });
    console.log('Logged in successfully');
    return;
  }

  // If no login form and no sidebar, may be loading
  await page.waitForSelector('ha-sidebar', { timeout: 15000 });
}

/**
 * Extended test with authenticated page fixture.
 */
export const test = base.extend({
  authenticatedPage: async ({ page }, use) => {
    await loginToHomeAssistant(page);
    await use(page);
  },
});

export { expect } from '@playwright/test';
```

**File**: `tests/e2e/fixtures/mock-api.ts`

```typescript
import axios from 'axios';

const MOCK_API_URL = process.env.MOCK_SERVER_URL || 'http://localhost:8000';

/**
 * Reset mock server to default state.
 *
 * Call before each test to ensure isolation.
 */
export async function resetMockServer() {
  try {
    await axios.post(`${MOCK_API_URL}/api/test/reset`, {}, { timeout: 2000 });
    console.log('Mock server state reset');
  } catch (error) {
    console.error('Failed to reset mock server:', error.message);
    throw new Error(
      `Mock server not responding at ${MOCK_API_URL}. ` +
      'Ensure docker-compose is running.'
    );
  }
}

/**
 * Set panel alarm mode via mock server.
 */
export async function setPanelMode(mode: 'standby' | 'home' | 'away') {
  const url = `${MOCK_API_URL}/api/v1/panel/mode/area_1/${mode}`;
  await axios.put(url);
  console.log(`Panel mode set to: ${mode}`);
}

/**
 * Get current mock server state (for debugging).
 */
export async function getMockServerState() {
  const response = await axios.get(`${MOCK_API_URL}/api/test/state`);
  return response.data;
}
```

**Install axios**:
```bash
npm install -D axios
```

### 6.4 Create panel test

**File**: `tests/e2e/abode-panel.spec.ts`

```typescript
import { test, expect } from './fixtures/auth';
import { resetMockServer } from './fixtures/mock-api';

test.describe('Abode Security Panel', () => {
  test.beforeEach(async () => {
    // Reset mock server before each test
    await resetMockServer();
  });

  test('panel appears in sidebar', async ({ authenticatedPage: page }) => {
    // Look for Abode panel in sidebar navigation
    const sidebar = page.locator('ha-sidebar');
    await expect(sidebar).toBeVisible();

    // Find the Abode menu item
    // Note: Selector may need adjustment based on HA version
    const abodePanel = sidebar.locator('text=Abode').first();

    // Verify panel is visible in sidebar
    await expect(abodePanel).toBeVisible({ timeout: 5000 });
  });

  test('panel shows correct content', async ({ authenticatedPage: page }) => {
    // Click Abode panel in sidebar
    const abodeLink = page.locator('ha-sidebar >> text=Abode').first();
    await abodeLink.click();

    // Wait for panel to load
    await page.waitForLoadState('networkidle');

    // Panel should be visible
    const panel = page.locator('abode-configuration-panel');
    await expect(panel).toBeVisible({ timeout: 10000 });

    // Verify heading text
    const heading = panel.locator('h1');
    await expect(heading).toHaveText('Abode Configuration');
  });

  test('panel loads without JavaScript errors', async ({ authenticatedPage: page }) => {
    const consoleErrors: string[] = [];

    // Capture console errors
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Capture page errors
    page.on('pageerror', (error) => {
      consoleErrors.push(error.message);
    });

    // Navigate to Abode panel
    await page.locator('ha-sidebar >> text=Abode').first().click();
    await page.waitForLoadState('networkidle');

    // Wait for panel to render
    await page.waitForSelector('abode-configuration-panel', { timeout: 10000 });

    // Allow any async operations to complete
    await page.waitForTimeout(1000);

    // Verify no errors occurred
    if (consoleErrors.length > 0) {
      console.error('Console errors detected:', consoleErrors);
    }
    expect(consoleErrors).toHaveLength(0);
  });

  test('panel is accessible from different starting pages', async ({ authenticatedPage: page }) => {
    // Test navigation from Overview page
    await page.goto('/lovelace/0');
    await page.locator('ha-sidebar >> text=Abode').first().click();
    await expect(page.locator('abode-configuration-panel')).toBeVisible();

    // Navigate away
    await page.goto('/lovelace/0');

    // Test navigation again (verifies clean state)
    await page.locator('ha-sidebar >> text=Abode').first().click();
    await expect(page.locator('abode-configuration-panel')).toBeVisible();
  });
});
```

### 6.5 Add npm scripts

**File**: `package.json` (root)

Add to `"scripts"`:
```json
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:e2e:debug": "playwright test --debug",
    "test:e2e:headed": "playwright test --headed",
    "test:e2e:report": "playwright show-report"
  }
}
```

### 6.6 Create test runner script

**File**: `scripts/test-e2e.sh`

```bash
#!/bin/bash
set -e

echo "========================================="
echo "Abode Security E2E Test Runner"
echo "========================================="
echo ""

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose not found"
    exit 1
fi

# Start services
echo "Starting services (HA + Mock Server)..."
docker-compose up -d

# Wait for Home Assistant to be ready
echo "Waiting for Home Assistant to start..."
MAX_WAIT=120
ELAPSED=0
while ! curl -f http://localhost:8123 > /dev/null 2>&1; do
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    if [ $ELAPSED -ge $MAX_WAIT ]; then
        echo "Error: Home Assistant failed to start within ${MAX_WAIT}s"
        docker-compose logs homeassistant
        exit 1
    fi
    echo -n "."
done
echo " Ready!"

# Wait for mock server
echo "Waiting for Mock Server..."
ELAPSED=0
while ! curl -f http://localhost:8000 > /dev/null 2>&1; do
    sleep 1
    ELAPSED=$((ELAPSED + 1))
    if [ $ELAPSED -ge 30 ]; then
        echo "Error: Mock server failed to start"
        exit 1
    fi
done
echo "Mock Server ready!"

# Run Playwright tests
echo ""
echo "Running Playwright tests..."
npm run test:e2e "$@"
TEST_EXIT_CODE=$?

# Cleanup (optional - comment out to leave running for debugging)
# echo ""
# echo "Stopping services..."
# docker-compose down

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "❌ Tests failed (exit code: $TEST_EXIT_CODE)"
    echo ""
    echo "To debug:"
    echo "  - View logs: docker-compose logs"
    echo "  - Run UI mode: npm run test:e2e:ui"
    echo "  - View report: npm run test:e2e:report"
fi

exit $TEST_EXIT_CODE
```

**Make executable**:
```bash
chmod +x scripts/test-e2e.sh
```

### 6.7 Run tests

**Option 1: Using test runner script**:
```bash
./scripts/test-e2e.sh
```

**Option 2: Manual**:
```bash
# Start services
docker-compose up -d

# Wait for HA to be ready
sleep 30

# Run tests
npm run test:e2e
```

**Option 3: UI Mode (recommended for development)**:
```bash
docker-compose up -d
npm run test:e2e:ui
```

The UI mode opens an interactive browser where you can:
- See tests run in real-time
- Step through each action
- Inspect elements
- Debug failures

**Expected output**:
```
Running 4 tests using 1 worker

  ✓ abode-panel.spec.ts:5:3 › panel appears in sidebar (2.3s)
  ✓ abode-panel.spec.ts:15:3 › panel shows correct content (3.1s)
  ✓ abode-panel.spec.ts:28:3 › panel loads without JavaScript errors (2.8s)
  ✓ abode-panel.spec.ts:48:3 › panel is accessible from different pages (4.2s)

  4 passed (12.4s)
```

### 6.8 Update .gitignore

Add:
```
# Playwright
/test-results/
/playwright-report/
/playwright/.cache/
```

## Success Criteria
- ✅ Playwright installed and configured
- ✅ `tests/e2e/` directory with fixtures and tests
- ✅ Panel visibility test passes
- ✅ Panel content test passes (verifies "Abode Configuration" text)
- ✅ No console errors test passes
- ✅ `npm run test:e2e` successfully runs all tests
- ✅ `npm run test:e2e:ui` opens interactive UI
- ✅ `scripts/test-e2e.sh` provides full test cycle

## Troubleshooting

**HA not responding**:
- Check containers: `docker-compose ps`
- Check logs: `docker-compose logs homeassistant`
- Increase wait timeout in test-e2e.sh

**Tests can't find panel**:
- Verify panel registered: Check HA sidebar manually
- Update selector in test (HA version differences)
- Check browser console for errors: `npm run test:e2e:headed`

**Authentication fails**:
- Check test credentials match `config/.storage/auth`
- Try manual login first, then run tests
- Update `fixtures/auth.ts` with correct credentials

**Flaky tests**:
- Increase timeouts
- Add `page.waitForLoadState('networkidle')` before assertions
- Use `test.setTimeout(30000)` for slow tests

**Debug specific test**:
```bash
npx playwright test abode-panel.spec.ts:15 --debug
```

**View test report after failure**:
```bash
npm run test:e2e:report
```

## Commit Message
```
feat: Add Playwright E2E testing infrastructure

- Initialize Playwright with config for HA integration testing
- Create auth fixtures for automated HA login
- Create mock-api fixtures for server state control
- Implement panel visibility and content tests
- Add npm scripts for E2E testing (test:e2e, test:e2e:ui, test:e2e:debug)
- Add scripts/test-e2e.sh for complete test cycle
- All tests passing: panel appears in sidebar with correct content

Phase 6/8 of better-development feature
```

## Next Steps
After completing this phase:
- Move to [Phase 7: CI Integration](phase-7.md)
- Add frontend build and E2E tests to GitHub Actions
