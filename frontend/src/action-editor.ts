import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type {
  HomeAssistant,
  AbodeAction,
  SensorsByCategory,
  AlarmEntity,
} from './types';
import { fetchSensors, fetchAlarms, createAction, updateAction } from './api';

type SensorCategory = keyof SensorsByCategory;

@customElement('abode-action-editor')
export class ActionEditor extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) action: AbodeAction | null = null;

  @state() private _name = '';
  @state() private _modes: string[] = [];
  @state() private _delaySeconds = 0;
  @state() private _selectedSensors: string[] = [];
  @state() private _selectedAlarms: string[] = [];
  @state() private _sensors: SensorsByCategory | null = null;
  @state() private _alarms: AlarmEntity[] = [];
  @state() private _errors: Record<string, string> = {};
  @state() private _saving = false;
  @state() private _loading = true;

  static styles = css`
    :host {
      display: block;
    }

    .editor-overlay {
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
      padding: 16px;
    }

    .editor-dialog {
      background: var(--card-background-color, #fff);
      border-radius: 12px;
      padding: 24px;
      max-width: 600px;
      width: 100%;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }

    h2 {
      margin: 0 0 24px 0;
      font-size: 20px;
      font-weight: 500;
      color: var(--primary-text-color);
    }

    .form-group {
      margin-bottom: 20px;
    }

    .form-group label {
      display: block;
      font-size: 14px;
      font-weight: 500;
      color: var(--primary-text-color);
      margin-bottom: 8px;
    }

    .form-group input[type='text'] {
      width: 100%;
      padding: 12px;
      border: 1px solid var(--divider-color, #e0e0e0);
      border-radius: 4px;
      font-size: 14px;
      color: var(--primary-text-color);
      background: var(--card-background-color, #fff);
      box-sizing: border-box;
    }

    .form-group input[type='text']:focus {
      outline: none;
      border-color: var(--primary-color, #03a9f4);
      box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.2);
    }

    .form-group input[type='text'].error {
      border-color: var(--error-color, #f44336);
    }

    .error-text {
      display: block;
      color: var(--error-color, #f44336);
      font-size: 12px;
      margin-top: 4px;
    }

    .checkbox-group {
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
    }

    .checkbox-group label {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: normal;
      cursor: pointer;
    }

    .checkbox-group input[type='checkbox'] {
      width: 18px;
      height: 18px;
      cursor: pointer;
      accent-color: var(--primary-color, #03a9f4);
    }

    .delay-control {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .delay-control input[type='range'] {
      flex: 1;
      height: 4px;
      accent-color: var(--primary-color, #03a9f4);
    }

    .delay-value {
      min-width: 50px;
      text-align: right;
      font-size: 14px;
      color: var(--primary-text-color);
    }

    .sensor-categories {
      display: flex;
      flex-direction: column;
      gap: 12px;
      max-height: 200px;
      overflow-y: auto;
      border: 1px solid var(--divider-color, #e0e0e0);
      border-radius: 4px;
      padding: 12px;
    }

    .category {
      border-bottom: 1px solid var(--divider-color, #e0e0e0);
      padding-bottom: 12px;
    }

    .category:last-child {
      border-bottom: none;
      padding-bottom: 0;
    }

    .category-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 500;
      text-transform: capitalize;
      margin-bottom: 8px;
      cursor: pointer;
    }

    .category-header input[type='checkbox'] {
      width: 16px;
      height: 16px;
      accent-color: var(--primary-color, #03a9f4);
    }

    .category-items {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding-left: 24px;
    }

    .category-items label {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      font-weight: normal;
      cursor: pointer;
    }

    .category-items input[type='checkbox'] {
      width: 14px;
      height: 14px;
      accent-color: var(--primary-color, #03a9f4);
    }

    .alarm-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      border: 1px solid var(--divider-color, #e0e0e0);
      border-radius: 4px;
      padding: 12px;
      max-height: 150px;
      overflow-y: auto;
    }

    .alarm-list label {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: normal;
      cursor: pointer;
    }

    .alarm-list input[type='checkbox'] {
      width: 16px;
      height: 16px;
      accent-color: var(--primary-color, #03a9f4);
    }

    .button-row {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      margin-top: 24px;
      padding-top: 16px;
      border-top: 1px solid var(--divider-color, #e0e0e0);
    }

    .button-row button {
      padding: 10px 20px;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.2s;
    }

    .button-row button.cancel {
      background: transparent;
      color: var(--secondary-text-color);
    }

    .button-row button.cancel:hover {
      background: var(--secondary-background-color);
    }

    .button-row button.primary {
      background: var(--primary-color, #03a9f4);
      color: white;
    }

    .button-row button.primary:hover:not(:disabled) {
      background: var(--primary-color-dark, #0288d1);
    }

    .button-row button.primary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .button-row button:focus-visible {
      outline: 2px solid var(--primary-color);
      outline-offset: 2px;
    }

    .loading {
      text-align: center;
      padding: 24px;
      color: var(--secondary-text-color);
    }
  `;

  async connectedCallback() {
    super.connectedCallback();
    await this._loadEntities();
    if (this.action) {
      this._populateForm();
    }
  }

  private async _loadEntities() {
    this._loading = true;
    try {
      const [sensors, alarms] = await Promise.all([
        fetchSensors(this.hass),
        fetchAlarms(this.hass),
      ]);
      this._sensors = sensors;
      this._alarms = alarms;
    } catch (err) {
      console.error('Failed to load entities:', err);
    } finally {
      this._loading = false;
    }
  }

  private _populateForm() {
    if (!this.action) return;
    this._name = this.action.name;
    this._modes = [...this.action.modes];
    this._delaySeconds = this.action.delay_seconds;
    this._selectedSensors = [...this.action.sensor_entity_ids];
    this._selectedAlarms = [...this.action.alarm_entity_ids];
  }

  private _toggleMode(mode: string) {
    if (this._modes.includes(mode)) {
      this._modes = this._modes.filter((m) => m !== mode);
    } else {
      this._modes = [...this._modes, mode];
    }
    this._clearError('modes');
  }

  private _toggleSensor(entityId: string) {
    if (this._selectedSensors.includes(entityId)) {
      this._selectedSensors = this._selectedSensors.filter((s) => s !== entityId);
    } else {
      this._selectedSensors = [...this._selectedSensors, entityId];
    }
    this._clearError('sensors');
  }

  private _toggleAlarm(entityId: string) {
    if (this._selectedAlarms.includes(entityId)) {
      this._selectedAlarms = this._selectedAlarms.filter((a) => a !== entityId);
    } else {
      this._selectedAlarms = [...this._selectedAlarms, entityId];
    }
    this._clearError('alarms');
  }

  private _isCategorySelected(category: SensorCategory): boolean {
    if (!this._sensors) return false;
    const sensors = this._sensors[category] || [];
    if (sensors.length === 0) return false;
    return sensors.every((s) => this._selectedSensors.includes(s.entity_id));
  }

  private _isCategoryPartial(category: SensorCategory): boolean {
    if (!this._sensors) return false;
    const sensors = this._sensors[category] || [];
    if (sensors.length === 0) return false;
    const selected = sensors.filter((s) =>
      this._selectedSensors.includes(s.entity_id)
    );
    return selected.length > 0 && selected.length < sensors.length;
  }

  private _toggleCategory(category: SensorCategory) {
    if (!this._sensors) return;
    const sensors = this._sensors[category] || [];
    const entityIds = sensors.map((s) => s.entity_id);

    if (this._isCategorySelected(category)) {
      // Deselect all in category
      this._selectedSensors = this._selectedSensors.filter(
        (s) => !entityIds.includes(s)
      );
    } else {
      // Select all in category
      const newIds = entityIds.filter((id) => !this._selectedSensors.includes(id));
      this._selectedSensors = [...this._selectedSensors, ...newIds];
    }
    this._clearError('sensors');
  }

  private _clearError(field: string) {
    if (this._errors[field]) {
      const { [field]: _, ...rest } = this._errors;
      this._errors = rest;
    }
  }

  private _validate(): boolean {
    this._errors = {};

    if (!this._name.trim()) {
      this._errors = { ...this._errors, name: 'Name is required' };
    }
    if (this._modes.length === 0) {
      this._errors = { ...this._errors, modes: 'Select at least one mode' };
    }
    if (this._selectedSensors.length === 0) {
      this._errors = { ...this._errors, sensors: 'Select at least one sensor' };
    }
    if (this._selectedAlarms.length === 0) {
      this._errors = { ...this._errors, alarms: 'Select at least one alarm' };
    }

    return Object.keys(this._errors).length === 0;
  }

  private async _handleSave() {
    if (!this._validate()) return;

    this._saving = true;
    try {
      const data = {
        name: this._name.trim(),
        modes: this._modes,
        delay_seconds: this._delaySeconds,
        sensor_entity_ids: this._selectedSensors,
        alarm_entity_ids: this._selectedAlarms,
      };

      if (this.action) {
        await updateAction(this.hass, this.action.id, data);
      } else {
        await createAction(this.hass, data);
      }

      this.dispatchEvent(new CustomEvent('save'));
    } catch (err) {
      console.error('Failed to save action:', err);
      this._errors = {
        ...this._errors,
        form: err instanceof Error ? err.message : 'Failed to save',
      };
    } finally {
      this._saving = false;
    }
  }

  private _handleCancel() {
    this.dispatchEvent(new CustomEvent('cancel'));
  }

  private _handleOverlayClick(e: Event) {
    if (e.target === e.currentTarget) {
      this._handleCancel();
    }
  }

  private _handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      this._handleCancel();
    }
  }

  render() {
    return html`
      <div
        class="editor-overlay"
        @click=${this._handleOverlayClick}
        @keydown=${this._handleKeydown}
      >
        <div class="editor-dialog" role="dialog" aria-modal="true" aria-labelledby="editor-title">
          <h2 id="editor-title">${this.action ? 'Edit Action' : 'New Action'}</h2>

          ${this._loading
            ? html`<div class="loading">Loading...</div>`
            : this._renderForm()}
        </div>
      </div>
    `;
  }

  private _renderForm() {
    return html`
      <div class="form-group">
        <label for="action-name">Name</label>
        <input
          id="action-name"
          type="text"
          .value=${this._name}
          @input=${(e: Event) => {
            this._name = (e.target as HTMLInputElement).value;
            this._clearError('name');
          }}
          class=${this._errors.name ? 'error' : ''}
          placeholder="Enter action name"
        />
        ${this._errors.name
          ? html`<span class="error-text">${this._errors.name}</span>`
          : ''}
      </div>

      <div class="form-group">
        <label>Modes (at least one required)</label>
        <div class="checkbox-group">
          ${['standby', 'home', 'away'].map(
            (mode) => html`
              <label>
                <input
                  type="checkbox"
                  .checked=${this._modes.includes(mode)}
                  @change=${() => this._toggleMode(mode)}
                />
                ${mode.charAt(0).toUpperCase() + mode.slice(1)}
              </label>
            `
          )}
        </div>
        ${this._errors.modes
          ? html`<span class="error-text">${this._errors.modes}</span>`
          : ''}
      </div>

      <div class="form-group">
        <label>Delay before triggering</label>
        <div class="delay-control">
          <input
            type="range"
            min="0"
            max="60"
            .value=${String(this._delaySeconds)}
            @input=${(e: Event) => {
              this._delaySeconds = Number((e.target as HTMLInputElement).value);
            }}
          />
          <span class="delay-value">${this._delaySeconds}s</span>
        </div>
      </div>

      <div class="form-group">
        <label>Sensors (at least one required)</label>
        ${this._renderSensorSelection()}
        ${this._errors.sensors
          ? html`<span class="error-text">${this._errors.sensors}</span>`
          : ''}
      </div>

      <div class="form-group">
        <label>Alarms to trigger (at least one required)</label>
        ${this._renderAlarmSelection()}
        ${this._errors.alarms
          ? html`<span class="error-text">${this._errors.alarms}</span>`
          : ''}
      </div>

      ${this._errors.form
        ? html`<div class="error-text" style="margin-bottom: 16px;">
            ${this._errors.form}
          </div>`
        : ''}

      <div class="button-row">
        <button class="cancel" @click=${this._handleCancel}>Cancel</button>
        <button class="primary" @click=${this._handleSave} ?disabled=${this._saving}>
          ${this._saving ? 'Saving...' : 'Save'}
        </button>
      </div>
    `;
  }

  private _renderSensorSelection() {
    if (!this._sensors) {
      return html`<div class="loading">Loading sensors...</div>`;
    }

    const categories: SensorCategory[] = [
      'door',
      'window',
      'motion',
      'moisture',
      'smoke',
      'connectivity',
      'other',
    ];

    const nonEmptyCategories = categories.filter(
      (cat) => (this._sensors![cat] || []).length > 0
    );

    if (nonEmptyCategories.length === 0) {
      return html`<div class="loading">No sensors available</div>`;
    }

    return html`
      <div class="sensor-categories">
        ${nonEmptyCategories.map((category) => {
          const sensors = this._sensors![category] || [];
          return html`
            <div class="category">
              <div class="category-header" @click=${() => this._toggleCategory(category)}>
                <input
                  type="checkbox"
                  .checked=${this._isCategorySelected(category)}
                  .indeterminate=${this._isCategoryPartial(category)}
                  @click=${(e: Event) => e.stopPropagation()}
                  @change=${() => this._toggleCategory(category)}
                />
                <span>${category} (${sensors.length})</span>
              </div>
              <div class="category-items">
                ${sensors.map(
                  (sensor) => html`
                    <label>
                      <input
                        type="checkbox"
                        .checked=${this._selectedSensors.includes(sensor.entity_id)}
                        @change=${() => this._toggleSensor(sensor.entity_id)}
                      />
                      ${sensor.name}
                    </label>
                  `
                )}
              </div>
            </div>
          `;
        })}
      </div>
    `;
  }

  private _renderAlarmSelection() {
    if (this._alarms.length === 0) {
      return html`<div class="loading">No alarms available</div>`;
    }

    return html`
      <div class="alarm-list">
        ${this._alarms.map(
          (alarm) => html`
            <label>
              <input
                type="checkbox"
                .checked=${this._selectedAlarms.includes(alarm.entity_id)}
                @change=${() => this._toggleAlarm(alarm.entity_id)}
              />
              ${alarm.name}
            </label>
          `
        )}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'abode-action-editor': ActionEditor;
  }
}
