import { LitElement, html, css } from 'lit';
import { customElement } from 'lit/decorators.js';

@customElement('abode-configuration-panel')
export class AbodeConfigurationPanel extends LitElement {
  static styles = css`
    :host {
      display: block;
      padding: 16px;
      background-color: var(--primary-background-color);
      color: var(--primary-text-color);
      min-height: 100vh;
    }

    .panel-content {
      max-width: 1200px;
      margin: 0 auto;
    }

    h1 {
      font-size: 24px;
      font-weight: 400;
      margin: 0 0 16px 0;
      color: var(--primary-text-color);
    }
  `;

  render() {
    return html`
      <div class="panel-content">
        <h1>Abode Configuration</h1>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'abode-configuration-panel': AbodeConfigurationPanel;
  }
}
