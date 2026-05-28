import { LitElement, html, css, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { AbodeSchedule, ScheduleCreateInput } from './types';
import './day-chip-picker';

/**
 * A single schedule row in view or edit mode.
 *
 * View mode: shows weekdays (read-only chips), arm→disarm times, enable
 * toggle, and — when canEdit — edit/delete icons.
 *
 * Edit mode: inline form with editable day chips, time inputs, optional
 * name, enable toggle, Save and Cancel buttons.
 *
 * Events emitted:
 * - `save`       { detail: { id: string; data: ScheduleCreateInput } }
 * - `delete`     { detail: { id: string } }
 * - `cancel-new` { detail: {} } — only when schedule.id === '' (new-row mode)
 */
@customElement('abode-schedule-row')
export class ScheduleRow extends LitElement {
  @property({ attribute: false }) schedule!: AbodeSchedule;
  @property({ type: Boolean }) canEdit = false;

  @state() private _editing = false;
  @state() private _draft: ScheduleCreateInput | null = null;
  @state() private _error: string | null = null;
  @state() private _saving = false;

  static styles = css`
    :host {
      display: block;
    }

    .row {
      padding: 10px 0;
      border-bottom: 1px solid var(--divider-color, #e0e0e0);
    }

    .row:last-of-type {
      border-bottom: none;
    }

    .view-row {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }

    .view-row.disabled {
      opacity: 0.5;
    }

    .time-display {
      font-size: 14px;
      color: var(--primary-text-color);
      white-space: nowrap;
    }

    .row-name {
      font-size: 13px;
      color: var(--secondary-text-color);
      font-style: italic;
    }

    .error-badge {
      display: inline-flex;
      align-items: center;
      padding: 2px 6px;
      background: var(--error-color, #f44336);
      color: white;
      border-radius: 10px;
      font-size: 11px;
      gap: 4px;
    }

    .icon-button {
      background: transparent;
      border: none;
      cursor: pointer;
      padding: 4px;
      color: var(--secondary-text-color);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 4px;
      transition:
        color 0.15s,
        background 0.15s;
    }

    .icon-button:hover {
      color: var(--primary-text-color);
      background: var(--secondary-background-color, #f5f5f5);
    }

    .icon-button:focus-visible {
      outline: 2px solid var(--primary-color, #03a9f4);
      outline-offset: 2px;
    }

    .icon-button.delete:hover {
      color: var(--error-color, #f44336);
    }

    .spacer {
      flex: 1;
    }

    /* Edit form */
    .edit-form {
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 4px 0;
    }

    .form-row {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .form-row label {
      font-size: 13px;
      color: var(--secondary-text-color);
      min-width: 60px;
    }

    .time-input {
      padding: 4px 8px;
      border: 1px solid var(--divider-color, #e0e0e0);
      border-radius: 4px;
      font-size: 14px;
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color);
    }

    .time-input:focus {
      outline: 2px solid var(--primary-color, #03a9f4);
      border-color: transparent;
    }

    .name-input {
      padding: 4px 8px;
      border: 1px solid var(--divider-color, #e0e0e0);
      border-radius: 4px;
      font-size: 14px;
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color);
      width: 180px;
    }

    .name-input:focus {
      outline: 2px solid var(--primary-color, #03a9f4);
      border-color: transparent;
    }

    .arrow {
      color: var(--secondary-text-color);
      font-size: 14px;
    }

    .form-actions {
      display: flex;
      gap: 8px;
      align-items: center;
    }

    .btn {
      padding: 6px 14px;
      border: none;
      border-radius: 4px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s;
    }

    .btn.primary {
      background: var(--primary-color, #03a9f4);
      color: white;
    }

    .btn.primary:hover:not(:disabled) {
      background: var(--primary-color-dark, #0288d1);
    }

    .btn.primary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .btn.secondary {
      background: transparent;
      color: var(--secondary-text-color);
    }

    .btn.secondary:hover {
      background: var(--secondary-background-color, #f5f5f5);
    }

    .btn:focus-visible {
      outline: 2px solid var(--primary-color, #03a9f4);
      outline-offset: 2px;
    }

    .validation-error {
      font-size: 12px;
      color: var(--error-color, #f44336);
      padding: 2px 0;
    }

    .enable-toggle {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      cursor: pointer;
    }

    .enable-toggle input[type='checkbox'] {
      cursor: pointer;
    }
  `;

  connectedCallback() {
    super.connectedCallback();
    // New-row mode: start in edit immediately. The `?.` guards the brief
    // window before Lit sets property values from attribute bindings; it does
    // not imply `schedule` can be permanently absent (it is `!`-asserted).
    if (this.schedule?.id === '') {
      this._startEdit();
    }
  }

  private _startEdit() {
    this._editing = true;
    // Project only the editable subset — `AbodeSchedule` includes server-
    // managed fields (id, created_at, last_*_at, etc.) that are NOT part
    // of `ScheduleCreateInput`. A naive `{...this.schedule}` widens the
    // draft type and TS will reject the eventual save call.
    this._draft = {
      name: this.schedule.name,
      weekdays: [...this.schedule.weekdays],
      arm_time: this.schedule.arm_time,
      disarm_time: this.schedule.disarm_time,
      enabled: this.schedule.enabled,
    };
    this._error = null;
  }

  private _cancel() {
    this._saving = false;
    if (this.schedule.id === '') {
      // New-row mode: parent removes this element, so _editing/_draft need
      // not be reset — the element is destroyed immediately after cancel-new.
      this.dispatchEvent(
        new CustomEvent('cancel-new', { detail: {}, bubbles: true, composed: true }),
      );
      return;
    }
    this._editing = false;
    this._draft = null;
    this._error = null;
  }

  private _validate(draft: ScheduleCreateInput): string | null {
    if (draft.weekdays.length === 0) return 'Pick at least one weekday';
    if (draft.arm_time === draft.disarm_time) return 'Arm and disarm times must differ';
    if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(draft.arm_time)) return 'Invalid arm time';
    if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(draft.disarm_time)) return 'Invalid disarm time';
    if ((draft.name?.length ?? 0) > 100) return 'Name too long (max 100)';
    return null;
  }

  private _save() {
    if (!this._draft) return;
    const err = this._validate(this._draft);
    if (err) {
      this._error = err;
      return;
    }
    this._error = null;
    this._saving = true;
    this.dispatchEvent(
      new CustomEvent('save', {
        detail: { id: this.schedule.id, data: { ...this._draft } },
        bubbles: true,
        composed: true,
      }),
    );
    // Parent resets _editing by replacing the schedule prop on success
  }

  private _delete() {
    this.dispatchEvent(
      new CustomEvent('delete', {
        detail: { id: this.schedule.id },
        bubbles: true,
        composed: true,
      }),
    );
  }

  private _onDaysChange(e: Event) {
    if (!this._draft) return;
    const { selected } = (e as CustomEvent).detail;
    this._draft = { ...this._draft, weekdays: selected };
    this._error = null;
  }

  private _onArmTimeChange(e: Event) {
    if (!this._draft) return;
    this._draft = { ...this._draft, arm_time: (e.target as HTMLInputElement).value };
    this._error = null;
  }

  private _onDisarmTimeChange(e: Event) {
    if (!this._draft) return;
    this._draft = { ...this._draft, disarm_time: (e.target as HTMLInputElement).value };
    this._error = null;
  }

  private _onNameChange(e: Event) {
    if (!this._draft) return;
    this._draft = { ...this._draft, name: (e.target as HTMLInputElement).value };
  }

  private _onEnabledChange(e: Event) {
    if (!this._draft) return;
    this._draft = { ...this._draft, enabled: (e.target as HTMLInputElement).checked };
  }

  render() {
    if (this._editing && this._draft) {
      return this._renderEditMode(this._draft);
    }
    return this._renderViewMode();
  }

  private _renderViewMode() {
    const s = this.schedule;
    const isDisabled = !s.enabled;
    return html`
      <div class="row">
        <div class="view-row ${isDisabled ? 'disabled' : ''}">
          <abode-day-chip-picker .selected=${s.weekdays} .disabled=${true}></abode-day-chip-picker>
          <span class="time-display">${s.arm_time} → ${s.disarm_time}</span>
          ${s.name ? html`<span class="row-name">${s.name}</span>` : nothing}
          ${s.last_error
            ? html`<span class="error-badge" title=${s.last_error}>⚠ Error</span>`
            : nothing}
          <span class="spacer"></span>
          <label class="enable-toggle" title=${s.enabled ? 'Enabled' : 'Disabled'}>
            <input
              type="checkbox"
              .checked=${s.enabled}
              ?disabled=${!this.canEdit}
              aria-label=${s.enabled ? 'Enabled' : 'Disabled'}
              @change=${this._onViewEnabledChange}
            />
            ${s.enabled ? 'Enabled' : 'Disabled'}
          </label>
          ${this.canEdit
            ? html`
                <button
                  type="button"
                  class="icon-button"
                  aria-label="Edit schedule"
                  title="Edit"
                  @click=${this._startEdit}
                >
                  ✏
                </button>
                <button
                  type="button"
                  class="icon-button delete"
                  aria-label="Delete schedule"
                  title="Delete"
                  @click=${this._delete}
                >
                  🗑
                </button>
              `
            : nothing}
        </div>
      </div>
    `;
  }

  private _onViewEnabledChange(e: Event) {
    if (!this.canEdit) return;
    const enabled = (e.target as HTMLInputElement).checked;
    // Emit save with only the enabled field changed so the parent can call
    // updateSchedule without the user having to enter full edit mode.
    this.dispatchEvent(
      new CustomEvent('save', {
        detail: {
          id: this.schedule.id,
          data: {
            name: this.schedule.name,
            weekdays: [...this.schedule.weekdays],
            arm_time: this.schedule.arm_time,
            disarm_time: this.schedule.disarm_time,
            enabled,
          },
        },
        bubbles: true,
        composed: true,
      }),
    );
  }

  private _renderEditMode(draft: ScheduleCreateInput) {
    return html`
      <div class="row">
        <div class="edit-form">
          <div class="form-row">
            <abode-day-chip-picker
              .selected=${draft.weekdays}
              @change=${this._onDaysChange}
            ></abode-day-chip-picker>
          </div>
          <div class="form-row">
            <label>Arm</label>
            <input
              type="time"
              class="time-input"
              .value=${draft.arm_time}
              @change=${this._onArmTimeChange}
              aria-label="Arm time"
            />
            <span class="arrow">→</span>
            <label>Disarm</label>
            <input
              type="time"
              class="time-input"
              .value=${draft.disarm_time}
              @change=${this._onDisarmTimeChange}
              aria-label="Disarm time"
            />
          </div>
          <div class="form-row">
            <label>Name</label>
            <input
              type="text"
              class="name-input"
              .value=${draft.name ?? ''}
              placeholder="Optional label"
              maxlength="100"
              @input=${this._onNameChange}
              aria-label="Schedule name"
            />
          </div>
          <div class="form-row">
            <label class="enable-toggle">
              <input
                type="checkbox"
                .checked=${draft.enabled ?? true}
                @change=${this._onEnabledChange}
                aria-label="Enabled"
              />
              Enabled
            </label>
          </div>
          ${this._error
            ? html`<div class="validation-error" role="alert">${this._error}</div>`
            : nothing}
          <div class="form-actions">
            <button
              type="button"
              class="btn primary"
              ?disabled=${this._saving}
              @click=${this._save}
            >
              Save
            </button>
            <button type="button" class="btn secondary" @click=${this._cancel}>Cancel</button>
          </div>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'abode-schedule-row': ScheduleRow;
  }
}
