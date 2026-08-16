/**
 * Tests for the ActionsTab component.
 *
 * Note: These tests focus on rendering behavior with pre-loaded data.
 * API integration is tested via E2E and integration tests.
 */

import { aTimeout, expect, fixture, html } from '@open-wc/testing';

import '../actions-tab.js';
import type { ActionsTab } from '../actions-tab.js';
import type { AbodeAction, HomeAssistant } from '../types.js';
import { createMockHass, createMockAction, elementUpdated, setState } from './test-helpers.js';

describe('ActionsTab', () => {
  describe('rendering with data', () => {
    it('shows empty state when no actions exist', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);

      // @ts-expect-error - accessing private property for testing
      el._actions = [];
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      expect(el.shadowRoot?.textContent).to.include('No actions configured');
      expect(el.shadowRoot?.textContent).to.include('Create your first action');
    });

    it('shows Add Action button', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);

      // @ts-expect-error - accessing private property for testing
      el._actions = [];
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const addButton = el.shadowRoot?.querySelector('.add-button');
      expect(addButton).to.exist;
      expect(addButton?.textContent).to.include('Add Action');
    });

    it('renders action list when actions exist', async () => {
      const hass = createMockHass();
      const actions = [
        createMockAction({ id: '1', name: 'Action 1' }),
        createMockAction({ id: '2', name: 'Action 2' }),
      ];

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);

      // @ts-expect-error - accessing private property for testing
      el._actions = actions;
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const actionRows = el.shadowRoot?.querySelectorAll('.action-row');
      expect(actionRows?.length).to.equal(2);
      expect(el.shadowRoot?.textContent).to.include('Action 1');
      expect(el.shadowRoot?.textContent).to.include('Action 2');
    });

    it('shows mode chips for each action', async () => {
      const hass = createMockHass();
      const actions = [createMockAction({ modes: ['home', 'away'] })];

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);

      // @ts-expect-error - accessing private property for testing
      el._actions = actions;
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const modeChips = el.shadowRoot?.querySelectorAll('.mode-chip');
      expect(modeChips?.length).to.equal(2);
    });

    it('shows disabled styling for disabled actions', async () => {
      const hass = createMockHass();
      const actions = [createMockAction({ enabled: false })];

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);

      // @ts-expect-error - accessing private property for testing
      el._actions = actions;
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const actionRow = el.shadowRoot?.querySelector('.action-row');
      expect(actionRow?.classList.contains('disabled')).to.be.true;
    });

    it('shows error state', async () => {
      const hass = createMockHass();

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);

      // @ts-expect-error - accessing private property for testing
      el._error = 'Network error';
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const errorEl = el.shadowRoot?.querySelector('.error');
      expect(errorEl).to.exist;
      expect(errorEl?.textContent).to.include('Network error');
    });
  });

  describe('interactions', () => {
    it('opens editor when clicking Add Action', async () => {
      const hass = createMockHass();

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);

      // @ts-expect-error - accessing private property for testing
      el._actions = [];
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const addButton = el.shadowRoot?.querySelector('.add-button') as HTMLButtonElement;
      addButton?.click();

      await elementUpdated(el);

      const editor = el.shadowRoot?.querySelector('abode-action-editor');
      expect(editor).to.exist;
    });

    it('shows delete confirmation dialog', async () => {
      const hass = createMockHass();
      const actions = [createMockAction()];

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);

      // @ts-expect-error - accessing private property for testing
      el._actions = actions;
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const deleteButton = el.shadowRoot?.querySelector('.icon-button.delete') as HTMLButtonElement;
      deleteButton?.click();

      await elementUpdated(el);

      const modal = el.shadowRoot?.querySelector('abode-modal');
      expect(modal).to.exist;
      expect(modal?.getAttribute('heading')).to.equal('Delete Action');
      // Body text is slotted into the modal but lives in the parent's shadow tree.
      expect(el.shadowRoot?.textContent).to.include('cannot be undone');
    });

    it('shows test confirmation dialog', async () => {
      const hass = createMockHass();
      const actions = [createMockAction()];

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);

      // @ts-expect-error - accessing private property for testing
      el._actions = actions;
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const testButton = el.shadowRoot?.querySelector(
        'button[aria-label="Test action"]',
      ) as HTMLButtonElement;
      testButton?.click();

      await elementUpdated(el);

      const modal = el.shadowRoot?.querySelector('abode-modal');
      expect(modal).to.exist;
      expect(modal?.getAttribute('heading')).to.equal('Test Action');
      expect(el.shadowRoot?.textContent).to.include('trigger real alarms');
    });
  });

  describe('confirm dialog lifecycle', () => {
    it('removes the captured action when delete resolves, even if confirm state is cleared mid-await', async () => {
      let resolveDelete!: () => void;
      const deletePromise = new Promise<void>((resolve) => {
        resolveDelete = resolve;
      });

      const hass = createMockHass({
        callWS: (async (params: { type: string }) => {
          if (params.type === 'abode_security/actions/delete') {
            return deletePromise;
          }
          return { success: true };
        }) as HomeAssistant['callWS'],
      });

      const actions = [
        createMockAction({ id: 'a1', name: 'A1' }),
        createMockAction({ id: 'a2', name: 'A2' }),
      ];

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);
      // @ts-expect-error - accessing private property for testing
      el._actions = actions;
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      // Open delete confirm for a1, then start the delete (don't await).
      // @ts-expect-error - accessing private method for testing
      el._requestDelete(actions[0]);
      await elementUpdated(el);
      // @ts-expect-error - accessing private method for testing
      const inFlight = el._confirmDelete();

      // Simulate state being cleared mid-await (cancel, re-entry, refactor).
      // The fix captures `action` into a local before await, so this should
      // not affect which action is removed.
      // @ts-expect-error - accessing private property for testing
      el._confirm = null;

      // Resolve the network call.
      resolveDelete();
      await inFlight;
      await elementUpdated(el);

      // a1 should be removed (captured before await); a2 stays.
      // @ts-expect-error - accessing private property for testing
      expect(el._actions.map((a: { id: string }) => a.id)).to.deep.equal(['a2']);
      // @ts-expect-error - accessing private property for testing
      expect(el._operationError).to.equal(null);
    });

    it('opening test confirm replaces an open delete confirm (single confirm at a time)', async () => {
      const hass = createMockHass();
      const actions = [
        createMockAction({ id: 'a1', name: 'A1' }),
        createMockAction({ id: 'a2', name: 'A2' }),
      ];

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);
      // @ts-expect-error - accessing private property for testing
      el._actions = actions;
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      // Request delete for a1, then test for a2.
      // @ts-expect-error - accessing private method for testing
      el._requestDelete(actions[0]);
      // @ts-expect-error - accessing private method for testing
      el._requestTest(actions[1]);
      await elementUpdated(el);

      // Exactly one confirm is open, and it's the test dialog targeting a2.
      const modals = el.shadowRoot?.querySelectorAll('abode-modal');
      expect(modals?.length).to.equal(1);
      expect(modals?.[0]?.getAttribute('heading')).to.equal('Test Action');
      expect(el.shadowRoot?.textContent).to.include('trigger real alarms');
      expect(el.shadowRoot?.textContent).to.include('A2');
    });

    it('cancelling a delete confirm clears confirm state without throwing', async () => {
      const hass = createMockHass();
      const actions = [createMockAction({ id: 'a1', name: 'A1' })];

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);
      // @ts-expect-error - accessing private property for testing
      el._actions = actions;
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      // Open delete dialog
      const deleteButton = el.shadowRoot?.querySelector('.icon-button.delete') as HTMLButtonElement;
      deleteButton?.click();
      await elementUpdated(el);

      // Click cancel
      const cancelButton = el.shadowRoot?.querySelector(
        '.dialog-button.cancel',
      ) as HTMLButtonElement;
      cancelButton?.click();
      await elementUpdated(el);

      // Dialog gone, action list unchanged.
      expect(el.shadowRoot?.querySelector('abode-modal')).to.equal(null);
      // @ts-expect-error - accessing private property for testing
      expect(el._confirm).to.equal(null);
      // @ts-expect-error - accessing private property for testing
      expect(el._actions.length).to.equal(1);
    });
  });

  describe('recent triggers', () => {
    it('shows recent triggers section', async () => {
      const hass = createMockHass();

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);

      // @ts-expect-error - accessing private property for testing
      el._actions = [];
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      expect(el.shadowRoot?.textContent).to.include('Recent Triggers');
    });

    it('shows "No recent triggers" when none exist', async () => {
      const hass = createMockHass();

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);

      // @ts-expect-error - accessing private property for testing
      el._actions = [createMockAction({ last_triggered: null })];
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      expect(el.shadowRoot?.textContent).to.include('No recent triggers');
    });

    it('shows recent triggers when they exist', async () => {
      const hass = createMockHass();
      const recentTime = new Date().toISOString();

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);

      // @ts-expect-error - accessing private property for testing
      el._actions = [createMockAction({ name: 'Recent Action', last_triggered: recentTime })];
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const triggerItems = el.shadowRoot?.querySelectorAll('.trigger-item');
      expect(triggerItems?.length).to.equal(1);
      expect(el.shadowRoot?.textContent).to.include('Recent Action');
    });
  });

  describe('accessibility', () => {
    it('has accessible Add Action button', async () => {
      const hass = createMockHass();

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);

      // @ts-expect-error - accessing private property for testing
      el._actions = [];
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const addButton = el.shadowRoot?.querySelector('.add-button');
      expect(addButton?.getAttribute('aria-label')).to.equal('Add new action');
    });

    it('action list has role="list"', async () => {
      const hass = createMockHass();

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);

      // @ts-expect-error - accessing private property for testing
      el._actions = [createMockAction()];
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const list = el.shadowRoot?.querySelector('.actions-list');
      expect(list?.getAttribute('role')).to.equal('list');
    });

    it('action rows have role="listitem"', async () => {
      const hass = createMockHass();

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);

      // @ts-expect-error - accessing private property for testing
      el._actions = [createMockAction()];
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const row = el.shadowRoot?.querySelector('.action-row');
      expect(row?.getAttribute('role')).to.equal('listitem');
    });

    it('delete dialog uses alertdialog variant', async () => {
      const hass = createMockHass();

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);

      // @ts-expect-error - accessing private property for testing
      el._actions = [createMockAction()];
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      // Open delete dialog
      const deleteButton = el.shadowRoot?.querySelector('.icon-button.delete') as HTMLButtonElement;
      deleteButton?.click();
      await elementUpdated(el);

      // <abode-modal> owns role/aria-modal — those are covered in abode-modal.test.ts.
      // Here we just verify the action-tab passes the right variant prop.
      const modal = el.shadowRoot?.querySelector('abode-modal');
      expect(modal?.getAttribute('variant')).to.equal('alertdialog');
    });
  });

  describe('lifecycle and async safety', () => {
    it('does not mutate state after disconnection while _loadData is in flight (#29)', async () => {
      let resolveActions!: (value: { actions: unknown[] }) => void;
      const actionsPromise = new Promise<{ actions: unknown[] }>((resolve) => {
        resolveActions = resolve;
      });

      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/actions/list') {
            return actionsPromise;
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);

      // _loadData is in flight, awaiting actionsPromise. Disconnect first…
      el.remove();

      // …then resolve. The result must be discarded.
      resolveActions({ actions: [createMockAction({ id: 'late', name: 'Late' })] });
      await actionsPromise;
      await aTimeout(0);

      // @ts-expect-error - accessing private property for testing
      expect(el._actions).to.deep.equal([], 'actions must not mutate after disconnect');
      // @ts-expect-error - accessing private property for testing
      expect(el._loading).to.equal(true, '_loading must remain true (state ignored)');
    });

    it('does not set _error after disconnection when _loadData rejects (#29)', async () => {
      let rejectActions!: (err: Error) => void;
      const actionsPromise = new Promise<unknown>((_, reject) => {
        rejectActions = reject;
      });

      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/actions/list') {
            return actionsPromise;
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);

      el.remove();
      rejectActions(new Error('socket dropped'));
      // The rejection must not leak as an unhandled promise — the catch in
      // _loadData handles it; we just yield once to let it run.
      await actionsPromise.catch(() => undefined);
      await aTimeout(0);

      // @ts-expect-error - accessing private property for testing
      expect(el._error).to.equal(null, '_error must not be set after disconnect');
    });
  });

  // --- #31 Mutation flow tests -------------------------------------------
  // These exercise the success/error paths of every state-changing handler:
  // toggle, delete, test. Existing tests stopped at "does the dialog open?"
  // — these go further and assert the resulting state mutations and error
  // surface, since these flows can fire real Abode hardware.

  describe('_toggleAction (#31)', () => {
    it('updates the action in _actions on success', async () => {
      const original = createMockAction({ id: 'a1', enabled: true });
      const updated = createMockAction({ id: 'a1', enabled: false });
      // Custom callWS throws on unmocked types — same effect as strict mode,
      // but `strict` only affects the default callWS (see test-helpers.ts).
      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/actions/list') {
            return Promise.resolve({ actions: [] });
          }
          if (params.type === 'abode_security/actions/update') {
            return Promise.resolve(updated);
          }
          throw new Error(`Unmocked WS: ${params.type}`);
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);
      await setState(el, { _actions: [original], _loading: false } as Partial<ActionsTab>);

      const toggle = el.shadowRoot?.querySelector('input[type="checkbox"]') as HTMLInputElement;
      toggle.click();
      await aTimeout(0);
      await elementUpdated(el);

      // Action replaced with the response — `enabled` flipped.
      // @ts-expect-error - accessing private property for testing
      expect((el._actions as AbodeAction[])[0].enabled).to.equal(false);
      // _togglingIds drained on completion.
      // @ts-expect-error - accessing private property for testing
      expect((el._togglingIds as Set<string>).size).to.equal(0);
      // No operation error.
      // @ts-expect-error - accessing private property for testing
      expect(el._operationError).to.equal(null);
    });

    it('marks the row as toggling while the WS call is in flight', async () => {
      const original = createMockAction({ id: 'a1', enabled: true });
      const updated = createMockAction({ id: 'a1', enabled: false });
      let resolveUpdate!: () => void;
      const updatePromise = new Promise<AbodeAction>((resolve) => {
        resolveUpdate = () => resolve(updated);
      });
      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/actions/update') {
            return updatePromise;
          }
          if (params.type === 'abode_security/actions/list') {
            return Promise.resolve({ actions: [] });
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);
      await setState(el, { _actions: [original], _loading: false } as Partial<ActionsTab>);

      (el.shadowRoot?.querySelector('input[type="checkbox"]') as HTMLInputElement).click();
      // Microtask drain — handler has assigned to _togglingIds but the WS
      // call is still suspended on updatePromise.
      await Promise.resolve();
      await elementUpdated(el);

      // @ts-expect-error - accessing private property for testing
      expect((el._togglingIds as Set<string>).has('a1')).to.equal(true);

      resolveUpdate();
      await aTimeout(0);
      await elementUpdated(el);
      // @ts-expect-error - accessing private property for testing
      expect((el._togglingIds as Set<string>).size).to.equal(0);
    });

    it('surfaces a contextual error and clears toggling state on failure', async () => {
      const original = createMockAction({ id: 'a1', enabled: true });
      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/actions/update') {
            return Promise.reject(new Error('boom'));
          }
          if (params.type === 'abode_security/actions/list') {
            return Promise.resolve({ actions: [] });
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);
      await setState(el, { _actions: [original], _loading: false } as Partial<ActionsTab>);

      (el.shadowRoot?.querySelector('input[type="checkbox"]') as HTMLInputElement).click();
      await aTimeout(0);
      await elementUpdated(el);

      // Error wording reflects the *intended direction* — the original was
      // enabled, so the user attempted to disable. This is the test that
      // would catch a flipped-condition regression in the error string.
      // @ts-expect-error - accessing private property for testing
      expect(el._operationError).to.equal('Failed to disable action');
      // @ts-expect-error - accessing private property for testing
      expect((el._togglingIds as Set<string>).size).to.equal(0);
      // No optimistic flip — original action unchanged.
      // @ts-expect-error - accessing private property for testing
      expect((el._actions as AbodeAction[])[0].enabled).to.equal(true);
    });

    it('error wording flips when toggling a disabled action on', async () => {
      const original = createMockAction({ id: 'a1', enabled: false });
      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/actions/update') {
            return Promise.reject(new Error('boom'));
          }
          if (params.type === 'abode_security/actions/list') {
            return Promise.resolve({ actions: [] });
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);
      await setState(el, { _actions: [original], _loading: false } as Partial<ActionsTab>);

      (el.shadowRoot?.querySelector('input[type="checkbox"]') as HTMLInputElement).click();
      await aTimeout(0);
      await elementUpdated(el);

      // @ts-expect-error - accessing private property for testing
      expect(el._operationError).to.equal('Failed to enable action');
    });
  });

  describe('_confirmDelete error path (#31)', () => {
    it('sets _operationError and clears confirm state when delete WS rejects', async () => {
      const action = createMockAction({ id: 'a1', name: 'A1' });
      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/actions/delete') {
            return Promise.reject(new Error('server error'));
          }
          if (params.type === 'abode_security/actions/list') {
            return Promise.resolve({ actions: [] });
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);
      await setState(el, { _actions: [action], _loading: false } as Partial<ActionsTab>);

      // @ts-expect-error - accessing private method for testing
      el._requestDelete(action);
      await elementUpdated(el);
      // @ts-expect-error - accessing private method for testing
      await el._confirmDelete();
      await elementUpdated(el);

      // @ts-expect-error - accessing private property for testing
      expect(el._operationError).to.equal('Failed to delete action');
      // @ts-expect-error - accessing private property for testing
      expect(el._confirm).to.equal(null, 'confirm cleared even on failure');
      // Action still present (not removed since delete failed).
      // @ts-expect-error - accessing private property for testing
      expect((el._actions as AbodeAction[]).length).to.equal(1);
    });
  });

  describe('_confirmTest (#31)', () => {
    it('closes the dialog and clears state on successful test', async () => {
      let testCalled = false;
      const action = createMockAction({ id: 'a1', name: 'A1' });
      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/actions/test') {
            testCalled = true;
            return Promise.resolve({ success: true });
          }
          if (params.type === 'abode_security/actions/list') {
            return Promise.resolve({ actions: [] });
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);
      await setState(el, { _actions: [action], _loading: false } as Partial<ActionsTab>);

      // @ts-expect-error - accessing private method for testing
      el._requestTest(action);
      await elementUpdated(el);
      // @ts-expect-error - accessing private method for testing
      await el._confirmTest();
      await elementUpdated(el);

      expect(testCalled).to.equal(true);
      // @ts-expect-error - accessing private property for testing
      expect(el._confirm).to.equal(null);
      // @ts-expect-error - accessing private property for testing
      expect(el._operationError).to.equal(null);
    });

    it('sets _operationError when test WS rejects', async () => {
      const action = createMockAction({ id: 'a1', name: 'A1' });
      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/actions/test') {
            return Promise.reject(new Error('alarm offline'));
          }
          if (params.type === 'abode_security/actions/list') {
            return Promise.resolve({ actions: [] });
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);
      await setState(el, { _actions: [action], _loading: false } as Partial<ActionsTab>);

      // @ts-expect-error - accessing private method for testing
      el._requestTest(action);
      await elementUpdated(el);
      // @ts-expect-error - accessing private method for testing
      await el._confirmTest();
      await elementUpdated(el);

      // The backend's reason is surfaced, not swallowed behind a generic
      // string: a test that raised no alarm has to say so.
      // @ts-expect-error - accessing private property for testing
      expect(el._operationError).to.equal('Failed to test action: alarm offline');
      // @ts-expect-error - accessing private property for testing
      expect(el._confirm).to.equal(null, 'confirm still closes on failure');
    });

    it('falls back to a generic message when the rejection carries none', async () => {
      const action = createMockAction({ id: 'a1', name: 'A1' });
      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/actions/test') {
            return Promise.reject({});
          }
          if (params.type === 'abode_security/actions/list') {
            return Promise.resolve({ actions: [] });
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);
      await setState(el, { _actions: [action], _loading: false } as Partial<ActionsTab>);

      // @ts-expect-error - accessing private method for testing
      el._requestTest(action);
      await elementUpdated(el);
      // @ts-expect-error - accessing private method for testing
      await el._confirmTest();
      await elementUpdated(el);

      // @ts-expect-error - accessing private property for testing
      expect(el._operationError).to.equal('Failed to test action');
    });
  });

  describe('_loadData error path (#31)', () => {
    it('sets _error when fetchActions rejects', async () => {
      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/actions/list') {
            return Promise.reject(new Error('cannot reach server'));
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);
      // Wait for connectedCallback's _loadData to reject and re-render.
      await aTimeout(0);
      await elementUpdated(el);

      // @ts-expect-error - accessing private property for testing
      expect(el._error).to.equal('cannot reach server');
      const errorEl = el.shadowRoot?.querySelector('.error');
      expect(errorEl, 'full-page error renders').to.exist;
    });
  });

  describe('_formatTime boundaries (#31)', () => {
    // Drives _formatTime directly. Each row is `[secondsAgo, expectedOutput]`
    // — we use a fixture table because the function has 4 in-bucket boundaries
    // and a separate test per bucket would be repetitive. The 7d locale
    // fallback is asserted separately below because its expected value is
    // locale-dependent.
    const cases: Array<[number, string]> = [
      [0, 'Just now'],
      [59, 'Just now'], // <60s still "Just now"
      [60, '1m ago'],
      [60 * 30, '30m ago'],
      [60 * 59, '59m ago'],
      [60 * 60, '1h ago'],
      [60 * 60 * 23, '23h ago'],
      [60 * 60 * 24, '1d ago'],
      [60 * 60 * 24 * 6, '6d ago'],
    ];

    cases.forEach(([secondsAgo, expected]) => {
      it(`renders "${expected}" for ${secondsAgo}s ago`, async () => {
        const hass = createMockHass();
        const el = await fixture<ActionsTab>(html`
          <abode-actions-tab .hass=${hass}></abode-actions-tab>
        `);
        const iso = new Date(Date.now() - secondsAgo * 1000).toISOString();
        // @ts-expect-error - calling private method for testing
        const result = el._formatTime(iso) as string;
        expect(result).to.equal(expected);
      });
    });

    it('falls back to locale-formatted date at the 7d boundary', async () => {
      // Asserts equality against `new Date(iso).toLocaleDateString()`
      // computed in-test rather than a brittle `\d` regex (which would
      // fail in locales using non-ASCII numerals like Arabic-Indic).
      // Source and expected share the same JS environment, so locale
      // mismatch is impossible.
      const hass = createMockHass();
      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);
      const date = new Date(Date.now() - 60 * 60 * 24 * 7 * 1000);
      const iso = date.toISOString();
      // @ts-expect-error - calling private method for testing
      const result = el._formatTime(iso) as string;
      expect(result).to.equal(date.toLocaleDateString());
      // Defense in depth: confirm the function did not accidentally fall
      // through to one of the relative-time buckets.
      expect(result).to.not.match(/Just now|m ago|h ago|d ago/);
    });

    it('returns empty string for null', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);
      // @ts-expect-error - calling private method for testing
      expect(el._formatTime(null)).to.equal('');
    });
  });

  // The bug that motivated this work: a configured action references
  // sensors that are unavailable, so it can never fire — but the list
  // gave the user no hint. The badge below makes that obvious before
  // the user re-tests and burns time chasing a phantom integration bug.
  describe('stale-sensor warning badge', () => {
    function hassWithStates(states: Record<string, string>): HomeAssistant {
      return createMockHass({
        states: Object.fromEntries(
          Object.entries(states).map(([id, state]) => [id, { entity_id: id, state }]),
        ),
      });
    }

    // The incident this came from: an action fired ten times, its alarm was
    // rejected by Abode every time, and the list showed a healthy
    // trigger_count with no hint anything was wrong.
    describe('last-run outcome badge', () => {
      async function mountWithOutcome(last_outcome: AbodeAction['last_outcome']) {
        const hass = hassWithStates({ 'binary_sensor.front': 'off' });
        const el = await fixture<ActionsTab>(html`
          <abode-actions-tab .hass=${hass}></abode-actions-tab>
        `);
        await setState(el, {
          _actions: [
            createMockAction({
              name: 'Call the police',
              sensor_entity_ids: ['binary_sensor.front'],
              trigger_count: 10,
              last_outcome,
            }),
          ],
          _loading: false,
        } as Partial<ActionsTab>);
        return el;
      }

      it('shouts when the last run failed to raise the alarm', async () => {
        const el = await mountWithOutcome('failed');
        const badge = el.shadowRoot?.querySelector('.outcome-badge.failed');
        expect(badge, 'expected a failed outcome badge').to.exist;
        expect((badge?.textContent ?? '').trim()).to.contain('alarm failed');
        expect(badge?.getAttribute('title')).to.contain('did NOT fire');
      });

      it('distinguishes a partial failure', async () => {
        const el = await mountWithOutcome('partial');
        const badge = el.shadowRoot?.querySelector('.outcome-badge.failed');
        expect((badge?.textContent ?? '').trim()).to.contain('alarm partly failed');
      });

      it('labels notification-only actions', async () => {
        const el = await mountWithOutcome('none');
        const badge = el.shadowRoot?.querySelector('.outcome-badge.notification-only');
        expect((badge?.textContent ?? '').trim()).to.contain('notification only');
      });

      it('stays quiet when the alarm armed correctly', async () => {
        const el = await mountWithOutcome('armed');
        expect(el.shadowRoot?.querySelector('.outcome-badge')).to.equal(null);
      });

      it('stays quiet for actions that predate the field', async () => {
        const el = await mountWithOutcome(undefined);
        expect(el.shadowRoot?.querySelector('.outcome-badge')).to.equal(null);
      });
    });

    it("renders 'N of M sensors unavailable' when any referenced sensor is unavailable", async () => {
      const hass = hassWithStates({
        'binary_sensor.front': 'off',
        'binary_sensor.back': 'unavailable',
        // 'binary_sensor.side' deliberately omitted — a stored entity_id
        // missing from hass.states (renamed, deleted, integration
        // removed) is just as unactionable as `unavailable`, so it must
        // count the same way.
      });
      const actions = [
        createMockAction({
          id: 'home-test',
          name: 'Home Test',
          sensor_entity_ids: ['binary_sensor.front', 'binary_sensor.back', 'binary_sensor.side'],
        }),
      ];
      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);
      await setState(el, {
        _actions: actions,
        _loading: false,
      } as Partial<ActionsTab>);

      const warning = el.shadowRoot?.querySelector('.stale-warning');
      expect(warning, 'expected a .stale-warning element').to.exist;
      expect((warning?.textContent ?? '').trim()).to.match(/2 of 3 sensors\s+unavailable/i);
    });

    it('uses singular noun and title when the action references only one sensor', async () => {
      // Pluralization regression: previously rendered "1 of 1 sensors
      // unavailable" / "These sensors won't fire" regardless of count.
      const hass = hassWithStates({
        'binary_sensor.only_one': 'unavailable',
      });
      const actions = [
        createMockAction({
          sensor_entity_ids: ['binary_sensor.only_one'],
        }),
      ];
      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);
      await setState(el, {
        _actions: actions,
        _loading: false,
      } as Partial<ActionsTab>);

      const warning = el.shadowRoot?.querySelector('.stale-warning');
      expect((warning?.textContent ?? '').trim()).to.match(/1 of 1 sensor\s+unavailable/i);
      expect((warning?.textContent ?? '').toLowerCase()).to.not.include('sensors');
      // Title also flips to singular tense.
      const title = warning?.getAttribute('title') ?? '';
      expect(title).to.match(/This sensor won't fire .* until it comes back/i);
    });

    it('omits the badge when every referenced sensor is reachable', async () => {
      const hass = hassWithStates({
        'binary_sensor.front': 'off',
        'binary_sensor.back': 'on',
      });
      const actions = [
        createMockAction({
          id: 'home-test',
          sensor_entity_ids: ['binary_sensor.front', 'binary_sensor.back'],
        }),
      ];
      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);
      await setState(el, {
        _actions: actions,
        _loading: false,
      } as Partial<ActionsTab>);

      expect(el.shadowRoot?.querySelector('.stale-warning')).to.equal(null);
    });

    it('counts `unknown`-state sensors as unavailable too', async () => {
      // Same predicate as the editor: a sensor that's `unknown` cannot
      // produce a clean off → on transition, so the trigger pipeline
      // can't fire on it. Both surfaces must agree — otherwise a
      // `unknown` sensor would show a red pill in the editor but no
      // warning chip on the list, and the user would chase the wrong
      // bug again.
      const hass = createMockHass({
        states: {
          'binary_sensor.online': { entity_id: 'binary_sensor.online', state: 'off' },
          'binary_sensor.uninitialized': {
            entity_id: 'binary_sensor.uninitialized',
            state: 'unknown',
          },
        },
      });
      const actions = [
        createMockAction({
          sensor_entity_ids: ['binary_sensor.online', 'binary_sensor.uninitialized'],
        }),
      ];
      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hass}></abode-actions-tab>
      `);
      await setState(el, {
        _actions: actions,
        _loading: false,
      } as Partial<ActionsTab>);

      const warning = el.shadowRoot?.querySelector('.stale-warning');
      expect(warning, 'expected a .stale-warning for the `unknown` sensor').to.exist;
      expect((warning?.textContent ?? '').trim()).to.match(/1 of 2 sensors\s+unavailable/i);
    });

    it('updates the badge count when hass.states changes (live)', async () => {
      // Replicates the real-world recovery flow: user fixes one
      // sensor's battery, HA reassigns `hass`, the panel should
      // re-render with the new count without a refetch.
      const initialHass = hassWithStates({
        'binary_sensor.front': 'unavailable',
        'binary_sensor.back': 'unavailable',
      });
      const actions = [
        createMockAction({
          sensor_entity_ids: ['binary_sensor.front', 'binary_sensor.back'],
        }),
      ];
      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${initialHass}></abode-actions-tab>
      `);
      await setState(el, {
        _actions: actions,
        _loading: false,
      } as Partial<ActionsTab>);
      expect((el.shadowRoot?.querySelector('.stale-warning')?.textContent ?? '').trim()).to.match(
        /2 of 2 sensors\s+unavailable/i,
      );

      // HA replaces the entire hass object on state changes — mimic
      // that here rather than mutating in place.
      el.hass = hassWithStates({
        'binary_sensor.front': 'off',
        'binary_sensor.back': 'unavailable',
      });
      await elementUpdated(el);
      expect((el.shadowRoot?.querySelector('.stale-warning')?.textContent ?? '').trim()).to.match(
        /1 of 2 sensors\s+unavailable/i,
      );

      // Fully recovered — badge disappears.
      el.hass = hassWithStates({
        'binary_sensor.front': 'off',
        'binary_sensor.back': 'off',
      });
      await elementUpdated(el);
      expect(el.shadowRoot?.querySelector('.stale-warning')).to.equal(null);
    });
  });

  describe('copy action ID (debug-logging gated)', () => {
    function hassWithDebug(debugLogging: boolean): HomeAssistant {
      return createMockHass({
        callWS: (async (params: { type: string }) => {
          if (params.type === 'abode_security/actions/list') {
            return { actions: [createMockAction({ id: 'uuid-1', name: 'Front Door' })] };
          }
          if (params.type === 'abode_security/config/get') {
            return { debounce_seconds: 1.0, debug_logging: debugLogging };
          }
          if (params.type === 'abode_security/modes/list') return { modes: [] };
          return { success: true };
        }) as HomeAssistant['callWS'],
      });
    }

    it('is hidden when debug_logging is false', async () => {
      const el = await fixture<ActionsTab>(html`
        <abode-actions-tab .hass=${hassWithDebug(false)}></abode-actions-tab>
      `);
      // Wait for the initial load + Promise.all to settle.
      await aTimeout(0);
      await elementUpdated(el);

      const copyButton = el.shadowRoot?.querySelector<HTMLButtonElement>(
        'button[aria-label="Copy action ID"]',
      );
      expect(copyButton).to.equal(null);
    });

    it('is visible when debug_logging is true and copies on click', async () => {
      // Stub the clipboard so we don't depend on browser permissions or
      // the test runner's clipboard isolation.
      const writeText = (() => {
        const calls: string[] = [];
        const fn = ((v: string) => {
          calls.push(v);
          return Promise.resolve();
        }) as ((v: string) => Promise<void>) & { calls: string[] };
        fn.calls = calls;
        return fn;
      })();
      const originalClipboard = navigator.clipboard;
      Object.defineProperty(navigator, 'clipboard', {
        value: { writeText },
        configurable: true,
      });

      try {
        const el = await fixture<ActionsTab>(html`
          <abode-actions-tab .hass=${hassWithDebug(true)}></abode-actions-tab>
        `);
        await aTimeout(0);
        await elementUpdated(el);

        const copyButton = el.shadowRoot?.querySelector<HTMLButtonElement>(
          'button[aria-label="Copy action ID"]',
        );
        expect(copyButton, 'copy button should render').to.exist;

        copyButton!.click();
        await aTimeout(0);
        expect(writeText.calls).to.deep.equal(['uuid-1']);
      } finally {
        Object.defineProperty(navigator, 'clipboard', {
          value: originalClipboard,
          configurable: true,
        });
      }
    });
  });
});
