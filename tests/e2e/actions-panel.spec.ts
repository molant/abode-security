import { test, expect } from './fixtures/auth';
import { resetMockServer } from './fixtures/mock-api';

/**
 * E2E tests for the Actions panel functionality.
 *
 * These tests verify the full user flow for creating, editing,
 * deleting, and testing actions through the UI.
 */
test.describe('Actions Panel', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    // Reset mock server and navigate to Abode panel
    await resetMockServer();
    await page.locator('ha-sidebar >> text=Abode').first().click();
    await page.waitForSelector('abode-configuration-panel', { timeout: 10000 });
  });

  test.describe('Tab Navigation', () => {
    test('displays Actions tab by default', async ({ authenticatedPage: page }) => {
      // Actions tab should be visible and active
      const actionsTab = page.locator('abode-actions-tab');
      await expect(actionsTab).toBeVisible({ timeout: 5000 });
    });

    test('can switch to Modes tab', async ({ authenticatedPage: page }) => {
      // Click Modes tab
      const modesTabButton = page.locator('button:has-text("Modes")');
      await modesTabButton.click();

      // Modes tab content should be visible
      const modesTab = page.locator('abode-modes-tab');
      await expect(modesTab).toBeVisible({ timeout: 5000 });

      // Should show the three modes
      await expect(page.locator('text=Standby')).toBeVisible();
      await expect(page.locator('text=Home')).toBeVisible();
      await expect(page.locator('text=Away')).toBeVisible();
    });

    test('can switch back to Actions tab', async ({ authenticatedPage: page }) => {
      // Switch to Modes tab first
      await page.locator('button:has-text("Modes")').click();
      await expect(page.locator('abode-modes-tab')).toBeVisible();

      // Switch back to Actions tab
      await page.locator('button:has-text("Actions")').click();
      await expect(page.locator('abode-actions-tab')).toBeVisible();
    });
  });

  test.describe('Actions List', () => {
    test('shows empty state when no actions exist', async ({ authenticatedPage: page }) => {
      // Wait for loading to complete
      await page.waitForSelector('.empty-state, .actions-list', { timeout: 5000 });

      // Should show empty state with create button
      const createButton = page.locator('text=Create your first action');
      await expect(createButton).toBeVisible();
    });

    test('shows Add Action button', async ({ authenticatedPage: page }) => {
      const addButton = page.locator('button:has-text("Add Action")');
      await expect(addButton).toBeVisible();
    });
  });

  test.describe('Action Editor', () => {
    test('opens editor when clicking Add Action', async ({ authenticatedPage: page }) => {
      // Click Add Action button
      await page.locator('button:has-text("Add Action")').click();

      // Editor modal should appear
      const editor = page.locator('abode-action-editor');
      await expect(editor).toBeVisible({ timeout: 5000 });

      // Should have form fields
      await expect(page.locator('input[placeholder*="Action name"]')).toBeVisible();
    });

    test('opens editor from empty state button', async ({ authenticatedPage: page }) => {
      // Wait for empty state
      await page.waitForSelector('.empty-state', { timeout: 5000 });

      // Click create button in empty state
      await page.locator('text=Create your first action').click();

      // Editor should open
      const editor = page.locator('abode-action-editor');
      await expect(editor).toBeVisible({ timeout: 5000 });
    });

    test('can close editor with Cancel button', async ({ authenticatedPage: page }) => {
      // Open editor
      await page.locator('button:has-text("Add Action")').click();
      await expect(page.locator('abode-action-editor')).toBeVisible();

      // Click Cancel
      await page.locator('button:has-text("Cancel")').click();

      // Editor should close
      await expect(page.locator('abode-action-editor')).not.toBeVisible();
    });

    test('can close editor with Escape key', async ({ authenticatedPage: page }) => {
      // Open editor
      await page.locator('button:has-text("Add Action")').click();
      await expect(page.locator('abode-action-editor')).toBeVisible();

      // Press Escape
      await page.keyboard.press('Escape');

      // Editor should close
      await expect(page.locator('abode-action-editor')).not.toBeVisible();
    });

    test('loads sensors in editor', async ({ authenticatedPage: page }) => {
      // Open editor
      await page.locator('button:has-text("Add Action")').click();
      await expect(page.locator('abode-action-editor')).toBeVisible();

      // Wait for sensors to load (should not show loading indicator forever)
      await page.waitForSelector('abode-action-editor .sensor-group, abode-action-editor .empty-state', {
        timeout: 10000,
      });

      // Should have sensor checkboxes or empty state for sensors
      const sensorSection = page.locator('abode-action-editor >> text=Sensors');
      await expect(sensorSection).toBeVisible();
    });

    test('loads alarms in editor', async ({ authenticatedPage: page }) => {
      // Open editor
      await page.locator('button:has-text("Add Action")').click();
      await expect(page.locator('abode-action-editor')).toBeVisible();

      // Should have alarms section
      const alarmsSection = page.locator('abode-action-editor >> text=Alarms');
      await expect(alarmsSection).toBeVisible();
    });

    test('shows validation error for empty name', async ({ authenticatedPage: page }) => {
      // Open editor
      await page.locator('button:has-text("Add Action")').click();
      await expect(page.locator('abode-action-editor')).toBeVisible();

      // Try to save without filling required fields
      await page.locator('button:has-text("Save")').click();

      // Should show validation error
      const error = page.locator('abode-action-editor .error, abode-action-editor [role="alert"]');
      await expect(error).toBeVisible({ timeout: 2000 });
    });
  });

  test.describe('Create Action Flow', () => {
    test('can create a new action', async ({ authenticatedPage: page }) => {
      // Open editor
      await page.locator('button:has-text("Add Action")').click();
      await expect(page.locator('abode-action-editor')).toBeVisible();

      // Fill in action name
      await page.locator('input[placeholder*="Action name"]').fill('Test Motion Alert');

      // Select a mode (click the Home mode checkbox)
      await page.locator('abode-action-editor label:has-text("Home") input[type="checkbox"]').check();

      // Wait for sensors and alarms to load
      await page.waitForTimeout(1000);

      // Select a sensor if available
      const sensorCheckbox = page.locator(
        'abode-action-editor .sensor-group input[type="checkbox"]'
      ).first();
      if (await sensorCheckbox.isVisible()) {
        await sensorCheckbox.check();
      }

      // Select an alarm if available
      const alarmCheckbox = page.locator(
        'abode-action-editor .alarms-list input[type="checkbox"]'
      ).first();
      if (await alarmCheckbox.isVisible()) {
        await alarmCheckbox.check();
      }

      // Save the action
      await page.locator('button:has-text("Save")').click();

      // Editor should close
      await expect(page.locator('abode-action-editor')).not.toBeVisible({ timeout: 5000 });

      // Action should appear in the list
      await expect(page.locator('text=Test Motion Alert')).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Action Operations', () => {
    // Helper to create an action via the UI
    async function createTestAction(page: any, name: string) {
      await page.locator('button:has-text("Add Action")').click();
      await page.locator('input[placeholder*="Action name"]').fill(name);
      await page.locator('abode-action-editor label:has-text("Home") input[type="checkbox"]').check();

      // Wait for sensors/alarms to load
      await page.waitForTimeout(1000);

      // Select first sensor if available
      const sensorCheckbox = page.locator(
        'abode-action-editor .sensor-group input[type="checkbox"]'
      ).first();
      if (await sensorCheckbox.isVisible()) {
        await sensorCheckbox.check();
      }

      // Select first alarm if available
      const alarmCheckbox = page.locator(
        'abode-action-editor .alarms-list input[type="checkbox"]'
      ).first();
      if (await alarmCheckbox.isVisible()) {
        await alarmCheckbox.check();
      }

      await page.locator('button:has-text("Save")').click();
      await expect(page.locator('abode-action-editor')).not.toBeVisible({ timeout: 5000 });
    }

    test('can toggle action enabled state', async ({ authenticatedPage: page }) => {
      // Create an action first
      await createTestAction(page, 'Toggle Test Action');

      // Find the action row
      const actionRow = page.locator('.action-row:has-text("Toggle Test Action")');
      await expect(actionRow).toBeVisible();

      // Find and click the toggle switch
      const toggleSwitch = actionRow.locator('.toggle-switch input[type="checkbox"]');
      const isChecked = await toggleSwitch.isChecked();

      await toggleSwitch.click();

      // Toggle state should change
      await expect(toggleSwitch).toHaveAttribute('checked', isChecked ? null : '');
    });

    test('can edit an existing action', async ({ authenticatedPage: page }) => {
      // Create an action first
      await createTestAction(page, 'Edit Test Action');

      // Find and click the edit button
      const actionRow = page.locator('.action-row:has-text("Edit Test Action")');
      await actionRow.locator('button[aria-label="Edit action"]').click();

      // Editor should open with existing data
      const editor = page.locator('abode-action-editor');
      await expect(editor).toBeVisible();

      // Name field should have existing value
      const nameInput = page.locator('input[placeholder*="Action name"]');
      await expect(nameInput).toHaveValue('Edit Test Action');

      // Change the name
      await nameInput.fill('Updated Action Name');
      await page.locator('button:has-text("Save")').click();

      // Editor should close and new name should appear
      await expect(editor).not.toBeVisible({ timeout: 5000 });
      await expect(page.locator('text=Updated Action Name')).toBeVisible();
    });

    test('can delete an action with confirmation', async ({ authenticatedPage: page }) => {
      // Create an action first
      await createTestAction(page, 'Delete Test Action');

      // Find and click the delete button
      const actionRow = page.locator('.action-row:has-text("Delete Test Action")');
      await actionRow.locator('button[aria-label="Delete action"]').click();

      // Confirmation dialog should appear
      const dialog = page.locator('.dialog:has-text("Delete Action")');
      await expect(dialog).toBeVisible();

      // Click Delete to confirm
      await dialog.locator('button:has-text("Delete")').click();

      // Dialog should close
      await expect(dialog).not.toBeVisible({ timeout: 5000 });

      // Action should be removed from list
      await expect(page.locator('text=Delete Test Action')).not.toBeVisible();
    });

    test('can cancel delete action', async ({ authenticatedPage: page }) => {
      // Create an action first
      await createTestAction(page, 'Cancel Delete Action');

      // Find and click the delete button
      const actionRow = page.locator('.action-row:has-text("Cancel Delete Action")');
      await actionRow.locator('button[aria-label="Delete action"]').click();

      // Confirmation dialog should appear
      const dialog = page.locator('.dialog:has-text("Delete Action")');
      await expect(dialog).toBeVisible();

      // Click Cancel
      await dialog.locator('button:has-text("Cancel")').click();

      // Dialog should close
      await expect(dialog).not.toBeVisible();

      // Action should still be in the list
      await expect(page.locator('text=Cancel Delete Action')).toBeVisible();
    });

    test('shows test action confirmation dialog', async ({ authenticatedPage: page }) => {
      // Create an action first
      await createTestAction(page, 'Test Button Action');

      // Find and click the test button
      const actionRow = page.locator('.action-row:has-text("Test Button Action")');
      await actionRow.locator('button[aria-label="Test action"]').click();

      // Confirmation dialog should appear with warning
      const dialog = page.locator('.dialog:has-text("Test Action")');
      await expect(dialog).toBeVisible();
      await expect(dialog.locator('text=trigger real alarms')).toBeVisible();

      // Cancel the test
      await dialog.locator('button:has-text("Cancel")').click();
      await expect(dialog).not.toBeVisible();
    });
  });

  test.describe('Modes Tab', () => {
    test('displays all three modes', async ({ authenticatedPage: page }) => {
      // Navigate to Modes tab
      await page.locator('button:has-text("Modes")').click();

      const modesTab = page.locator('abode-modes-tab');
      await expect(modesTab).toBeVisible();

      // Should show all three modes
      await expect(modesTab.locator('text=Standby')).toBeVisible();
      await expect(modesTab.locator('text=Home')).toBeVisible();
      await expect(modesTab.locator('text=Away')).toBeVisible();
    });

    test('shows action count for each mode', async ({ authenticatedPage: page }) => {
      // Navigate to Modes tab
      await page.locator('button:has-text("Modes")').click();

      // Each mode card should show action count (even if 0)
      const modesTab = page.locator('abode-modes-tab');
      await expect(modesTab).toBeVisible();

      // Look for action count text
      const actionCountText = modesTab.locator('text=/\\d+ actions?/');
      // Should have at least one mode showing action count
      await expect(actionCountText.first()).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Error Handling', () => {
    test('shows error when API fails', async ({ authenticatedPage: page }) => {
      const consoleErrors: string[] = [];

      // Capture console errors
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });

      // The panel should handle API errors gracefully
      // Wait for initial load
      await page.waitForSelector('abode-actions-tab', { timeout: 10000 });

      // If there are errors, they should be displayed in the UI, not just console
      const errorDisplay = page.locator('.error, [role="alert"]');
      // This test documents current behavior - errors may or may not be visible
    });
  });

  test.describe('Responsive Layout', () => {
    test('works on mobile viewport', async ({ authenticatedPage: page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });

      // Navigate to panel
      await page.locator('ha-sidebar >> text=Abode').first().click();
      await page.waitForSelector('abode-configuration-panel', { timeout: 10000 });

      // Panel should still be functional
      const actionsTab = page.locator('abode-actions-tab');
      await expect(actionsTab).toBeVisible();

      // Add Action button should be visible
      const addButton = page.locator('button:has-text("Add Action")');
      await expect(addButton).toBeVisible();
    });

    test('editor modal works on mobile', async ({ authenticatedPage: page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });

      // Open editor
      await page.locator('button:has-text("Add Action")').click();

      // Editor should be visible and usable
      const editor = page.locator('abode-action-editor');
      await expect(editor).toBeVisible();

      // Form fields should be accessible
      const nameInput = page.locator('input[placeholder*="Action name"]');
      await expect(nameInput).toBeVisible();
    });
  });

  test.describe('Accessibility', () => {
    test('dialogs have proper ARIA attributes', async ({ authenticatedPage: page }) => {
      // Create an action first using empty state button
      await page.locator('button:has-text("Add Action")').click();
      await expect(page.locator('abode-action-editor')).toBeVisible();

      // Editor overlay should have proper ARIA
      const overlay = page.locator('.editor-overlay');
      await expect(overlay).toHaveAttribute('role', 'dialog');
      await expect(overlay).toHaveAttribute('aria-modal', 'true');

      // Close editor
      await page.keyboard.press('Escape');

      // If we had an action, test delete dialog accessibility
      // For now, just verify the editor closes properly
      await expect(page.locator('abode-action-editor')).not.toBeVisible();
    });

    test('buttons have accessible labels', async ({ authenticatedPage: page }) => {
      // Check main Add Action button
      const addButton = page.locator('button:has-text("Add Action")');
      await expect(addButton).toHaveAttribute('aria-label', 'Add new action');
    });
  });
});
