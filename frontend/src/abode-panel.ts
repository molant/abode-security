import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { HomeAssistant } from './types';
import './modes-tab';
import './actions-tab';

@customElement('abode-configuration-panel')
export class AbodeConfigurationPanel extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @state() private _activeTab: 'modes' | 'actions' = 'actions';

  static styles = css`
    :host {
      display: block;
      background-color: var(--primary-background-color);
      color: var(--primary-text-color);
      min-height: 100vh;
    }

    .panel-content {
      max-width: 1200px;
      margin: 0 auto;
      padding: 16px;
    }

    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;
    }

    h1 {
      font-size: 24px;
      font-weight: 400;
      margin: 0;
      color: var(--primary-text-color);
    }

    .tab-bar {
      display: flex;
      gap: 4px;
      border-bottom: 1px solid var(--divider-color, #e0e0e0);
      margin-bottom: 16px;
    }

    .tab-bar button {
      padding: 12px 24px;
      border: none;
      background: transparent;
      color: var(--secondary-text-color, #757575);
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      margin-bottom: -1px;
      transition: color 0.2s, border-color 0.2s;
    }

    .tab-bar button:hover {
      color: var(--primary-text-color);
    }

    .tab-bar button.active {
      color: var(--primary-color, #03a9f4);
      border-bottom-color: var(--primary-color, #03a9f4);
    }

    .tab-bar button:focus {
      outline: none;
    }

    .tab-bar button:focus-visible {
      outline: 2px solid var(--primary-color, #03a9f4);
      outline-offset: -2px;
    }

    .tab-content {
      min-height: 400px;
    }
  `;

  render() {
    const activeTabId = this._activeTab === 'modes' ? 'modes-panel' : 'actions-panel';
    return html`
      <div class="panel-content">
        <div class="header">
          <h1>Abode Configuration</h1>
        </div>

        <div class="tab-bar" role="tablist">
          <button
            role="tab"
            id="actions-tab"
            aria-selected=${this._activeTab === 'actions'}
            aria-controls="actions-panel"
            class=${this._activeTab === 'actions' ? 'active' : ''}
            @click=${() => (this._activeTab = 'actions')}
          >
            Actions
          </button>
          <button
            role="tab"
            id="modes-tab"
            aria-selected=${this._activeTab === 'modes'}
            aria-controls="modes-panel"
            class=${this._activeTab === 'modes' ? 'active' : ''}
            @click=${() => (this._activeTab = 'modes')}
          >
            Modes
          </button>
        </div>

        <div
          class="tab-content"
          role="tabpanel"
          id=${activeTabId}
          aria-labelledby=${this._activeTab === 'modes' ? 'modes-tab' : 'actions-tab'}
        >
          ${this._activeTab === 'modes'
            ? html`<abode-modes-tab .hass=${this.hass}></abode-modes-tab>`
            : html`<abode-actions-tab .hass=${this.hass}></abode-actions-tab>`}
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'abode-configuration-panel': AbodeConfigurationPanel;
  }
}
