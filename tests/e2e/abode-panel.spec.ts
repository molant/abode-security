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
