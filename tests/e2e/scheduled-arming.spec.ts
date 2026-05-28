import { test, expect } from './fixtures/auth';
import { resetMockServer } from './fixtures/mock-api';

/**
 * E2E happy-path test for the Scheduled Arming feature (Phase 4).
 *
 * Exercises the full CRUD cycle via the Modes tab's "Home schedules" section.
 * Requires the dev stack (./scripts/dev.sh) to be running.
 */
test.describe('Scheduled Arming', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await resetMockServer();
    // Navigate to the Abode panel and switch to the Modes tab
    await page.locator('ha-sidebar').locator('text=Abode').first().click();
    await page.waitForSelector('abode-configuration-panel', { timeout: 10000 });
    await page.locator('button:has-text("Modes")').click();
    await expect(page.locator('abode-modes-tab')).toBeVisible({ timeout: 5000 });
  });

  test('schedules section renders with empty state', async ({ authenticatedPage: page }) => {
    // The schedules section heading should be visible
    await expect(page.locator('text=Home schedules')).toBeVisible({ timeout: 5000 });

    // Empty state message should appear when no schedules
    await expect(page.locator('text=No schedules yet')).toBeVisible({ timeout: 5000 });

    // Add button should be visible for admin
    await expect(page.locator('button:has-text("+ Add schedule")')).toBeVisible({ timeout: 5000 });
  });

  test('full CRUD cycle: create, edit, toggle, delete', async ({ authenticatedPage: page }) => {
    // --- Create ---
    const addBtn = page.locator('button:has-text("+ Add schedule")');
    await expect(addBtn).toBeVisible({ timeout: 5000 });
    await addBtn.click();

    // New row in edit mode: day chips should be visible
    await expect(page.locator('abode-day-chip-picker')).toBeVisible({ timeout: 3000 });

    // Select Mon, Tue, Wed — chain from the day-chip-picker host element to
    // correctly pierce the nested shadow DOM (component > shadow root > .chip).
    const chipPicker = page.locator('abode-day-chip-picker');
    await chipPicker.locator('.chip').nth(0).click(); // Monday
    await chipPicker.locator('.chip').nth(1).click(); // Tuesday
    await chipPicker.locator('.chip').nth(2).click(); // Wednesday

    // Set arm time
    const armInput = page.locator('input[aria-label="Arm time"]');
    await armInput.fill('22:00');

    // Set disarm time
    const disarmInput = page.locator('input[aria-label="Disarm time"]');
    await disarmInput.fill('06:00');

    // Click Save
    await page.locator('button:has-text("Save")').click();

    // Row should appear in list with time display
    await expect(page.locator('text=22:00')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=06:00')).toBeVisible({ timeout: 5000 });

    // Add button should reappear
    await expect(addBtn).toBeVisible({ timeout: 3000 });

    // --- Edit: change name to "Weeknights" ---
    await page.locator('[aria-label="Edit schedule"]').click();

    const nameInput = page.locator('input[aria-label="Schedule name"]');
    await expect(nameInput).toBeVisible({ timeout: 3000 });
    await nameInput.fill('Weeknights');

    await page.locator('button:has-text("Save")').click();

    // Name should be displayed in view mode
    await expect(page.locator('text=Weeknights')).toBeVisible({ timeout: 5000 });

    // --- Toggle enabled off ---
    // Use aria-label="Enabled" to target the view-mode toggle specifically,
    // avoiding ambiguity with the edit-mode "Enabled" checkbox.
    const enabledCheckbox = page.locator('input[aria-label="Enabled"]');
    await enabledCheckbox.uncheck();

    // Verify disabled visual state — scoped to the named row, waits for WS round-trip
    const viewRow = page.locator('.view-row:has-text("Weeknights")');
    await expect(viewRow).toHaveClass(/disabled/, { timeout: 5000 });

    // --- Delete ---
    await page.locator('[aria-label="Delete schedule"]').click();

    // Confirm dialog should appear
    await expect(page.locator('text=Delete schedule?')).toBeVisible({ timeout: 3000 });

    // Click Delete in confirm dialog
    await page.locator('.dialog-button.danger').click();

    // Row should be gone; empty state should return
    await expect(page.locator('text=Weeknights')).not.toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=No schedules yet')).toBeVisible({ timeout: 5000 });
  });

  test('validation: saving without weekdays shows error', async ({ authenticatedPage: page }) => {
    await page.locator('button:has-text("+ Add schedule")').click();
    await expect(page.locator('abode-day-chip-picker')).toBeVisible({ timeout: 3000 });

    // Do NOT select any day chips — click Save immediately
    await page.locator('button:has-text("Save")').click();

    // Validation error should appear
    await expect(page.locator('[role="alert"]')).toBeVisible({ timeout: 3000 });
    await expect(page.locator('text=weekday')).toBeVisible({ timeout: 3000 });
  });

  test('cancel new row removes it without saving', async ({ authenticatedPage: page }) => {
    await page.locator('button:has-text("+ Add schedule")').click();
    await expect(page.locator('abode-day-chip-picker')).toBeVisible({ timeout: 3000 });

    // Cancel
    await page.locator('button:has-text("Cancel")').click();

    // New row gone; empty state back
    await expect(page.locator('abode-day-chip-picker')).not.toBeVisible({ timeout: 3000 });
    await expect(page.locator('text=No schedules yet')).toBeVisible({ timeout: 5000 });
  });
});
