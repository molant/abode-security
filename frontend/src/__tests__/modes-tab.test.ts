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
      const el = await fixture<ModesTab>(html` <abode-modes-tab .hass=${hass}></abode-modes-tab> `);

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

      const el = await fixture<ModesTab>(html` <abode-modes-tab .hass=${hass}></abode-modes-tab> `);

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

      const el = await fixture<ModesTab>(html` <abode-modes-tab .hass=${hass}></abode-modes-tab> `);

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

      const el = await fixture<ModesTab>(html` <abode-modes-tab .hass=${hass}></abode-modes-tab> `);

      // @ts-expect-error - accessing private property for testing
      el._modes = modes;
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      expect(el.shadowRoot?.textContent).to.match(/\b0 actions\b/);
    });

    // #123 — disabled actions were invisible in the mode card: the badge
    // showed only enabled actions and the action list filtered them out,
    // so users saw "0 actions" / "No actions configured" while a disabled
    // action existed for the mode. These tests pin the new behavior.
    it('badge shows "{n} disabled" when only disabled actions exist for a mode', async () => {
      const hass = createMockHass();
      const modes = createMockModes();
      // Standby: 0 enabled, 1 disabled.
      modes[0].action_count = 0;
      modes[0].disabled_action_count = 1;

      const el = await fixture<ModesTab>(html` <abode-modes-tab .hass=${hass}></abode-modes-tab> `);
      // @ts-expect-error - accessing private property for testing
      el._modes = modes;
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const standbyCard = Array.from(el.shadowRoot?.querySelectorAll('.mode-card') ?? []).find(
        (card) => card.textContent?.includes('Standby'),
      );
      expect(standbyCard?.textContent).to.match(/\b1 disabled\b/);
      expect(standbyCard?.textContent).to.not.match(/\b0 actions\b/);
    });

    it('badge shows "{a} active, {d} disabled" when both kinds exist', async () => {
      const hass = createMockHass();
      const modes = createMockModes();
      // Away: 2 enabled, 3 disabled.
      modes[2].action_count = 2;
      modes[2].disabled_action_count = 3;

      const el = await fixture<ModesTab>(html` <abode-modes-tab .hass=${hass}></abode-modes-tab> `);
      // @ts-expect-error - accessing private property for testing
      el._modes = modes;
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const awayCard = Array.from(el.shadowRoot?.querySelectorAll('.mode-card') ?? []).find(
        (card) => card.textContent?.includes('Away'),
      );
      expect(awayCard?.textContent).to.match(/\b2 active\b/);
      expect(awayCard?.textContent).to.match(/\b3 disabled\b/);
    });

    it('renders disabled actions in the mode card list with a disabled marker', async () => {
      const hass = createMockHass();
      const modes = createMockModes();
      // Away: 0 enabled, 1 disabled.
      modes[2].action_count = 0;
      modes[2].disabled_action_count = 1;

      const el = await fixture<ModesTab>(html` <abode-modes-tab .hass=${hass}></abode-modes-tab> `);
      // @ts-expect-error - accessing private property for testing
      el._modes = modes;
      // @ts-expect-error - accessing private property for testing
      el._actions = [
        {
          id: 'a1',
          name: 'Call the police',
          modes: ['away'],
          sensor_entity_ids: [],
          alarm_entity_ids: [],
          enabled: false,
          delay_seconds: 0,
          last_triggered: null,
          trigger_count: 0,
        },
      ];
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const awayCard = Array.from(el.shadowRoot?.querySelectorAll('.mode-card') ?? []).find(
        (card) => card.textContent?.includes('Away'),
      );
      // The action must appear in the list, not be hidden behind
      // "No actions configured".
      expect(awayCard?.textContent).to.include('Call the police');
      expect(awayCard?.textContent).to.not.include('No actions configured');
      // The disabled action list item must carry a visible disabled marker
      // so users can distinguish it from enabled ones.
      const disabledItem = awayCard?.querySelector('.action-list li.disabled');
      expect(disabledItem, 'disabled action <li> must carry the .disabled class').to.exist;
    });

    it('highlights active mode', async () => {
      const hass = createMockHass();
      const modes = createMockModes();
      modes[1].active = true; // Home is active

      const el = await fixture<ModesTab>(html` <abode-modes-tab .hass=${hass}></abode-modes-tab> `);

      // @ts-expect-error - accessing private property for testing
      el._modes = modes;
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const modeCards = el.shadowRoot?.querySelectorAll('.mode-card');
      expect(modeCards).to.have.length(3);

      // Find the active card
      const activeCard = Array.from(modeCards || []).find((card) =>
        card.classList.contains('active'),
      );
      expect(activeCard).to.exist;
      expect(activeCard?.textContent).to.include('Home');
    });

    it('shows error state', async () => {
      const hass = createMockHass();

      const el = await fixture<ModesTab>(html` <abode-modes-tab .hass=${hass}></abode-modes-tab> `);

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

      const el = await fixture<ModesTab>(html` <abode-modes-tab .hass=${hass}></abode-modes-tab> `);

      // @ts-expect-error - accessing private property for testing
      el._error = 'Test error';
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const errorEl = el.shadowRoot?.querySelector('.error');
      expect(errorEl?.getAttribute('role')).to.equal('alert');
    });
  });

  describe('mode switching (#1)', () => {
    it('clicking a non-active mode card opens a confirm dialog', async () => {
      const hass = createMockHass();
      const el = await fixture<ModesTab>(html` <abode-modes-tab .hass=${hass}></abode-modes-tab> `);

      // createMockModes(): standby (inactive), home (active), away (inactive).
      // @ts-expect-error - accessing private property for testing
      el._modes = createMockModes();
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      // Click the switch button on the away (inactive) card.
      const awayCard = Array.from(el.shadowRoot?.querySelectorAll('.mode-card') ?? []).find(
        (card) => card.textContent?.includes('Away'),
      ) as HTMLElement;
      const switchBtn = awayCard.querySelector('.switch-button') as HTMLButtonElement;
      expect(switchBtn, 'inactive card must render a switch button').to.exist;
      switchBtn.click();
      await elementUpdated(el);

      const modal = el.shadowRoot?.querySelector('abode-modal');
      expect(modal, 'confirm dialog must open').to.exist;
      expect(modal?.getAttribute('variant')).to.equal('alertdialog');
      // Body text should reference the target mode by name.
      expect(el.shadowRoot?.textContent).to.include('Away');
    });

    it('does not render a switch button on the active mode card', async () => {
      const hass = createMockHass();
      const el = await fixture<ModesTab>(html` <abode-modes-tab .hass=${hass}></abode-modes-tab> `);

      // @ts-expect-error - accessing private property for testing
      el._modes = createMockModes(); // home is active
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const homeCard = Array.from(el.shadowRoot?.querySelectorAll('.mode-card') ?? []).find(
        (card) => card.classList.contains('active'),
      ) as HTMLElement;
      const switchBtn = homeCard.querySelector('.switch-button');
      expect(switchBtn, 'active card must not render a switch button').to.equal(null);
    });

    it('confirming the dialog calls setMode WS with the target mode_id', async () => {
      let setCall: { type: string; mode_id?: string } | null = null;
      const hass = createMockHass({
        callWS: ((params: { type: string; mode_id?: string }) => {
          if (params.type === 'abode_security/modes/set') {
            setCall = params;
            return Promise.resolve({ success: true, mode_id: params.mode_id });
          }
          if (params.type === 'abode_security/modes/list') {
            return Promise.resolve({ modes: createMockModes() });
          }
          if (params.type === 'abode_security/actions/list') {
            return Promise.resolve({ actions: [] });
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ModesTab>(html` <abode-modes-tab .hass=${hass}></abode-modes-tab> `);
      // @ts-expect-error - accessing private property for testing
      el._modes = createMockModes();
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      // Open dialog for Away.
      const awayCard = Array.from(el.shadowRoot?.querySelectorAll('.mode-card') ?? []).find(
        (card) => card.textContent?.includes('Away'),
      ) as HTMLElement;
      (awayCard.querySelector('.switch-button') as HTMLButtonElement).click();
      await elementUpdated(el);

      // Click the dialog's confirm button (slot="footer", class includes 'primary').
      const confirmBtn = Array.from(
        el.shadowRoot?.querySelectorAll('button[slot="footer"]') ?? [],
      ).find((b) => b.classList.contains('primary')) as HTMLButtonElement;
      expect(confirmBtn, 'confirm button must exist in the dialog').to.exist;
      confirmBtn.click();
      await aTimeout(0);
      await elementUpdated(el);

      expect(setCall, 'setMode WS must be called').to.not.equal(null);
      expect(setCall!.type).to.equal('abode_security/modes/set');
      expect(setCall!.mode_id).to.equal('away');
    });

    it('cancelling the dialog does not call setMode', async () => {
      let setCalled = false;
      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/modes/set') {
            setCalled = true;
            return Promise.resolve({ success: true });
          }
          // Explicit list/actions mocks — fetchModes/fetchActions extract
          // `.modes`/`.actions` from the response. Returning the loose
          // `{ success: true }` would resolve those to `undefined`, which
          // (post-PR10's `?? []` removal) would crash the next render.
          if (params.type === 'abode_security/modes/list') {
            return Promise.resolve({ modes: [] });
          }
          if (params.type === 'abode_security/actions/list') {
            return Promise.resolve({ actions: [] });
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ModesTab>(html` <abode-modes-tab .hass=${hass}></abode-modes-tab> `);
      // @ts-expect-error - accessing private property for testing
      el._modes = createMockModes();
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const awayCard = Array.from(el.shadowRoot?.querySelectorAll('.mode-card') ?? []).find(
        (card) => card.textContent?.includes('Away'),
      ) as HTMLElement;
      (awayCard.querySelector('.switch-button') as HTMLButtonElement).click();
      await elementUpdated(el);

      // Cancel button.
      const cancelBtn = Array.from(
        el.shadowRoot?.querySelectorAll('button[slot="footer"]') ?? [],
      ).find((b) => b.classList.contains('cancel')) as HTMLButtonElement;
      cancelBtn.click();
      await elementUpdated(el);

      expect(setCalled).to.equal(false);
      expect(el.shadowRoot?.querySelector('abode-modal')).to.equal(null);
    });

    it('keeps the mode grid visible during the post-switch refresh (no loading flash)', async () => {
      // The post-switch refresh must not flip _loading=true — that would
      // replace the grid (and the "Switching…" pending label on the target
      // card) with "Loading modes...". Achieved by passing `silent: true`
      // to _loadData.
      let modesListCalls = 0;
      let resolveRefresh!: (v: { modes: ReturnType<typeof createMockModes> }) => void;
      const refreshPromise = new Promise<{ modes: ReturnType<typeof createMockModes> }>(
        (resolve) => {
          resolveRefresh = resolve;
        },
      );

      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/modes/set') {
            return Promise.resolve({ success: true });
          }
          if (params.type === 'abode_security/modes/list') {
            modesListCalls += 1;
            // First call: initial connectedCallback load. Resolve immediately.
            // Second call: post-switch refresh — keep pending so we can
            // observe the mid-refresh DOM state.
            if (modesListCalls === 1) {
              return Promise.resolve({ modes: createMockModes() });
            }
            return refreshPromise;
          }
          if (params.type === 'abode_security/actions/list') {
            return Promise.resolve({ actions: [] });
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ModesTab>(html` <abode-modes-tab .hass=${hass}></abode-modes-tab> `);
      // Wait for initial load to settle.
      await aTimeout(0);
      await elementUpdated(el);

      // Click switch on Away → confirm.
      const awayCard = Array.from(el.shadowRoot?.querySelectorAll('.mode-card') ?? []).find(
        (card) => card.textContent?.includes('Away'),
      ) as HTMLElement;
      (awayCard.querySelector('.switch-button') as HTMLButtonElement).click();
      await elementUpdated(el);
      const confirmBtn = Array.from(
        el.shadowRoot?.querySelectorAll('button[slot="footer"]') ?? [],
      ).find((b) => b.classList.contains('primary')) as HTMLButtonElement;
      confirmBtn.click();
      // setMode resolves → _loadData fires (suspended on refreshPromise).
      // Yield enough microtasks for the chain to suspend on the controlled
      // promise.
      await aTimeout(0);
      await elementUpdated(el);

      // Mid-refresh assertions: grid is still rendered and the "Loading
      // modes..." spinner is NOT shown.
      const cards = el.shadowRoot?.querySelectorAll('.mode-card');
      expect(cards?.length, 'mode grid must stay visible').to.be.greaterThan(0);
      expect(el.shadowRoot?.textContent ?? '').to.not.include('Loading modes...');
      // The target card still shows the pending label.
      const awayCardMid = Array.from(cards ?? []).find((c) => c.textContent?.includes('Away'));
      expect(awayCardMid?.textContent).to.include('Switching');

      // Resolve so the test runner exits cleanly.
      resolveRefresh({ modes: createMockModes() });
      await refreshPromise;
      await aTimeout(0);
    });

    it('routes a post-switch _loadData failure to the banner, not the full-page error', async () => {
      // setMode succeeds, but the immediate refresh fails. The previous
      // implementation let _loadData write to `_error`, which would render
      // a full-page error that wipes the just-confirmed switch.
      let setSucceeded = false;
      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/modes/set') {
            setSucceeded = true;
            return Promise.resolve({ success: true });
          }
          if (params.type === 'abode_security/modes/list' && setSucceeded) {
            return Promise.reject(new Error('refresh blip'));
          }
          if (params.type === 'abode_security/modes/list') {
            return Promise.resolve({ modes: createMockModes() });
          }
          if (params.type === 'abode_security/actions/list') {
            return Promise.resolve({ actions: [] });
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ModesTab>(html` <abode-modes-tab .hass=${hass}></abode-modes-tab> `);
      // @ts-expect-error - accessing private property for testing
      el._modes = createMockModes();
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const awayCard = Array.from(el.shadowRoot?.querySelectorAll('.mode-card') ?? []).find(
        (card) => card.textContent?.includes('Away'),
      ) as HTMLElement;
      (awayCard.querySelector('.switch-button') as HTMLButtonElement).click();
      await elementUpdated(el);
      const confirmBtn = Array.from(
        el.shadowRoot?.querySelectorAll('button[slot="footer"]') ?? [],
      ).find((b) => b.classList.contains('primary')) as HTMLButtonElement;
      confirmBtn.click();
      await aTimeout(0);
      await elementUpdated(el);

      // Banner present, full-page error absent, mode grid still rendered.
      const banner = el.shadowRoot?.querySelector('.operation-error');
      expect(banner, 'refresh failure must surface as banner').to.exist;
      expect(banner?.textContent).to.include('refresh failed');
      const fullPageError = el.shadowRoot?.querySelector('.error');
      expect(fullPageError, 'full-page error must NOT be rendered').to.equal(null);
      expect(el.shadowRoot?.querySelectorAll('.mode-card')?.length).to.be.greaterThan(0);
    });

    it('shows an error banner when setMode rejects', async () => {
      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/modes/set') {
            return Promise.reject(new Error('panel offline'));
          }
          if (params.type === 'abode_security/modes/list') {
            return Promise.resolve({ modes: createMockModes() });
          }
          if (params.type === 'abode_security/actions/list') {
            return Promise.resolve({ actions: [] });
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ModesTab>(html` <abode-modes-tab .hass=${hass}></abode-modes-tab> `);
      // @ts-expect-error - accessing private property for testing
      el._modes = createMockModes();
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const awayCard = Array.from(el.shadowRoot?.querySelectorAll('.mode-card') ?? []).find(
        (card) => card.textContent?.includes('Away'),
      ) as HTMLElement;
      (awayCard.querySelector('.switch-button') as HTMLButtonElement).click();
      await elementUpdated(el);
      const confirmBtn = Array.from(
        el.shadowRoot?.querySelectorAll('button[slot="footer"]') ?? [],
      ).find((b) => b.classList.contains('primary')) as HTMLButtonElement;
      confirmBtn.click();
      await aTimeout(0);
      await elementUpdated(el);

      const banner = el.shadowRoot?.querySelector('.operation-error');
      expect(banner, 'error banner must render after setMode rejection').to.exist;
      // We surface a fixed user-facing label rather than err.message — keeps
      // backend internals out of the UI (mirrors actions-tab convention).
      expect(banner?.textContent).to.include('Failed to change mode');
      expect(banner?.getAttribute('role')).to.equal('alert');
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

      const el = await fixture<ModesTab>(html` <abode-modes-tab .hass=${hass}></abode-modes-tab> `);

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
