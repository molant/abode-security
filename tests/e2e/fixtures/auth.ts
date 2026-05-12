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

  // Wait for login page to fully load
  await page.waitForLoadState('networkidle');

  // HA uses web components - look for the login button to know form is ready
  const loginButton = page.locator('text=Log in').first();
  if (await loginButton.isVisible().catch(() => false)) {
    // Login with test credentials
    // Note: Adjust username/password based on your config/.storage/auth setup
    // HA uses Material web components - target by placeholder text
    await page.locator('input').first().fill('admin');
    await page.locator('input').nth(1).fill('admin');
    await loginButton.click();

    // Wait for sidebar to appear (login successful)
    await page.waitForSelector('ha-sidebar', { timeout: 15000 });
    console.log('Logged in successfully');
    return;
  }

  // If no login form and no sidebar, may be loading
  await page.waitForSelector('ha-sidebar', { timeout: 15000 });
}

/**
 * Extended test with authenticated page fixture.
 */
export const test = base.extend<{ authenticatedPage: Page }>({
  authenticatedPage: async ({ page }, use) => {
    await loginToHomeAssistant(page);
    await use(page);
  },
});

export { expect } from '@playwright/test';
