import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { HomeAssistant, AbodeMode, AbodeAction } from './types';
import { fetchModes, fetchActions } from './api';

@customElement('abode-modes-tab')
export class ModesTab extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @state() private _modes: AbodeMode[] = [];
  @state() private _actions: AbodeAction[] = [];
  @state() private _loading = true;
  @state() private _error: string | null = null;

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

  private async _loadData() {
    this._abort?.abort();
    const controller = new AbortController();
    this._abort = controller;
    const { signal } = controller;

    this._loading = true;
    this._error = null;

    try {
      const [modes, actions] = await Promise.all([
        fetchModes(this.hass),
        fetchActions(this.hass),
      ]);
      if (signal.aborted) return;
      this._modes = modes ?? [];
      this._actions = actions ?? [];
    } catch (err) {
      if (signal.aborted) return;
      this._error = err instanceof Error ? err.message : 'Failed to load data';
    } finally {
      if (!signal.aborted) this._loading = false;
    }
  }

  private _getActionsForMode(modeId: string): AbodeAction[] {
    return this._actions.filter(
      (action) => action.enabled && action.modes.includes(modeId)
    );
  }

  render() {
    if (this._loading) {
      return html`<div class="loading">Loading modes...</div>`;
    }

    if (this._error) {
      return html`<div class="error" role="alert">${this._error}</div>`;
    }

    return html`
      <div class="modes-grid">
        ${this._modes.map((mode) => this._renderModeCard(mode))}
      </div>
    `;
  }

  private _renderModeCard(mode: AbodeMode) {
    const actionsForMode = this._getActionsForMode(mode.id);

    return html`
      <div class="mode-card ${mode.active ? 'active' : ''}">
        <div class="mode-header">
          <div class="mode-icon">
            <ha-icon icon=${mode.icon}></ha-icon>
          </div>
          <div class="mode-info">
            <h3>${mode.name}</h3>
            <div class="badges">
              <span class="badge">${mode.action_count} actions</span>
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
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'abode-modes-tab': ModesTab;
  }
}
