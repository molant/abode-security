import { LitElement, html, css, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { PropertyValues } from 'lit';
import type { HomeAssistant, AbodeMode, AbodeAction, Mode } from './types';
import { fetchModes, fetchActions, setMode } from './api';
import './abode-modal';
import './schedules-section';

// Mirrors backend STATE_TO_MODE (websocket_api.py). Replicated here so the
// frontend can derive the active mode from `hass.states[panel].state` at
// render time and stay live-reactive — the cached snapshot lags 30–60s
// behind the SocketIO update through the entry/exit countdown (#124).
const STATE_TO_MODE: Record<string, Mode> = {
  disarmed: 'standby',
  armed_home: 'home',
  armed_away: 'away',
};

// Safety bound on the pending indicator. The Abode panel's exit delay is
// typically 30–60s; this covers the worst case plus headroom. Without it, a
// stuck SocketIO subscription would freeze the "Switching…" UI indefinitely.
const PENDING_TIMEOUT_MS = 90_000;

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
  // Entity to watch for live alarm state (#124). Null when no panel is
  // registered — UI falls back to the cached `active` flag on each mode.
  @state() private _panelEntityId: string | null = null;

  // Mode-switching state:
  // - _confirmMode holds the target mode while the confirm dialog is open (#1).
  // - _targetMode (#124) is the mode the user just confirmed switching to.
  //   It persists past the WS round-trip until `hass.states[panel].state`
  //   reaches the corresponding alarm_control_panel state, so the
  //   "Switching…" indicator stays visible through the Abode entry/exit
  //   countdown. Cleared in willUpdate when live state matches, on error,
  //   or via PENDING_TIMEOUT_MS as a safety net.
  // - _setError surfaces a failed switch as a dismissible banner.
  @state() private _confirmMode: AbodeMode | null = null;
  @state() private _targetMode: Mode | null = null;
  @state() private _setError: string | null = null;
  private _pendingTimer: ReturnType<typeof setTimeout> | null = null;

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
      gap: 12px;
    }

    .mode-card {
      background: var(--card-background-color, #fff);
      border-radius: 8px;
      padding: 12px 14px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
      border: 2px solid transparent;
      transition:
        border-color 0.2s,
        box-shadow 0.2s;
    }

    .mode-card.active {
      border-color: var(--primary-color, #03a9f4);
      box-shadow: 0 4px 12px rgba(3, 169, 244, 0.2);
    }

    .mode-header {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 8px;
    }

    .mode-icon {
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--primary-color, #03a9f4);
      color: white;
      border-radius: 50%;
    }

    .mode-icon ha-icon {
      --mdc-icon-size: 20px;
    }

    .mode-info h3 {
      margin: 0;
      font-size: 16px;
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
      margin: 12px 0 0 0;
      padding: 0;
      list-style: none;
    }

    .action-list li {
      padding: 6px 0;
      border-bottom: 1px solid var(--divider-color, #e0e0e0);
      font-size: 13px;
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

    .action-list li.disabled {
      color: var(--secondary-text-color);
      opacity: 0.75;
    }

    .action-list .disabled-tag {
      margin-left: auto;
      padding: 1px 6px;
      background: var(--secondary-background-color, #f5f5f5);
      border-radius: 10px;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
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
      margin-top: 12px;
      padding: 8px 14px;
      border: 1px solid var(--primary-color, #03a9f4);
      border-radius: 4px;
      background: transparent;
      color: var(--primary-color, #03a9f4);
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition:
        background 0.2s,
        color 0.2s;
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
      margin-top: 12px;
      padding: 8px 14px;
      text-align: center;
      font-size: 12px;
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
    this._clearPendingTimer();
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
      const [modesResponse, actions] = await Promise.all([
        fetchModes(this.hass),
        fetchActions(this.hass),
      ]);
      if (signal.aborted) return;
      this._modes = modesResponse.modes;
      // `?? null` normalizes older backends (and test fixtures) that omit
      // the field, keeping the field's declared type accurate at runtime.
      this._panelEntityId = modesResponse.panel_entity_id ?? null;
      this._actions = actions;
    } catch (err) {
      if (signal.aborted) return;
      this._error = err instanceof Error ? err.message : 'Failed to load data';
    } finally {
      if (!signal.aborted) this._loading = false;
    }
  }

  /**
   * Live-derived active mode from `hass.states[panel].state` (#124). Returns
   * null when the panel entity is unknown (older backend, no alarm device)
   * or in an intermediate state (e.g. `arming`, `pending`, `triggered`) the
   * mode mapping doesn't cover. Callers fall back to the cached `mode.active`
   * flag in that case.
   */
  private _liveActiveMode(): Mode | null {
    if (!this._panelEntityId) return null;
    const state = this.hass.states?.[this._panelEntityId]?.state;
    if (!state) return null;
    return STATE_TO_MODE[state] ?? null;
  }

  private _activeMode(): Mode | null {
    const live = this._liveActiveMode();
    if (live !== null) return live;
    // Fallback: no live source (panel_entity_id null or unknown state) →
    // use the cached snapshot's `active` flag.
    return this._modes.find((m) => m.active)?.id ?? null;
  }

  private _clearPendingTimer() {
    if (this._pendingTimer !== null) {
      clearTimeout(this._pendingTimer);
      this._pendingTimer = null;
    }
  }

  /** Drop the "Switching…" pending state. Called from the success path
   * (live state caught up), the error path, and the safety-timeout path. */
  private _resetPending() {
    this._targetMode = null;
    this._clearPendingTimer();
  }

  willUpdate(_changed: PropertyValues) {
    // Drop the pending indicator once live state catches up. This is the
    // success path through the Abode entry/exit countdown — the SocketIO
    // event arrives, `hass` is reassigned by HA, willUpdate fires, and we
    // clear `_targetMode` so the target card flips from "Switching…" to
    // "Current mode".
    if (this._targetMode !== null && this._liveActiveMode() === this._targetMode) {
      this._resetPending();
    }
  }

  private _getActionsForMode(modeId: Mode): AbodeAction[] {
    // Include disabled actions so the in-card list reflects what is
    // configured for the mode (#123). Sort enabled first so disabled ones
    // appear at the bottom of the list as a less-prominent group.
    return this._actions
      .filter((action) => action.modes.includes(modeId))
      .sort((a, b) => Number(b.enabled) - Number(a.enabled));
  }

  private _renderActionCountBadge(mode: AbodeMode) {
    const enabled = mode.action_count;
    const disabled = mode.disabled_action_count ?? 0;
    if (enabled > 0 && disabled > 0) {
      return html`<span class="badge">${enabled} active, ${disabled} disabled</span>`;
    }
    if (enabled === 0 && disabled > 0) {
      return html`<span class="badge">${disabled} disabled</span>`;
    }
    return html`<span class="badge">${enabled} ${enabled === 1 ? 'action' : 'actions'}</span>`;
  }

  private _requestSwitch(mode: AbodeMode) {
    // No-op when this mode is already the live-active one (the UI
    // suppresses the button anyway; this is defense-in-depth for
    // programmatic callers).
    //
    // Note: we deliberately do NOT block on `_targetMode !== null` here.
    // Allowing a second confirm during a pending switch is what makes
    // "switch to standby = cancel arming" reachable when the first switch
    // is still mid-flight or live state lags (#124).
    if (this._activeMode() === mode.id && this._targetMode === null) return;
    // Clear any stale error from a prior failed attempt — opening a fresh
    // confirm dialog implies the user has acknowledged the previous one.
    this._setError = null;
    this._confirmMode = mode;
  }

  private async _confirmSwitch() {
    if (!this._confirmMode) return;
    const target = this._confirmMode;
    this._confirmMode = null;
    this._targetMode = target.id;
    this._setError = null;
    // Safety net: clear the pending indicator if live state never catches
    // up (lost SocketIO subscription, network blip). Without this the
    // target card would say "Switching…" forever.
    this._clearPendingTimer();
    this._pendingTimer = setTimeout(() => {
      this._pendingTimer = null;
      this._targetMode = null;
    }, PENDING_TIMEOUT_MS);
    try {
      await setMode(this.hass, target.id);
    } catch (err) {
      // Match actions-tab convention: log the raw exception for diagnostics,
      // surface a fixed user-facing label so backend internals don't leak.
      console.error('Failed to set mode:', err);
      // Stale-rejection guard: a second _confirmSwitch (e.g. the user
      // clicking Standby to cancel arming) can run while this one is still
      // awaiting setMode. If our request was superseded, _targetMode now
      // points at the newer target — don't clear it or show an error for
      // this stale attempt.
      if (this._targetMode === target.id) {
        this._setError = 'Failed to change mode';
        this._resetPending();
      }
      return;
    }
    // Switch succeeded. Don't reload modes — the active flag is derived
    // live from `hass.states[panel].state` (#124), and the SocketIO update
    // that flips that state will re-render us via the @property hass
    // reassignment HA performs on every state change. `_targetMode` keeps
    // the "Switching…" indicator visible until then.
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

      <div class="modes-grid">${this._modes.map((mode) => this._renderModeCard(mode))}</div>

      <abode-schedules-section .hass=${this.hass}></abode-schedules-section>

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
          Switch the system to <strong>${target.name}</strong>? This changes the live arming state
          and runs any actions configured for this mode.
        </p>
        <button
          slot="footer"
          class="dialog-button cancel"
          @click=${() => (this._confirmMode = null)}
        >
          Cancel
        </button>
        <button slot="footer" class="dialog-button primary" @click=${this._confirmSwitch}>
          Switch
        </button>
      </abode-modal>
    `;
  }

  private _renderModeCard(mode: AbodeMode) {
    const actionsForMode = this._getActionsForMode(mode.id);
    const activeMode = this._activeMode();
    const isActive = activeMode === mode.id;
    const isTarget = this._targetMode === mode.id;
    // While a switch is pending, the target card shows "Switching…" and
    // every other card (including the live-active one) shows a Switch
    // button. That's what makes Standby clickable mid-arming so the user
    // can cancel (#124).
    const showCurrent = isActive && this._targetMode === null;

    return html`
      <div class="mode-card ${isActive ? 'active' : ''}">
        <div class="mode-header">
          <div class="mode-icon">
            <ha-icon icon=${mode.icon}></ha-icon>
          </div>
          <div class="mode-info">
            <h3>${mode.name}</h3>
            <div class="badges">
              ${this._renderActionCountBadge(mode)}
              ${isActive ? html`<span class="badge active">Active</span>` : ''}
            </div>
          </div>
        </div>

        ${actionsForMode.length > 0
          ? html`
              <ul class="action-list" aria-label="Actions for ${mode.name} mode">
                ${actionsForMode.map(
                  (action) => html`
                    <li class=${action.enabled ? nothing : 'disabled'}>
                      <ha-icon icon="mdi:bell-ring"></ha-icon>
                      ${action.name}
                      ${action.enabled ? nothing : html`<span class="disabled-tag">Disabled</span>`}
                    </li>
                  `,
                )}
              </ul>
            `
          : html`<div class="empty-actions">No actions configured</div>`}
        ${showCurrent
          ? html`<div class="current-mode-label">Current mode</div>`
          : html`
              <button
                class="switch-button"
                ?disabled=${isTarget}
                aria-label=${`Switch to ${mode.name} mode`}
                @click=${() => this._requestSwitch(mode)}
              >
                ${isTarget ? `Switching to ${mode.name}…` : `Switch to ${mode.name}`}
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
