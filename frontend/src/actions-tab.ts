import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { repeat } from 'lit/directives/repeat.js';
import type { HomeAssistant, AbodeAction } from './types';
import { getEntityState, isUnavailableState } from './types';
import {
  fetchActions,
  fetchIntegrationConfig,
  updateAction,
  deleteAction,
  testAction,
} from './api';
import './action-editor';
import './abode-modal';

/**
 * Actions tab — lists configured Abode actions and orchestrates the
 * create/edit/delete/test/toggle flows. The `<abode-action-editor>` is
 * opened in-place when the user clicks Add or Edit; delete and test
 * each go through an `<abode-modal variant="alertdialog">` confirm.
 *
 * @prop {HomeAssistant} hass - Required.
 */
@customElement('abode-actions-tab')
export class ActionsTab extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @state() private _actions: AbodeAction[] = [];
  @state() private _loading = true;
  @state() private _error: string | null = null;
  @state() private _editingAction: AbodeAction | null = null;
  @state() private _showEditor = false;
  @state() private _confirm: { kind: 'delete' | 'test'; action: AbodeAction } | null = null;
  @state() private _togglingIds: Set<string> = new Set();
  @state() private _operationError: string | null = null;
  // Mirrors the `debug_logging` integration option (read-only). When true, the
  // actions list shows a per-row "copy action ID" button so power users can
  // grab a UUID for use with `abode_security.fire_test_notification` or for
  // filtering automations on `action_id`. We fail closed: any fetch error or
  // missing field hides the affordance, since this is purely a power-user
  // shortcut and false-true would surface a feature the user didn't opt into.
  @state() private _debugLogging = false;
  @state() private _copiedId: string | null = null;

  // Aborted on disconnect so a late-resolving fetch can't write state to a
  // detached element (panel tab switches destroy the inactive tab — closes #29).
  // See action-editor.ts for full rationale; this version omits the Retry path.
  private _abort: AbortController | null = null;
  private _copyResetTimeout: ReturnType<typeof setTimeout> | null = null;

  static styles = css`
    :host {
      display: block;
    }

    .actions-header {
      display: flex;
      justify-content: flex-end;
      margin-bottom: 16px;
    }

    .add-button {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      background: var(--primary-color, #03a9f4);
      color: white;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.2s;
    }

    .add-button:hover {
      background: var(--primary-color-dark, #0288d1);
    }

    .add-button:focus-visible {
      outline: 2px solid var(--primary-color);
      outline-offset: 2px;
    }

    .add-button ha-icon {
      --mdc-icon-size: 18px;
    }

    .actions-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .action-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px;
      background: var(--card-background-color, #fff);
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .action-row.disabled {
      opacity: 0.6;
    }

    .action-info {
      flex: 1;
      min-width: 0;
    }

    .action-name {
      font-size: 16px;
      font-weight: 500;
      color: var(--primary-text-color);
      margin-bottom: 4px;
    }

    .action-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }

    .modes-list {
      display: flex;
      gap: 4px;
    }

    .mode-chip {
      padding: 2px 8px;
      background: var(--primary-color, #03a9f4);
      color: white;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 500;
      text-transform: uppercase;
    }

    /* Warning chip surfaced when a saved action references an entity
     * that is currently unavailable in hass.states — the trap that
     * caused the "Home Test" bug: UI looked fine but no event could
     * ever fire because the chosen sensors were offline. */
    .stale-warning {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      color: var(--warning-color, #ff9800);
    }

    .stale-warning ha-icon {
      --mdc-icon-size: 16px;
    }

    .outcome-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
    }

    .outcome-badge ha-icon {
      --mdc-icon-size: 16px;
    }

    /* A security action that promised an alarm and didn't deliver is the
       loudest state this list can show — error red, not warning amber. */
    .outcome-badge.failed {
      color: var(--error-color, #db4437);
      font-weight: 500;
    }

    .outcome-badge.notification-only {
      color: var(--secondary-text-color, #727272);
    }

    .action-controls {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .icon-button {
      width: 36px;
      height: 36px;
      padding: 0;
      border: none;
      background: transparent;
      border-radius: 50%;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--secondary-text-color);
      transition:
        background 0.2s,
        color 0.2s;
    }

    .icon-button:hover {
      background: var(--secondary-background-color, #f5f5f5);
      color: var(--primary-text-color);
    }

    .icon-button:focus-visible {
      outline: 2px solid var(--primary-color);
      outline-offset: 2px;
    }

    .icon-button.delete:hover {
      color: var(--error-color, #f44336);
    }

    .icon-button ha-icon {
      --mdc-icon-size: 20px;
    }

    .empty-state {
      text-align: center;
      padding: 48px;
      color: var(--secondary-text-color);
    }

    .empty-state ha-icon {
      --mdc-icon-size: 48px;
      margin-bottom: 16px;
      opacity: 0.5;
    }

    .empty-state p {
      margin: 0 0 16px 0;
      font-size: 16px;
    }

    .recent-triggers {
      margin-top: 32px;
    }

    .recent-triggers h3 {
      font-size: 16px;
      font-weight: 500;
      color: var(--primary-text-color);
      margin: 0 0 12px 0;
    }

    .trigger-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .trigger-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      background: var(--card-background-color, #fff);
      border-radius: 8px;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    }

    .trigger-name {
      font-size: 14px;
      color: var(--primary-text-color);
    }

    .trigger-time {
      font-size: 12px;
      color: var(--secondary-text-color);
    }

    .loading {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 48px;
      color: var(--secondary-text-color);
    }

    .error {
      padding: 16px;
      background-color: var(--error-color, #f44336);
      color: white;
      border-radius: 4px;
    }

    .operation-error {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      background-color: var(--error-color, #f44336);
      color: white;
      border-radius: 4px;
      margin-bottom: 16px;
    }

    .dismiss-error {
      background: transparent;
      border: none;
      color: white;
      font-size: 20px;
      cursor: pointer;
      padding: 0 4px;
      opacity: 0.8;
    }

    .dismiss-error:hover {
      opacity: 1;
    }

    /* Dialog button styles — applied to <button slot="footer"> inside <abode-modal>. */
    .dialog-button {
      padding: 8px 16px;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.2s;
    }

    .dialog-button.cancel {
      background: transparent;
      color: var(--secondary-text-color);
    }

    .dialog-button.cancel:hover {
      background: var(--secondary-background-color);
    }

    .dialog-button.danger {
      background: var(--error-color, #f44336);
      color: white;
    }

    .dialog-button.danger:hover {
      background: #d32f2f;
    }

    .dialog-button.primary {
      background: var(--primary-color, #03a9f4);
      color: white;
    }

    .dialog-button.primary:hover {
      background: var(--primary-color-dark, #0288d1);
    }

    /* Toggle switch */
    .toggle-switch {
      position: relative;
      width: 40px;
      height: 20px;
    }

    .toggle-switch input {
      opacity: 0;
      width: 0;
      height: 0;
    }

    .toggle-slider {
      position: absolute;
      cursor: pointer;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: #ccc;
      transition: 0.3s;
      border-radius: 20px;
    }

    .toggle-slider:before {
      position: absolute;
      content: '';
      height: 16px;
      width: 16px;
      left: 2px;
      bottom: 2px;
      background-color: white;
      transition: 0.3s;
      border-radius: 50%;
    }

    .toggle-switch input:checked + .toggle-slider {
      background-color: var(--primary-color, #03a9f4);
    }

    .toggle-switch input:checked + .toggle-slider:before {
      transform: translateX(20px);
    }

    .toggle-switch input:disabled + .toggle-slider {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .toggle-switch input:focus-visible + .toggle-slider {
      outline: 2px solid var(--primary-color);
      outline-offset: 2px;
    }
  `;

  async connectedCallback() {
    super.connectedCallback();
    await this._loadData();
  }

  disconnectedCallback() {
    this._abort?.abort();
    this._abort = null;
    if (this._copyResetTimeout !== null) {
      clearTimeout(this._copyResetTimeout);
      this._copyResetTimeout = null;
    }
    super.disconnectedCallback();
  }

  private async _loadData() {
    this._abort?.abort();
    const controller = new AbortController();
    this._abort = controller;
    const { signal } = controller;

    this._loading = true;
    this._error = null;

    try {
      const actions = await fetchActions(this.hass);
      if (signal.aborted) return;
      this._actions = actions;
      // Config fetch is best-effort and fire-and-forget: a failure here
      // (or its later arrival) must not block the actions list from
      // rendering. Default `_debugLogging = false` keeps the copy-ID
      // affordance hidden until the fetch confirms opt-in. Kept off the
      // main await chain so existing tests' microtask ordering — which
      // sets `_actions` after `await fixture(...)` — still wins.
      void fetchIntegrationConfig(this.hass)
        .then((config) => {
          if (signal.aborted) return;
          this._debugLogging = config.debug_logging === true;
        })
        .catch(() => {
          /* leave _debugLogging at its safe default */
        });
    } catch (err) {
      if (signal.aborted) return;
      this._error = err instanceof Error ? err.message : 'Failed to load actions';
    } finally {
      if (!signal.aborted) this._loading = false;
    }
  }

  private async _copyActionId(action: AbodeAction) {
    try {
      await navigator.clipboard.writeText(action.id);
      this._copiedId = action.id;
      if (this._copyResetTimeout !== null) clearTimeout(this._copyResetTimeout);
      this._copyResetTimeout = setTimeout(() => {
        this._copyResetTimeout = null;
        if (this._copiedId === action.id) this._copiedId = null;
      }, 1500);
    } catch (err) {
      console.error('Failed to copy action ID:', err);
      this._operationError = 'Failed to copy action ID';
    }
  }

  private _getRecentTriggers(): AbodeAction[] {
    return this._actions
      .filter((a) => a.last_triggered)
      .sort((a, b) => new Date(b.last_triggered!).getTime() - new Date(a.last_triggered!).getTime())
      .slice(0, 5);
  }

  private _formatTime(isoString: string | null): string {
    if (!isoString) return '';
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  }

  private _addAction() {
    this._editingAction = null;
    this._showEditor = true;
  }

  private _editAction(action: AbodeAction) {
    this._editingAction = action;
    this._showEditor = true;
  }

  private async _toggleAction(action: AbodeAction) {
    const id = action.id;
    this._togglingIds = new Set([...this._togglingIds, id]);
    this._operationError = null;

    try {
      const updated = await updateAction(this.hass, id, { enabled: !action.enabled });
      this._actions = this._actions.map((a) => (a.id === id ? updated : a));
    } catch (err) {
      console.error('Failed to toggle action:', err);
      this._operationError = `Failed to ${action.enabled ? 'disable' : 'enable'} action`;
    } finally {
      this._togglingIds = new Set([...this._togglingIds].filter((i) => i !== id));
    }
  }

  private _requestDelete(action: AbodeAction) {
    this._confirm = { kind: 'delete', action };
  }

  private async _confirmDelete() {
    if (this._confirm?.kind !== 'delete') return;
    const { action } = this._confirm;
    this._confirm = null;
    this._operationError = null;

    try {
      await deleteAction(this.hass, action.id);
      this._actions = this._actions.filter((a) => a.id !== action.id);
    } catch (err) {
      console.error('Failed to delete action:', err);
      this._operationError = 'Failed to delete action';
    }
  }

  private _requestTest(action: AbodeAction) {
    this._confirm = { kind: 'test', action };
  }

  private async _confirmTest() {
    if (this._confirm?.kind !== 'test') return;
    const { action } = this._confirm;
    this._confirm = null;
    this._operationError = null;

    try {
      await testAction(this.hass, action.id);
    } catch (err) {
      console.error('Failed to test action:', err);
      // Surface the backend's reason rather than a generic string. A test
      // that raises no alarm must say so — "Failed to test action" reads like
      // a UI glitch, not "your alarm did not fire".
      const message = (err as { message?: string } | undefined)?.message;
      this._operationError = message
        ? `Failed to test action: ${message}`
        : 'Failed to test action';
    }
  }

  private _closeEditor() {
    this._showEditor = false;
    this._editingAction = null;
  }

  private async _handleSave() {
    this._closeEditor();
    await this._loadData();
  }

  render() {
    if (this._loading) {
      return html`<div class="loading">Loading actions...</div>`;
    }

    if (this._error) {
      return html`<div class="error" role="alert">${this._error}</div>`;
    }

    const recentTriggers = this._getRecentTriggers();

    return html`
      ${this._operationError
        ? html`
            <div class="operation-error" role="alert">
              ${this._operationError}
              <button
                class="dismiss-error"
                @click=${() => (this._operationError = null)}
                aria-label="Dismiss error"
              >
                ×
              </button>
            </div>
          `
        : ''}

      <div class="actions-header">
        <button class="add-button" @click=${this._addAction} aria-label="Add new action">
          <ha-icon icon="mdi:plus"></ha-icon>
          Add Action
        </button>
      </div>

      ${this._actions.length === 0
        ? html`
            <div class="empty-state">
              <ha-icon icon="mdi:bell-off-outline"></ha-icon>
              <p>No actions configured</p>
              <button class="add-button" @click=${this._addAction}>
                <ha-icon icon="mdi:plus"></ha-icon>
                Create your first action
              </button>
            </div>
          `
        : html`
            <div class="actions-list" role="list">
              ${repeat(
                this._actions,
                (action) => action.id,
                (action) => this._renderActionRow(action),
              )}
            </div>
          `}

      <div class="recent-triggers">
        <h3>Recent Triggers</h3>
        ${recentTriggers.length === 0
          ? html`<div class="empty-state" style="padding: 24px;">No recent triggers</div>`
          : html`
              <div class="trigger-list">
                ${recentTriggers.map(
                  (action) => html`
                    <div class="trigger-item">
                      <span class="trigger-name">${action.name}</span>
                      <span class="trigger-time">${this._formatTime(action.last_triggered)}</span>
                    </div>
                  `,
                )}
              </div>
            `}
      </div>

      ${this._showEditor
        ? html`
            <abode-action-editor
              .hass=${this.hass}
              .action=${this._editingAction}
              @save=${this._handleSave}
              @cancel=${this._closeEditor}
            ></abode-action-editor>
          `
        : ''}
      ${this._confirm?.kind === 'delete' ? this._renderDeleteDialog() : ''}
      ${this._confirm?.kind === 'test' ? this._renderTestDialog() : ''}
    `;
  }

  // The outcome of the last execution. Without this, an action whose alarm
  // failed on every one of its triggers rendered identically to one that
  // worked — the failure existed only as a log line.
  private _renderOutcomeBadge(action: AbodeAction) {
    if (!action.last_outcome || action.last_outcome === 'armed') return '';

    if (action.last_outcome === 'none') {
      return html`
        <span
          class="outcome-badge notification-only"
          title="This action only sends a notification. It does not raise an alarm or contact monitoring."
        >
          <ha-icon icon="mdi:bell-outline" aria-hidden="true"></ha-icon>
          notification only
        </span>
      `;
    }

    const partial = action.last_outcome === 'partial';
    return html`
      <span
        class="outcome-badge failed"
        title=${partial
          ? 'Some alarms failed to arm the last time this action fired. Monitoring may not have been contacted.'
          : 'The alarm did NOT fire the last time this action ran. Monitoring was not contacted. Check the alarm assigned to this action.'}
      >
        <ha-icon icon="mdi:alert-octagon" aria-hidden="true"></ha-icon>
        ${partial ? 'alarm partly failed' : 'alarm failed'}
      </span>
    `;
  }

  private _renderActionRow(action: AbodeAction) {
    const isToggling = this._togglingIds.has(action.id);
    // A stored sensor entity_id that isn't in hass.states (renamed, deleted,
    // integration removed) and one that is `unavailable`/`unknown` are
    // equally unactionable — the backend trigger filter rejects anything
    // that isn't a clean off → on. `getEntityState`'s default fallback is
    // `'unavailable'`, so a missing entity falls into the same bucket.
    const unavailableCount = action.sensor_entity_ids.filter((id) =>
      isUnavailableState(getEntityState(this.hass, id)),
    ).length;
    const totalCount = action.sensor_entity_ids.length;

    return html`
      <div class="action-row ${action.enabled ? '' : 'disabled'}" role="listitem">
        <div class="action-info">
          <div class="action-name">${action.name}</div>
          <div class="action-meta">
            <div class="modes-list">
              ${action.modes.map((mode) => html`<span class="mode-chip">${mode}</span>`)}
            </div>
            ${unavailableCount > 0
              ? html`
                  <span
                    class="stale-warning"
                    title=${unavailableCount === 1
                      ? "This sensor won't fire this action until it comes back online."
                      : "These sensors won't fire this action until they come back online."}
                  >
                    <ha-icon icon="mdi:alert" aria-hidden="true"></ha-icon>
                    ${unavailableCount} of ${totalCount} ${totalCount === 1 ? 'sensor' : 'sensors'}
                    unavailable
                  </span>
                `
              : ''}
            ${this._renderOutcomeBadge(action)}
          </div>
        </div>
        <div class="action-controls">
          <label class="toggle-switch">
            <input
              type="checkbox"
              .checked=${action.enabled}
              .disabled=${isToggling}
              @change=${() => this._toggleAction(action)}
              aria-label="${action.enabled ? 'Disable' : 'Enable'} action"
            />
            <span class="toggle-slider"></span>
          </label>
          ${this._debugLogging
            ? html`
                <button
                  class="icon-button"
                  @click=${() => this._copyActionId(action)}
                  title=${this._copiedId === action.id
                    ? 'Copied!'
                    : `Copy action ID (${action.id})`}
                  aria-label="Copy action ID"
                >
                  <ha-icon
                    icon=${this._copiedId === action.id ? 'mdi:check' : 'mdi:content-copy'}
                  ></ha-icon>
                </button>
              `
            : ''}
          <button
            class="icon-button"
            @click=${() => this._requestTest(action)}
            title="Test"
            aria-label="Test action"
          >
            <ha-icon icon="mdi:play"></ha-icon>
          </button>
          <button
            class="icon-button"
            @click=${() => this._editAction(action)}
            title="Edit"
            aria-label="Edit action"
          >
            <ha-icon icon="mdi:pencil"></ha-icon>
          </button>
          <button
            class="icon-button delete"
            @click=${() => this._requestDelete(action)}
            title="Delete"
            aria-label="Delete action"
          >
            <ha-icon icon="mdi:delete"></ha-icon>
          </button>
        </div>
      </div>
    `;
  }

  private _renderDeleteDialog() {
    return html`
      <abode-modal
        heading="Delete Action"
        variant="alertdialog"
        @dismiss=${() => (this._confirm = null)}
      >
        <p>Delete action "${this._confirm?.action.name}"? This cannot be undone.</p>
        <button slot="footer" class="dialog-button cancel" @click=${() => (this._confirm = null)}>
          Cancel
        </button>
        <button slot="footer" class="dialog-button danger" @click=${this._confirmDelete}>
          Delete
        </button>
      </abode-modal>
    `;
  }

  private _renderTestDialog() {
    return html`
      <abode-modal
        heading="Test Action"
        variant="alertdialog"
        @dismiss=${() => (this._confirm = null)}
      >
        <p>
          This will trigger real alarms. Are you sure you want to test
          "${this._confirm?.action.name}"?
        </p>
        <button slot="footer" class="dialog-button cancel" @click=${() => (this._confirm = null)}>
          Cancel
        </button>
        <button slot="footer" class="dialog-button primary" @click=${this._confirmTest}>
          Test
        </button>
      </abode-modal>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'abode-actions-tab': ActionsTab;
  }
}
