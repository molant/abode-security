import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { HomeAssistant, AbodeCamera } from './types';
import { fetchCameras } from './api';

/**
 * Cameras tab — lists every camera entity sharing a device with an
 * Abode-managed sensor. Auto-discovers on tab activation; refreshes
 * still images every 5 s while visible. Tapping a notification deep-link
 * with `?tab=cameras&camera=<entity_id>` scrolls and highlights the
 * matching card.
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
  @state() private _refreshToken: number = Date.now();
  @state() private _imageErrors: Set<string> = new Set();

  private _abort: AbortController | null = null;
  private _refreshInterval: ReturnType<typeof setInterval> | null = null;
  private _highlightTimeout: ReturnType<typeof setTimeout> | null = null;

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
      transition: box-shadow 0.2s;
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
      padding: 12px 16px 8px;
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

    .camera-image {
      width: 100%;
      display: block;
      background: #000;
      min-height: 160px;
      object-fit: cover;
    }

    .camera-image-error {
      min-height: 160px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #1a1a1a;
      color: #666;
      font-size: 12px;
    }

    .paired-sensors {
      padding: 8px 16px 12px;
      font-size: 12px;
      color: var(--secondary-text-color, #757575);
    }
  `;

  connectedCallback() {
    super.connectedCallback();
    void this._loadCameras();
    this._startRefresh();
  }

  disconnectedCallback() {
    this._abort?.abort();
    this._abort = null;
    this._stopRefresh();
    if (this._highlightTimeout !== null) {
      clearTimeout(this._highlightTimeout);
      this._highlightTimeout = null;
    }
    super.disconnectedCallback();
  }

  updated(changedProps: Map<string, unknown>) {
    if (changedProps.has('selectedCameraEntityId') && this.selectedCameraEntityId) {
      this._scrollToSelected();
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

  private _startRefresh() {
    this._stopRefresh();
    this._refreshInterval = setInterval(() => {
      if (document.visibilityState !== 'hidden') {
        this._refreshToken = Date.now();
      }
    }, 5000);
  }

  private _stopRefresh() {
    if (this._refreshInterval !== null) {
      clearInterval(this._refreshInterval);
      this._refreshInterval = null;
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

  private _stillUrl(camera: AbodeCamera): string {
    return `/api/camera_proxy/${camera.entity_id}?_=${this._refreshToken}`;
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
      return html`
        <div class="empty-state">
          No Abode cameras found. Pair a camera with one of your Abode sensors via Settings →
          Devices.
        </div>
      `;
    }
    return html`
      <div class="camera-list">${this._cameras.map((camera) => this._renderCard(camera))}</div>
    `;
  }

  private _renderCard(camera: AbodeCamera) {
    const hasError = this._imageErrors.has(camera.entity_id);
    return html`
      <div class="camera-card" data-entity-id=${camera.entity_id}>
        <div class="camera-card-header">
          <span class="camera-name">${camera.name}</span>
          ${camera.area ? html`<span class="area-chip">${camera.area}</span>` : ''}
        </div>
        ${hasError
          ? html`<div class="camera-image-error">Failed to load image</div>`
          : html`<img
              class="camera-image"
              src=${this._stillUrl(camera)}
              alt=${camera.name}
              loading="lazy"
              @error=${() => this._handleImageError(camera.entity_id)}
            />`}
        ${camera.paired_sensor_entity_ids.length > 0
          ? html`
              <div class="paired-sensors">
                Paired with: ${this._pairedSensorNames(camera.paired_sensor_entity_ids)}
              </div>
            `
          : ''}
      </div>
    `;
  }

  private _pairedSensorNames(entityIds: string[]): string {
    return entityIds
      .map((id) => {
        const state = this.hass.states[id];
        return state?.attributes?.['friendly_name'] ?? id;
      })
      .join(', ');
  }

  private _handleImageError(entityId: string) {
    this._imageErrors = new Set([...this._imageErrors, entityId]);
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'abode-cameras-tab': CamerasTab;
  }
}
