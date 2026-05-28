import { LitElement, html, css, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { AbodeSchedule, HomeAssistant, ScheduleCreateInput } from './types';
import { fetchSchedules, createSchedule, updateSchedule, deleteSchedule } from './api';
import './schedule-row';
import './abode-modal';

/**
 * Section container that lists all Home schedules below the modes grid.
 *
 * Fetches schedules on mount via WebSocket. Admin users see an Add button
 * and per-row edit/delete controls; non-admins see read-only rows.
 *
 * Admin gating in the UI is a UX layer only — the WS endpoints enforce
 * `@require_admin` server-side. The frontend hides controls non-admins
 * can't use so they don't hit dead-end errors.
 *
 * @prop {HomeAssistant} hass - Required.
 */
@customElement('abode-schedules-section')
export class SchedulesSection extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;

  @state() private _schedules: AbodeSchedule[] = [];
  @state() private _loading = true;
  @state() private _error: string | null = null;
  @state() private _newRow: AbodeSchedule | null = null;
  @state() private _confirmDeleteId: string | null = null;

  private _abort: AbortController | null = null;

  static styles = css`
    :host {
      display: block;
      margin-top: 24px;
    }

    .section-heading {
      font-size: 16px;
      font-weight: 500;
      color: var(--primary-text-color);
      margin: 0 0 12px 0;
    }

    .loading {
      color: var(--secondary-text-color);
      font-size: 14px;
    }

    .error-banner {
      padding: 10px 14px;
      background: var(--error-color, #f44336);
      color: white;
      border-radius: 4px;
      font-size: 14px;
      margin-bottom: 12px;
    }

    .empty-state {
      color: var(--secondary-text-color);
      font-size: 14px;
      font-style: italic;
      padding: 8px 0;
    }

    .add-button {
      margin-top: 12px;
      padding: 6px 14px;
      border: 1px solid var(--primary-color, #03a9f4);
      border-radius: 4px;
      background: transparent;
      color: var(--primary-color, #03a9f4);
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition:
        background 0.15s,
        color 0.15s;
    }

    .add-button:hover {
      background: var(--primary-color, #03a9f4);
      color: white;
    }

    .add-button:focus-visible {
      outline: 2px solid var(--primary-color, #03a9f4);
      outline-offset: 2px;
    }

    /* Confirm-delete dialog buttons */
    .dialog-button {
      padding: 8px 16px;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s;
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
      background: var(--error-color, #f44336);
      opacity: 0.85;
    }

    .dialog-button:focus-visible {
      outline: 2px solid var(--primary-color, #03a9f4);
      outline-offset: 2px;
    }
  `;

  connectedCallback() {
    super.connectedCallback();
    // Kick off the fetch as fire-and-forget; _load handles its own errors.
    void this._load();
  }

  disconnectedCallback() {
    this._abort?.abort();
    this._abort = null;
    super.disconnectedCallback();
  }

  private get _isAdmin(): boolean {
    // HA exposes `hass.user.is_admin` as a UX hint. The WS endpoints
    // enforce @require_admin server-side; this only hides controls.
    // If `hass.user` is absent (rare, during HA reload), treat as non-admin.
    return Boolean(this.hass.user?.is_admin);
  }

  private async _load() {
    this._abort?.abort();
    const controller = new AbortController();
    this._abort = controller;
    const { signal } = controller;

    this._loading = true;
    this._error = null;
    try {
      const schedules = await fetchSchedules(this.hass);
      if (signal.aborted) return;
      this._schedules = schedules;
    } catch (err) {
      if (signal.aborted) return;
      this._error = err instanceof Error ? err.message : 'Failed to load schedules';
    } finally {
      if (!signal.aborted) this._loading = false;
    }
  }

  private _addNewRow() {
    this._newRow = {
      id: '',
      name: '',
      weekdays: [],
      arm_time: '22:00',
      disarm_time: '06:00',
      enabled: true,
      created_at: '',
      last_armed_at: null,
      last_disarmed_at: null,
      last_skip_reason: null,
      last_error: null,
    };
  }

  private async _onSave(e: Event) {
    const { id, data } = (e as CustomEvent<{ id: string; data: ScheduleCreateInput }>).detail;
    this._error = null;
    try {
      if (!id) {
        const created = await createSchedule(this.hass, data);
        this._schedules = [...this._schedules, created];
        this._newRow = null;
      } else {
        const updated = await updateSchedule(this.hass, { id, ...data });
        this._schedules = this._schedules.map((s) => (s.id === id ? updated : s));
      }
    } catch (err) {
      this._error = err instanceof Error ? err.message : 'Failed to save schedule';
    }
  }

  private _onDeleteRequest(e: Event) {
    const { id } = (e as CustomEvent<{ id: string }>).detail;
    this._confirmDeleteId = id;
  }

  private async _confirmDelete() {
    const id = this._confirmDeleteId;
    if (!id) return;
    this._confirmDeleteId = null;
    this._error = null;
    try {
      await deleteSchedule(this.hass, id);
      this._schedules = this._schedules.filter((s) => s.id !== id);
    } catch (err) {
      this._error = err instanceof Error ? err.message : 'Failed to delete schedule';
    }
  }

  render() {
    return html`
      <section
        aria-labelledby="schedules-heading"
        @save=${this._onSave}
        @delete=${this._onDeleteRequest}
        @cancel-new=${() => {
          this._newRow = null;
        }}
      >
        <h2 id="schedules-heading" class="section-heading">Home schedules</h2>

        ${this._loading ? html`<div class="loading">Loading…</div>` : nothing}
        ${this._error ? html`<div role="alert" class="error-banner">${this._error}</div>` : nothing}
        ${!this._loading && this._schedules.length === 0 && !this._newRow
          ? html`<p class="empty-state">No schedules yet. Add one to arm Home automatically.</p>`
          : nothing}
        ${this._schedules.map(
          (s) => html`
            <abode-schedule-row .schedule=${s} .canEdit=${this._isAdmin}></abode-schedule-row>
          `,
        )}
        ${this._newRow
          ? html`
              <abode-schedule-row .schedule=${this._newRow} .canEdit=${true}></abode-schedule-row>
            `
          : nothing}
        ${this._isAdmin && !this._newRow
          ? html` <button class="add-button" @click=${this._addNewRow}>+ Add schedule</button> `
          : nothing}
      </section>

      ${this._confirmDeleteId ? this._renderDeleteConfirm() : nothing}
    `;
  }

  private _renderDeleteConfirm() {
    return html`
      <abode-modal
        heading="Delete schedule?"
        variant="alertdialog"
        @dismiss=${() => {
          this._confirmDeleteId = null;
        }}
      >
        <p>
          This will stop the automatic arming at the configured times. The action does not affect
          the current panel state.
        </p>
        <button
          slot="footer"
          class="dialog-button cancel"
          @click=${() => {
            this._confirmDeleteId = null;
          }}
        >
          Cancel
        </button>
        <button slot="footer" class="dialog-button danger" @click=${this._confirmDelete}>
          Delete
        </button>
      </abode-modal>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'abode-schedules-section': SchedulesSection;
  }
}
