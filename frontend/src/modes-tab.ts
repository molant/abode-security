import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { HomeAssistant, AbodeMode, AbodeAction, Mode } from './types';
import { fetchModes, fetchActions, setMode } from './api';
import './abode-modal';

/**
 * Modes tab — displays the three Abode arming modes (standby/home/away)
 * with their action counts and the active flag, and lets the user
 * switch modes from the panel via a confirm dialog (#1). Switching
 * delegates to the `abode_security/modes/set` WS endpoint, which in
 * turn calls the standard `alarm_control_panel` arm/disarm services.
 *
 * @prop {HomeAssistant} hass - Required.
 */
@customElement('abode-modes-tab')
export class ModesTab extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @state() private _modes: AbodeMode[] = [];
  @state() private _actions: AbodeAction[] = [];
  @state() private _loading = true;
  @state() private _error: string | null = null;

  // Mode-switching state (#1):
  // - _confirmMode holds the target mode while the confirm dialog is open.
  // - _settingModeId is set during the in-flight WS call so the UI can show
  //   a busy state and prevent re-entry.
  // - _setError surfaces a failed switch as a dismissible banner.
  @state() private _confirmMode: AbodeMode | null = null;
  @state() private _settingModeId: Mode | null = null;
  @state() private _setError: string | null = null;

  // Aborted on disconnect so a late-resolving fetch can't write state to a
  // detached element (panel tab switches destroy the inactive tab — closes #29).
  // See action-editor.ts for full rationale; this version omits the Retry path.
  private _abort: AbortController | null = null;

  static styles = css`
    :host {
      display: block;
    }

    .modes-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
    }

    .mode-card {
      background: var(--card-background-color, #fff);
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
      border: 2px solid transparent;
      transition: border-color 0.2s, box-shadow 0.2s;
    }

    .mode-card.active {
      border-color: var(--primary-color, #03a9f4);
      box-shadow: 0 4px 12px rgba(3, 169, 244, 0.2);
    }

    .mode-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
    }

    .mode-icon {
      width: 48px;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--primary-color, #03a9f4);
      color: white;
      border-radius: 50%;
    }

    .mode-icon ha-icon {
      --mdc-icon-size: 24px;
    }

    .mode-info h3 {
      margin: 0;
      font-size: 18px;
      font-weight: 500;
      color: var(--primary-text-color);
      text-transform: capitalize;
    }

    .badges {
      display: flex;
      gap: 8px;
      margin-top: 4px;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      padding: 2px 8px;
      background: var(--secondary-background-color, #f5f5f5);
      border-radius: 12px;
      font-size: 12px;
      color: var(--secondary-text-color);
    }

    .badge.active {
      background: var(--primary-color, #03a9f4);
      color: white;
    }

    .action-list {
      margin: 16px 0 0 0;
      padding: 0;
      list-style: none;
    }

    .action-list li {
      padding: 8px 0;
      border-bottom: 1px solid var(--divider-color, #e0e0e0);
      font-size: 14px;
      color: var(--primary-text-color);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .action-list li:last-child {
      border-bottom: none;
    }

    .action-list li ha-icon {
      --mdc-icon-size: 16px;
      color: var(--secondary-text-color);
    }

    .empty-actions {
      padding: 12px 0;
      color: var(--secondary-text-color);
      font-size: 14px;
      font-style: italic;
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

    .switch-button {
      width: 100%;
      margin-top: 16px;
      padding: 10px 16px;
      border: 1px solid var(--primary-color, #03a9f4);
      border-radius: 4px;
      background: transparent;
      color: var(--primary-color, #03a9f4);
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.2s, color 0.2s;
    }

    .switch-button:hover:not(:disabled) {
      background: var(--primary-color, #03a9f4);
      color: white;
    }

    .switch-button:focus-visible {
      outline: 2px solid var(--primary-color, #03a9f4);
      outline-offset: 2px;
    }

    .switch-button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .current-mode-label {
      margin-top: 16px;
      padding: 10px 16px;
      text-align: center;
      font-size: 13px;
      color: var(--secondary-text-color);
      font-style: italic;
    }

    /* Confirm dialog button styles — applied to <button slot="footer"> inside <abode-modal>. */
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

    .dialog-button.primary {
      background: var(--primary-color, #03a9f4);
      color: white;
    }

    .dialog-button.primary:hover {
      background: var(--primary-color-dark, #0288d1);
    }
  `;

  async connectedCallback() {
    super.connectedCallback();
    await this._loadData();
  }

  disconnectedCallback() {
    this._abort?.abort();
    this._abort = null;
    super.disconnectedCallback();
  }

  private async _loadData(options: { silent?: boolean } = {}) {
    this._abort?.abort();
    const controller = new AbortController();
    this._abort = controller;
    const { signal } = controller;

    // `silent` keeps `_loading` untouched so an in-place refresh doesn't
    // flash the full-page "Loading modes..." spinner over the visible grid.
    // The initial connectedCallback load is loud (default); post-switch
    // refresh is silent.
    if (!options.silent) this._loading = true;
    this._error = null;

    try {
      const [modes, actions] = await Promise.all([
        fetchModes(this.hass),
        fetchActions(this.hass),
      ]);
      if (signal.aborted) return;
      this._modes = modes;
      this._actions = actions;
    } catch (err) {
      if (signal.aborted) return;
      this._error = err instanceof Error ? err.message : 'Failed to load data';
    } finally {
      if (!signal.aborted && !options.silent) this._loading = false;
    }
  }

  private _getActionsForMode(modeId: Mode): AbodeAction[] {
    return this._actions.filter(
      (action) => action.enabled && action.modes.includes(modeId)
    );
  }

  private _requestSwitch(mode: AbodeMode) {
    // No-op for already-active mode (the UI suppresses the button anyway,
    // this is a defense-in-depth check in case a programmatic caller fires).
    if (mode.active || this._settingModeId !== null) return;
    // Clear any stale error from a prior failed attempt — opening a fresh
    // confirm dialog implies the user has acknowledged the previous one.
    this._setError = null;
    this._confirmMode = mode;
  }

  private async _confirmSwitch() {
    if (!this._confirmMode) return;
    const target = this._confirmMode;
    this._confirmMode = null;
    this._settingModeId = target.id;
    this._setError = null;
    try {
      await setMode(this.hass, target.id);
    } catch (err) {
      // Match actions-tab convention: log the raw exception for diagnostics,
      // surface a fixed user-facing label so backend internals don't leak.
      console.error('Failed to set mode:', err);
      this._setError = 'Failed to change mode';
      this._settingModeId = null;
      return;
    }
    // Switch succeeded — refresh so the active flag flips. Pass
    // `silent: true` so the grid stays visible (with its "Switching…"
    // pending label on the targeted card) instead of flashing
    // "Loading modes..." over the full tab during the refresh.
    //
    // _loadData catches its own exception and writes to `this._error`,
    // which would trigger the full-page error branch in render() and wipe
    // the successful-switch UX. Detect that case and re-route the message
    // through the dismissible banner instead.
    await this._loadData({ silent: true });
    if (this._error) {
      this._setError = `Mode changed; refresh failed: ${this._error}`;
      this._error = null;
    }
    this._settingModeId = null;
  }

  render() {
    if (this._loading) {
      return html`<div class="loading">Loading modes...</div>`;
    }

    if (this._error) {
      return html`<div class="error" role="alert">${this._error}</div>`;
    }

    return html`
      ${this._setError
        ? html`
            <div class="operation-error" role="alert">
              ${this._setError}
              <button
                class="dismiss-error"
                @click=${() => (this._setError = null)}
                aria-label="Dismiss error"
              >
                ×
              </button>
            </div>
          `
        : ''}

      <div class="modes-grid">
        ${this._modes.map((mode) => this._renderModeCard(mode))}
      </div>

      ${this._confirmMode ? this._renderConfirmDialog(this._confirmMode) : ''}
    `;
  }

  private _renderConfirmDialog(target: AbodeMode) {
    return html`
      <abode-modal
        heading="Switch mode?"
        variant="alertdialog"
        @dismiss=${() => (this._confirmMode = null)}
      >
        <p>
          Switch the system to <strong>${target.name}</strong>? This changes
          the live arming state and runs any actions configured for this mode.
        </p>
        <button
          slot="footer"
          class="dialog-button cancel"
          @click=${() => (this._confirmMode = null)}
        >
          Cancel
        </button>
        <button
          slot="footer"
          class="dialog-button primary"
          @click=${this._confirmSwitch}
        >
          Switch
        </button>
      </abode-modal>
    `;
  }

  private _renderModeCard(mode: AbodeMode) {
    const actionsForMode = this._getActionsForMode(mode.id);
    const isPending = this._settingModeId === mode.id;
    const anySwitchPending = this._settingModeId !== null;

    return html`
      <div class="mode-card ${mode.active ? 'active' : ''}">
        <div class="mode-header">
          <div class="mode-icon">
            <ha-icon icon=${mode.icon}></ha-icon>
          </div>
          <div class="mode-info">
            <h3>${mode.name}</h3>
            <div class="badges">
              <span class="badge">${mode.action_count} ${mode.action_count === 1 ? 'action' : 'actions'}</span>
              ${mode.active ? html`<span class="badge active">Active</span>` : ''}
            </div>
          </div>
        </div>

        ${actionsForMode.length > 0
          ? html`
              <ul class="action-list" aria-label="Actions for ${mode.name} mode">
                ${actionsForMode.map(
                  (action) => html`
                    <li>
                      <ha-icon icon="mdi:bell-ring"></ha-icon>
                      ${action.name}
                    </li>
                  `
                )}
              </ul>
            `
          : html`<div class="empty-actions">No actions configured</div>`}

        ${mode.active
          ? html`<div class="current-mode-label">Current mode</div>`
          : html`
              <button
                class="switch-button"
                ?disabled=${anySwitchPending}
                aria-label=${`Switch to ${mode.name} mode`}
                @click=${() => this._requestSwitch(mode)}
              >
                ${isPending ? 'Switching…' : `Switch to ${mode.name}`}
              </button>
            `}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'abode-modes-tab': ModesTab;
  }
}
