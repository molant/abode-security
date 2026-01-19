import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { HomeAssistant, AbodeAction } from './types';
import { fetchActions, updateAction, deleteAction, testAction } from './api';
import './action-editor';

@customElement('abode-actions-tab')
export class ActionsTab extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @state() private _actions: AbodeAction[] = [];
  @state() private _loading = true;
  @state() private _error: string | null = null;
  @state() private _editingAction: AbodeAction | null = null;
  @state() private _showEditor = false;
  @state() private _showDeleteConfirm = false;
  @state() private _showTestConfirm = false;
  @state() private _pendingAction: AbodeAction | null = null;
  @state() private _togglingIds: Set<string> = new Set();
  @state() private _operationError: string | null = null;

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

    .trigger-info {
      font-size: 12px;
      color: var(--secondary-text-color);
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
      transition: background 0.2s, color 0.2s;
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

    /* Dialog styles */
    .dialog-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }

    .dialog {
      background: var(--card-background-color, #fff);
      border-radius: 8px;
      padding: 24px;
      max-width: 400px;
      width: 90%;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }

    .dialog h3 {
      margin: 0 0 16px 0;
      font-size: 18px;
      font-weight: 500;
      color: var(--primary-text-color);
    }

    .dialog p {
      margin: 0 0 24px 0;
      color: var(--secondary-text-color);
      line-height: 1.5;
    }

    .dialog-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
    }

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

  private async _loadData() {
    this._loading = true;
    this._error = null;

    try {
      this._actions = await fetchActions(this.hass);
    } catch (err) {
      this._error = err instanceof Error ? err.message : 'Failed to load actions';
    } finally {
      this._loading = false;
    }
  }

  private _getRecentTriggers(): AbodeAction[] {
    return this._actions
      .filter((a) => a.last_triggered)
      .sort(
        (a, b) =>
          new Date(b.last_triggered!).getTime() - new Date(a.last_triggered!).getTime()
      )
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
    this._pendingAction = action;
    this._showDeleteConfirm = true;
  }

  private async _confirmDelete() {
    if (!this._pendingAction) return;
    this._operationError = null;

    try {
      await deleteAction(this.hass, this._pendingAction.id);
      this._actions = this._actions.filter((a) => a.id !== this._pendingAction!.id);
    } catch (err) {
      console.error('Failed to delete action:', err);
      this._operationError = 'Failed to delete action';
    } finally {
      this._showDeleteConfirm = false;
      this._pendingAction = null;
    }
  }

  private _requestTest(action: AbodeAction) {
    this._pendingAction = action;
    this._showTestConfirm = true;
  }

  private async _confirmTest() {
    if (!this._pendingAction) return;
    this._operationError = null;

    try {
      await testAction(this.hass, this._pendingAction.id);
    } catch (err) {
      console.error('Failed to test action:', err);
      this._operationError = 'Failed to test action';
    } finally {
      this._showTestConfirm = false;
      this._pendingAction = null;
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
        <button
          class="add-button"
          @click=${this._addAction}
          aria-label="Add new action"
        >
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
              ${this._actions.map((action) => this._renderActionRow(action))}
            </div>
          `}

      <div class="recent-triggers">
        <h3>Recent Triggers</h3>
        ${recentTriggers.length === 0
          ? html`<div class="empty-state" style="padding: 24px;">
              No recent triggers
            </div>`
          : html`
              <div class="trigger-list">
                ${recentTriggers.map(
                  (action) => html`
                    <div class="trigger-item">
                      <span class="trigger-name">${action.name}</span>
                      <span class="trigger-time"
                        >${this._formatTime(action.last_triggered)}</span
                      >
                    </div>
                  `
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
      ${this._showDeleteConfirm ? this._renderDeleteDialog() : ''}
      ${this._showTestConfirm ? this._renderTestDialog() : ''}
    `;
  }

  private _renderActionRow(action: AbodeAction) {
    const isToggling = this._togglingIds.has(action.id);

    return html`
      <div class="action-row ${action.enabled ? '' : 'disabled'}" role="listitem">
        <div class="action-info">
          <div class="action-name">${action.name}</div>
          <div class="action-meta">
            <div class="modes-list">
              ${action.modes.map(
                (mode) => html`<span class="mode-chip">${mode}</span>`
              )}
            </div>
            ${action.trigger_count > 0
              ? html`<span class="trigger-info"
                  >${action.trigger_count} triggers</span
                >`
              : ''}
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
      <div
        class="dialog-overlay"
        @click=${(e: Event) => {
          if (e.target === e.currentTarget) this._showDeleteConfirm = false;
        }}
        @keydown=${(e: KeyboardEvent) => {
          if (e.key === 'Escape') this._showDeleteConfirm = false;
        }}
      >
        <div class="dialog" role="alertdialog" aria-modal="true" aria-labelledby="delete-title">
          <h3 id="delete-title">Delete Action</h3>
          <p>
            Delete action "${this._pendingAction?.name}"? This cannot be undone.
          </p>
          <div class="dialog-actions">
            <button
              class="dialog-button cancel"
              @click=${() => (this._showDeleteConfirm = false)}
            >
              Cancel
            </button>
            <button class="dialog-button danger" @click=${this._confirmDelete}>
              Delete
            </button>
          </div>
        </div>
      </div>
    `;
  }

  private _renderTestDialog() {
    return html`
      <div
        class="dialog-overlay"
        @click=${(e: Event) => {
          if (e.target === e.currentTarget) this._showTestConfirm = false;
        }}
        @keydown=${(e: KeyboardEvent) => {
          if (e.key === 'Escape') this._showTestConfirm = false;
        }}
      >
        <div class="dialog" role="alertdialog" aria-modal="true" aria-labelledby="test-title">
          <h3 id="test-title">Test Action</h3>
          <p>
            This will trigger real alarms. Are you sure you want to test
            "${this._pendingAction?.name}"?
          </p>
          <div class="dialog-actions">
            <button
              class="dialog-button cancel"
              @click=${() => (this._showTestConfirm = false)}
            >
              Cancel
            </button>
            <button class="dialog-button primary" @click=${this._confirmTest}>
              Test
            </button>
          </div>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'abode-actions-tab': ActionsTab;
  }
}
