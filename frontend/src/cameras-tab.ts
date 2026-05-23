import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { HomeAssistant, AbodeCamera } from './types';
import { fetchCameras } from './api';

/**
 * Cameras tab — lists every camera entity in Home Assistant. The integration
 * is camera-source-agnostic so any HA camera (Abode, Unifi Protect, generic,
 * …) is a valid deep-link target.
 *
 * Each card renders HA's native <ha-camera-stream> (the same element the
 * picture-entity Lovelace card uses with `camera_view: auto`) so auth and
 * stream lifecycle are handled by HA. Tapping a card fires `hass-more-info`,
 * matching `tap_action: more-info` on picture-entity. On deep-link arrival
 * (`?camera=<entity_id>`), the matching camera's more-info dialog auto-opens
 * once so the user lands directly on the stream; the underlying grid is
 * still rendered so closing the dialog leaves the user on the scrolled and
 * highlighted card.
 *
 * @prop {HomeAssistant} hass - Required. Provided by the panel.
 * @prop {string | null} selectedCameraEntityId - Set by the panel from
 *   the URL query on deep-link arrival. Null clears highlight.
 */
@customElement('abode-cameras-tab')
export class CamerasTab extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) selectedCameraEntityId: string | null = null;

  @state() private _cameras: AbodeCamera[] = [];
  @state() private _loading = true;
  @state() private _error: string | null = null;

  private _abort: AbortController | null = null;
  private _highlightTimeout: ReturnType<typeof setTimeout> | null = null;
  private _autoOpenedFor: string | null = null;

  static styles = css`
    :host {
      display: block;
    }

    .loading,
    .empty-state {
      padding: 32px 16px;
      text-align: center;
      color: var(--secondary-text-color, #757575);
    }

    .error {
      padding: 16px;
      color: var(--error-color, #db4437);
    }

    .retry-button {
      margin-top: 8px;
      padding: 8px 16px;
      border: 1px solid var(--primary-color, #03a9f4);
      background: transparent;
      color: var(--primary-color, #03a9f4);
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
    }

    .camera-list {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 16px;
    }

    .camera-card {
      border: 1px solid var(--divider-color, #e0e0e0);
      border-radius: 8px;
      overflow: hidden;
      background: var(--card-background-color, #fff);
      cursor: pointer;
      transition: box-shadow 0.2s;
    }

    .camera-card:hover {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    }

    .camera-card.highlight {
      animation: highlight-pulse 1.5s ease-out;
    }

    @keyframes highlight-pulse {
      0% {
        box-shadow: 0 0 0 4px var(--primary-color, #03a9f4);
      }
      100% {
        box-shadow: 0 0 0 0 transparent;
      }
    }

    .camera-card-header {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 16px;
    }

    .camera-name {
      font-weight: 500;
      flex: 1;
    }

    .area-chip {
      font-size: 11px;
      padding: 2px 8px;
      background: var(--secondary-background-color, #f5f5f5);
      border-radius: 12px;
      color: var(--secondary-text-color, #757575);
    }

    .camera-stream {
      display: block;
      width: 100%;
      min-height: 160px;
      background: #000;
    }
  `;

  connectedCallback() {
    super.connectedCallback();
    void this._loadCameras();
  }

  disconnectedCallback() {
    this._abort?.abort();
    this._abort = null;
    if (this._highlightTimeout !== null) {
      clearTimeout(this._highlightTimeout);
      this._highlightTimeout = null;
    }
    super.disconnectedCallback();
  }

  updated(changedProps: Map<string, unknown>) {
    // Reset the auto-open guard when the deep-link target itself changes
    // (Lit only puts the prop in changedProps when it actually differs).
    if (changedProps.has('selectedCameraEntityId')) {
      this._autoOpenedFor = null;
    }
    // Only react to the deep-link on selection change or when the cameras
    // list arrives — without this guard every `hass` rebind would re-call
    // scrollIntoView and re-arm the highlight pulse.
    const deepLinkChanged =
      changedProps.has('selectedCameraEntityId') || changedProps.has('_cameras');
    if (deepLinkChanged && this.selectedCameraEntityId) {
      this._scrollToSelected();
      this._maybeAutoOpenMoreInfo();
    }
  }

  private async _loadCameras() {
    this._abort?.abort();
    const controller = new AbortController();
    this._abort = controller;
    const { signal } = controller;

    this._loading = true;
    this._error = null;

    try {
      const cameras = await fetchCameras(this.hass);
      if (signal.aborted) return;
      this._cameras = cameras;
    } catch (err) {
      if (signal.aborted) return;
      this._error = err instanceof Error ? err.message : 'Failed to load cameras';
    } finally {
      if (!signal.aborted) this._loading = false;
    }
  }

  private _scrollToSelected() {
    // Wait for the next paint so the card exists in the DOM.
    requestAnimationFrame(() => {
      if (!this.selectedCameraEntityId) return;
      const card = this.shadowRoot?.querySelector<HTMLElement>(
        `[data-entity-id="${CSS.escape(this.selectedCameraEntityId)}"]`,
      );
      if (!card) return;
      card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      card.classList.add('highlight');
      if (this._highlightTimeout !== null) clearTimeout(this._highlightTimeout);
      this._highlightTimeout = setTimeout(() => {
        card.classList.remove('highlight');
        this._highlightTimeout = null;
      }, 1500);
    });
  }

  private _maybeAutoOpenMoreInfo() {
    const target = this.selectedCameraEntityId;
    if (!target) return;
    if (this._autoOpenedFor === target) return;
    if (!this._cameras.some((c) => c.entity_id === target)) return;
    this._autoOpenedFor = target;
    this._openMoreInfo(target);
  }

  private _openMoreInfo(entityId: string) {
    this.dispatchEvent(
      new CustomEvent('hass-more-info', {
        detail: { entityId },
        bubbles: true,
        composed: true,
      }),
    );
  }

  render() {
    if (this._loading) {
      return html`<div class="loading">Loading cameras…</div>`;
    }
    if (this._error) {
      return html`
        <div class="error">
          ${this._error}
          <div>
            <button class="retry-button" @click=${() => this._loadCameras()}>Retry</button>
          </div>
        </div>
      `;
    }
    if (this._cameras.length === 0) {
      return html`<div class="empty-state">No cameras found in Home Assistant.</div>`;
    }
    return html`
      <div class="camera-list">${this._cameras.map((camera) => this._renderCard(camera))}</div>
    `;
  }

  private _renderCard(camera: AbodeCamera) {
    const stateObj = this.hass.states?.[camera.entity_id];
    return html`
      <div
        class="camera-card"
        data-entity-id=${camera.entity_id}
        role="button"
        tabindex="0"
        @click=${() => this._openMoreInfo(camera.entity_id)}
        @keydown=${(ev: KeyboardEvent) => {
          if (ev.key === 'Enter' || ev.key === ' ') {
            ev.preventDefault();
            this._openMoreInfo(camera.entity_id);
          }
        }}
      >
        <div class="camera-card-header">
          <span class="camera-name">${camera.name}</span>
          ${camera.area ? html`<span class="area-chip">${camera.area}</span>` : ''}
        </div>
        <ha-camera-stream
          class="camera-stream"
          allow-exoplayer
          muted
          .hass=${this.hass}
          .stateObj=${stateObj}
        ></ha-camera-stream>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'abode-cameras-tab': CamerasTab;
  }
}
