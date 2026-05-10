/**
 * Tests for the ModesTab component.
 *
 * Note: These tests focus on rendering behavior with pre-loaded data.
 * API integration is tested via E2E and integration tests.
 */

import { aTimeout, expect, fixture, html } from '@open-wc/testing';

import '../modes-tab.js';
import type { ModesTab } from '../modes-tab.js';
import type { HomeAssistant } from '../types.js';
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

    it('shows plural "actions" for count > 1', async () => {
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

      // Word-boundary anchored — substring match could be satisfied by
      // unrelated content elsewhere in the tree.
      expect(el.shadowRoot?.textContent).to.match(/\b5 actions\b/);
    });

    it('shows singular "action" (no trailing s) for count of 1', async () => {
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

      // The negative-lookahead `(?!s)` is what differentiates this from the
      // pre-fix substring-only assertion: "1 actions" satisfies `'1 action'`
      // as a substring, but fails this regex because the next char is `s`.
      expect(el.shadowRoot?.textContent).to.match(/\b1 action\b(?!s)/);
    });

    it('shows plural "actions" for count of 0', async () => {
      // English uses plural for zero ("0 actions"); guards against an
      // overly-aggressive `=== 1 ? singular : plural` ternary that mistakenly
      // pluralizes only on count > 1.
      const hass = createMockHass();
      const modes = createMockModes();
      modes[0].action_count = 0;

      const el = await fixture<ModesTab>(html`
        <abode-modes-tab .hass=${hass}></abode-modes-tab>
      `);

      // @ts-expect-error - accessing private property for testing
      el._modes = modes;
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      expect(el.shadowRoot?.textContent).to.match(/\b0 actions\b/);
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

  describe('lifecycle and async safety', () => {
    it('does not mutate state after disconnection while _loadData is in flight (#29)', async () => {
      let resolveModes!: (value: { modes: unknown[] }) => void;
      const modesPromise = new Promise<{ modes: unknown[] }>((resolve) => {
        resolveModes = resolve;
      });

      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/modes/list') {
            return modesPromise;
          }
          if (params.type === 'abode_security/actions/list') {
            return Promise.resolve({ actions: [] });
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ModesTab>(html`
        <abode-modes-tab .hass=${hass}></abode-modes-tab>
      `);

      el.remove();
      resolveModes({ modes: createMockModes() });
      await modesPromise;
      await aTimeout(0);

      // @ts-expect-error - accessing private property for testing
      expect(el._modes).to.deep.equal([], 'modes must not mutate after disconnect');
      // @ts-expect-error - accessing private property for testing
      expect(el._loading).to.equal(true, '_loading must remain true (state ignored)');
    });
  });
});
