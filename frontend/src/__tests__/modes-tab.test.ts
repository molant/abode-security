/**
 * Tests for the ModesTab component.
 *
 * Note: These tests focus on rendering behavior with pre-loaded data.
 * API integration is tested via E2E and integration tests.
 */

import { expect, fixture, html } from '@open-wc/testing';

import '../modes-tab.js';
import type { ModesTab } from '../modes-tab.js';
import { createMockHass, createMockModes, elementUpdated } from './test-helpers.js';

describe('ModesTab', () => {
  describe('rendering with data', () => {
    it('renders mode cards when data is provided directly', async () => {
      const hass = createMockHass();

      // Create element and manually set loaded state
      const el = await fixture<ModesTab>(html`
        <abode-modes-tab .hass=${hass}></abode-modes-tab>
      `);

      // Manually inject loaded state for testing
      // @ts-expect-error - accessing private property for testing
      el._modes = createMockModes();
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      // Should show all three modes
      expect(el.shadowRoot?.textContent).to.include('Standby');
      expect(el.shadowRoot?.textContent).to.include('Home');
      expect(el.shadowRoot?.textContent).to.include('Away');
    });

    it('shows action counts for each mode', async () => {
      const hass = createMockHass();
      const modes = createMockModes();
      modes[1].action_count = 5; // Home mode

      const el = await fixture<ModesTab>(html`
        <abode-modes-tab .hass=${hass}></abode-modes-tab>
      `);

      // @ts-expect-error - accessing private property for testing
      el._modes = modes;
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      expect(el.shadowRoot?.textContent).to.include('5 actions');
    });

    it('shows singular "action" for count of 1', async () => {
      const hass = createMockHass();
      const modes = createMockModes();
      modes[0].action_count = 1;

      const el = await fixture<ModesTab>(html`
        <abode-modes-tab .hass=${hass}></abode-modes-tab>
      `);

      // @ts-expect-error - accessing private property for testing
      el._modes = modes;
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      expect(el.shadowRoot?.textContent).to.include('1 action');
    });

    it('highlights active mode', async () => {
      const hass = createMockHass();
      const modes = createMockModes();
      modes[1].active = true; // Home is active

      const el = await fixture<ModesTab>(html`
        <abode-modes-tab .hass=${hass}></abode-modes-tab>
      `);

      // @ts-expect-error - accessing private property for testing
      el._modes = modes;
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const modeCards = el.shadowRoot?.querySelectorAll('.mode-card');
      expect(modeCards).to.have.length(3);

      // Find the active card
      const activeCard = Array.from(modeCards || []).find(
        card => card.classList.contains('active')
      );
      expect(activeCard).to.exist;
      expect(activeCard?.textContent).to.include('Home');
    });

    it('shows error state', async () => {
      const hass = createMockHass();

      const el = await fixture<ModesTab>(html`
        <abode-modes-tab .hass=${hass}></abode-modes-tab>
      `);

      // @ts-expect-error - accessing private property for testing
      el._error = 'Failed to load modes';
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const errorEl = el.shadowRoot?.querySelector('.error');
      expect(errorEl).to.exist;
      expect(errorEl?.textContent).to.include('Failed to load modes');
    });
  });

  describe('accessibility', () => {
    it('error has role="alert"', async () => {
      const hass = createMockHass();

      const el = await fixture<ModesTab>(html`
        <abode-modes-tab .hass=${hass}></abode-modes-tab>
      `);

      // @ts-expect-error - accessing private property for testing
      el._error = 'Test error';
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const errorEl = el.shadowRoot?.querySelector('.error');
      expect(errorEl?.getAttribute('role')).to.equal('alert');
    });
  });
});
