/**
 * Tests for the ActionsTab component.
 *
 * Note: These tests focus on rendering behavior with pre-loaded data.
 * API integration is tested via E2E and integration tests.
 */

import { expect, fixture, html } from '@open-wc/testing';

import '../actions-tab.js';
import type { ActionsTab } from '../actions-tab.js';
import { createMockHass, createMockAction, elementUpdated } from './test-helpers.js';

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
      const actions = [
        createMockAction({ modes: ['home', 'away'] }),
      ];

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
      const actions = [
        createMockAction({ enabled: false }),
      ];

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

      const dialog = el.shadowRoot?.querySelector('.dialog');
      expect(dialog).to.exist;
      expect(dialog?.textContent).to.include('Delete Action');
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

      const testButton = el.shadowRoot?.querySelector('button[aria-label="Test action"]') as HTMLButtonElement;
      testButton?.click();

      await elementUpdated(el);

      const dialog = el.shadowRoot?.querySelector('.dialog');
      expect(dialog).to.exist;
      expect(dialog?.textContent).to.include('trigger real alarms');
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

    it('delete dialog has proper ARIA attributes', async () => {
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

      const dialog = el.shadowRoot?.querySelector('.dialog');
      expect(dialog?.getAttribute('role')).to.equal('alertdialog');
      expect(dialog?.getAttribute('aria-modal')).to.equal('true');
    });
  });
});
