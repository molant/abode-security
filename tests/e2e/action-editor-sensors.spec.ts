import { test, expect } from './fixtures/auth';
import { resetMockServer } from './fixtures/mock-api';

/**
 * E2E coverage for sensor-category collapse + search in the action editor
 * (issue #113). Asserted against the live HA stack so the WS round-trip
 * for sensors/alarms is exercised end-to-end — the unit tests cover the
 * same logic but against pre-injected state.
 */
test.describe('Action editor: sensor categories collapse + search (#113)', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await resetMockServer();
    await page.locator('ha-sidebar >> text=Abode').first().click();
    await page.waitForSelector('abode-configuration-panel', { timeout: 10000 });
  });

  /**
   * Sensor UI elements live inside several layered shadow roots
   * (panel → actions-tab → action-editor → abode-modal). Playwright's
   * CSS engine auto-pierces open shadow roots, so we just locate the
   * editor host element and use plain CSS selectors against it.
   */
  const sensorRoot = (page: import('@playwright/test').Page) =>
    page.locator('abode-action-editor');

  async function openNewActionEditor(page: import('@playwright/test').Page) {
    // The empty-state CTA and the toolbar Add button are the two entry
    // points; whichever is currently visible works.
    const addButton = page.locator('button:has-text("Add Action")');
    if (await addButton.isVisible().catch(() => false)) {
      await addButton.click();
    } else {
      await page.locator('text=Create your first action').click();
    }
    await expect(page.locator('abode-action-editor')).toBeVisible({ timeout: 5000 });
    // Wait for the sensor section to settle: either the search input has
    // rendered (sensors loaded) or the load-error retry button appeared.
    await sensorRoot(page)
      .locator('.sensor-search, .retry-row button')
      .first()
      .waitFor({ state: 'visible', timeout: 10000 });
  }

  test('sensor categories start collapsed; no category items render', async ({
    authenticatedPage: page,
  }) => {
    await openNewActionEditor(page);

    const editor = sensorRoot(page);
    // At least one category should exist (mock seeds binary_sensors).
    await expect(editor.locator('.category-header').first()).toBeVisible();

    // Nothing inside any category should be rendered while collapsed.
    await expect(editor.locator('.category-items')).toHaveCount(0);

    // Every disclosure button reports aria-expanded="false".
    const disclosures = editor.locator('button.disclosure');
    const total = await disclosures.count();
    expect(total).toBeGreaterThan(0);
    for (let i = 0; i < total; i++) {
      await expect(disclosures.nth(i)).toHaveAttribute('aria-expanded', 'false');
    }
  });

  test('disclosure click expands a single category and renders its items', async ({
    authenticatedPage: page,
  }) => {
    await openNewActionEditor(page);
    const editor = sensorRoot(page);

    const firstDisclosure = editor.locator('button.disclosure').first();
    await firstDisclosure.click();

    await expect(firstDisclosure).toHaveAttribute('aria-expanded', 'true');
    // Exactly one category should now have its items visible.
    await expect(editor.locator('.category-items')).toHaveCount(1);

    // Toggling again collapses it.
    await firstDisclosure.click();
    await expect(firstDisclosure).toHaveAttribute('aria-expanded', 'false');
    await expect(editor.locator('.category-items')).toHaveCount(0);
  });

  test('clicking the disclosure does not toggle the category checkbox', async ({
    authenticatedPage: page,
  }) => {
    await openNewActionEditor(page);
    const editor = sensorRoot(page);

    const firstCategory = editor.locator('.category').first();
    const headerCheckbox = firstCategory.locator('.category-header input[type="checkbox"]');
    await expect(headerCheckbox).not.toBeChecked();

    await firstCategory.locator('button.disclosure').click();

    // Selection state must be untouched — the disclosure's stopPropagation
    // is the only thing preventing the header's select-all from firing.
    await expect(headerCheckbox).not.toBeChecked();
  });

  test('search input filters items live and auto-expands matching categories', async ({
    authenticatedPage: page,
  }) => {
    await openNewActionEditor(page);
    const editor = sensorRoot(page);

    // Capture the first sensor name from any (currently collapsed) category
    // so the assertion stays independent of the mock fixture's exact device
    // list — we just need a real name we know matches.
    const firstDisclosure = editor.locator('button.disclosure').first();
    await firstDisclosure.click();
    const firstSensorLabel = await editor
      .locator('.category-items label')
      .first()
      .innerText();
    const firstWord = firstSensorLabel.trim().split(/\s+/)[0];
    // Collapse again so we can verify search re-expands on its own.
    await firstDisclosure.click();
    await expect(editor.locator('.category-items')).toHaveCount(0);

    // Type a partial match into the search box.
    const search = editor.locator('.sensor-search');
    await search.fill(firstWord);

    // The matching category auto-expands and shows at least the originally
    // observed sensor.
    await expect(
      editor.locator('.category-items label', { hasText: firstSensorLabel.trim() }),
    ).toBeVisible();

    // Clearing the search returns to the user's original collapse state.
    // Because the only earlier expansion was used to scrape a sensor name
    // and then collapsed again, every category should now be collapsed —
    // assert both the empty items list AND the aria-expanded flag so a
    // future refactor that drops the user-state restore can't make this
    // test pass for the wrong reason.
    await search.fill('');
    await expect(editor.locator('.category-items')).toHaveCount(0);
    const disclosures = editor.locator('button.disclosure');
    const total = await disclosures.count();
    for (let i = 0; i < total; i++) {
      await expect(disclosures.nth(i)).toHaveAttribute('aria-expanded', 'false');
    }
  });

  test('search with no matches hides every category and shows an empty hint', async ({
    authenticatedPage: page,
  }) => {
    await openNewActionEditor(page);
    const editor = sensorRoot(page);

    // A clearly-impossible substring — no device fixture name contains this.
    await editor.locator('.sensor-search').fill('xyzzy-no-such-sensor-name-xyzzy');

    // No category headers should render while the filter rejects everything.
    await expect(editor.locator('.category-header')).toHaveCount(0);
    // The "no matches" hint should be visible (text includes the query).
    await expect(editor.locator('text=No sensors match')).toBeVisible();
  });
});
