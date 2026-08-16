import { LitElement, html, css, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type {
  HomeAssistant,
  AbodeAction,
  Mode,
  SensorsByCategory,
  SensorEntity,
  AlarmEntity,
} from './types';
import { MODES, getEntityState, isUnavailableState } from './types';
import { fetchSensors, fetchAlarms, createAction, updateAction, wsErrorMessage } from './api';
import './abode-modal';

// "Toggle membership of `value` in a string array" — pure, no `this` access,
// so it lives at module scope rather than as a static method. Returns a new
// array (never mutates input) so Lit picks up the @state change.
function toggleIn<T extends string>(arr: readonly T[], value: T): T[] {
  return arr.includes(value) ? arr.filter((x) => x !== value) : [...arr, value];
}

// Display order for sensor categories (#120). HA `device_class` is open-ended;
// anything not in this list keeps its relative alphabetical order and is
// appended after the prioritized categories so unknown classes still surface.
//
// Camera smart-detect categories (person/vehicle/smoke_alarm/…) come right
// after `motion` — they're the next-most-useful trigger for custom actions
// (#135), and rank above the more niche detector classes.
const SENSOR_CATEGORY_PRIORITY = [
  'door',
  'window',
  'motion',
  'person',
  'vehicle',
  'animal',
  'object',
  'package',
  'face',
  'visitor',
  'smoke_alarm',
  'co_alarm',
  'speaking',
  'barking',
  'baby_cry',
  'glass_break',
  'siren',
  'smoke',
  'gas',
  'carbon_monoxide',
  'moisture',
] as const;
const SENSOR_CATEGORY_RANK = new Map<string, number>(
  SENSOR_CATEGORY_PRIORITY.map((cat, idx) => [cat, idx]),
);
function compareSensorCategories(a: string, b: string): number {
  const ra = SENSOR_CATEGORY_RANK.get(a) ?? Number.MAX_SAFE_INTEGER;
  const rb = SENSOR_CATEGORY_RANK.get(b) ?? Number.MAX_SAFE_INTEGER;
  return ra - rb || a.localeCompare(b);
}

// Per-device-class labels for the "on" / "off" states. "Door open" reads
// natural; "motion on" does not. Anything not in this map falls back to the
// raw on/off — better than guessing wrong for an unfamiliar class.
const STATE_LABELS: Record<string, { on: string; off: string }> = {
  door: { on: 'open', off: 'closed' },
  window: { on: 'open', off: 'closed' },
  garage_door: { on: 'open', off: 'closed' },
  opening: { on: 'open', off: 'closed' },
  motion: { on: 'detected', off: 'clear' },
  occupancy: { on: 'detected', off: 'clear' },
  presence: { on: 'detected', off: 'clear' },
  moisture: { on: 'wet', off: 'dry' },
  smoke: { on: 'detected', off: 'clear' },
  gas: { on: 'detected', off: 'clear' },
  carbon_monoxide: { on: 'detected', off: 'clear' },
  // Camera smart-detect categories (#135). Backend emits these for entities
  // without a device_class — same "detected"/"clear" verbs as motion.
  person: { on: 'detected', off: 'clear' },
  vehicle: { on: 'detected', off: 'clear' },
  animal: { on: 'detected', off: 'clear' },
  object: { on: 'detected', off: 'clear' },
  package: { on: 'detected', off: 'clear' },
  face: { on: 'detected', off: 'clear' },
  visitor: { on: 'detected', off: 'clear' },
  smoke_alarm: { on: 'detected', off: 'clear' },
  co_alarm: { on: 'detected', off: 'clear' },
  speaking: { on: 'detected', off: 'clear' },
  barking: { on: 'detected', off: 'clear' },
  baby_cry: { on: 'detected', off: 'clear' },
  glass_break: { on: 'detected', off: 'clear' },
  siren: { on: 'detected', off: 'clear' },
};

// Human-readable headers for categories that don't read naturally with the
// default underscore→space conversion. "smoke alarm" → "Smoke alarm detected"
// reads better, and matches the labels HA itself shows in the camera card so
// users see the same words in both places (#135). Categories not in this map
// keep the existing fallback (replace underscores, no further capitalization
// beyond CSS).
const CATEGORY_HUMAN_LABELS: Record<string, string> = {
  person: 'Person detected',
  vehicle: 'Vehicle detected',
  animal: 'Animal detected',
  object: 'Object detected',
  package: 'Package detected',
  face: 'Face detected',
  visitor: 'Visitor',
  smoke_alarm: 'Smoke alarm detected',
  co_alarm: 'CO alarm detected',
  speaking: 'Speaking detected',
  barking: 'Barking detected',
  baby_cry: 'Baby cry detected',
  glass_break: 'Glass break detected',
  siren: 'Siren detected',
};

function describeState(state: string, category: string): string {
  if (isUnavailableState(state)) return 'unavailable';
  const labels = STATE_LABELS[category];
  if (!labels) return state;
  if (state === 'on') return labels.on;
  if (state === 'off') return labels.off;
  return state;
}

/**
 * Modal editor for creating or updating an Abode action. Rendered
 * inside an `<abode-modal>` (size="lg"); the parent listens for the
 * `save` and `cancel` events to close it.
 *
 * @fires save   - Dispatched after a successful create or update WS call.
 *                 Detail: undefined. The parent should refresh its list.
 * @fires cancel - Dispatched on the Cancel button, Escape, or overlay
 *                 click (the modal forwards `dismiss` here).
 *
 * @prop {HomeAssistant} hass        - Required.
 * @prop {AbodeAction | null} action - Existing action to edit, or null
 *                                     to start a fresh "create" form.
 */
@customElement('abode-action-editor')
export class ActionEditor extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) action: AbodeAction | null = null;

  @state() private _name = '';
  @state() private _modes: Mode[] = [];
  @state() private _delaySeconds = 0;
  @state() private _selectedSensors: string[] = [];
  @state() private _selectedAlarms: string[] = [];
  @state() private _sensors: SensorsByCategory | null = null;
  @state() private _alarms: AlarmEntity[] = [];
  @state() private _errors: Record<string, string> = {};
  @state() private _saving = false;
  @state() private _loading = true;
  @state() private _loadError: string | null = null;
  // Set when Save is pressed on an action with no alarm selected. The second
  // press goes through. An action named "Call the police" that is silently
  // notification-only is the single most dangerous thing this editor can
  // produce, so it takes an explicit acknowledgement.
  @state() private _confirmNotificationOnly = false;
  // Sensor categories collapse by default to keep the form scannable
  // (#113). Edit mode seeds this with categories that already contain
  // selected sensors so the user can see what they've picked.
  @state() private _expandedCategories: Set<string> = new Set();
  @state() private _sensorSearch = '';

  // Tracks the in-flight _loadEntities call. Aborted on disconnect (so a
  // late-resolving fetch doesn't write state to a detached element) and on
  // Retry (so a slow first attempt doesn't overwrite a fresh successful one).
  // hass.callWS doesn't support cancellation, but the signal lets us discard
  // the *result* once it arrives.
  private _abort: AbortController | null = null;

  static styles = css`
    :host {
      display: block;
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

    .sensor-search {
      width: 100%;
      padding: 8px 12px;
      margin-bottom: 8px;
      border: 1px solid var(--divider-color, #e0e0e0);
      border-radius: 4px;
      font-size: 13px;
      color: var(--primary-text-color);
      background: var(--card-background-color, #fff);
      box-sizing: border-box;
    }

    .sensor-search:focus {
      outline: none;
      border-color: var(--primary-color, #03a9f4);
      box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.2);
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

    .category-header > span {
      flex: 1;
    }

    .category-header input[type='checkbox'] {
      width: 16px;
      height: 16px;
      accent-color: var(--primary-color, #03a9f4);
    }

    .disclosure {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      padding: 0;
      border: none;
      background: transparent;
      color: var(--secondary-text-color, #757575);
      font-size: 12px;
      line-height: 1;
      cursor: pointer;
      transition: transform 0.15s;
    }

    .disclosure[aria-expanded='true'] {
      transform: rotate(90deg);
    }

    .disclosure:focus-visible {
      outline: 2px solid var(--primary-color, #03a9f4);
      outline-offset: 2px;
      border-radius: 2px;
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

    .category-items .entity-area {
      font-size: 12px;
      color: var(--secondary-text-color, #757575);
    }

    /* Row layout: a flex row that puts the info button on the right
     * and the clickable label on the left. The label itself is a CSS
     * grid so name, area, and state pill align in columns across rows
     * like a table. Earlier we tried display:contents on the label to
     * make its children direct grid items of .sensor-row, but
     * Chromium's handling of display:contents on form controls is
     * inconsistent (the label loses its implicit click-forwarding to
     * the wrapped <input> under some conditions), which broke the
     * picker. The current shape is dumber and works.
     *
     * Column widths inside the label grid:
     *   checkbox    auto, minimal
     *   name        1fr,  takes remaining space and ellipsis-truncates
     *   area        minmax(0, auto), fits its content (collapses to 0
     *               on rows without an area so the state pill still
     *               aligns one column over)
     *   state pill  minmax(6.5rem, auto) — "unavailable" doesn't force
     *               ellipsis but a short "open" still column-aligns
     *               with longer labels in adjacent rows
     */
    .sensor-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .sensor-row > label {
      flex: 1;
      min-width: 0;
      display: grid;
      grid-template-columns: auto minmax(0, 1fr) minmax(0, auto) minmax(6.5rem, auto);
      align-items: center;
      column-gap: 12px;
      cursor: pointer;
    }

    .sensor-row.unavailable .entity-name {
      text-decoration: line-through;
      opacity: 0.7;
    }

    .entity-name {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      min-width: 0;
    }

    /* State pill — colored dot plus label. Pulls from HA's CSS variable
     * palette where available so it follows light/dark theming. The
     * leading "·" separator from the area column is dropped now that
     * the area sits in its own grid column. */
    .state-pill {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 11px;
      color: var(--secondary-text-color, #757575);
      white-space: nowrap;
    }

    .state-pill::before {
      content: '';
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: currentColor;
    }

    .state-pill.on {
      color: var(--state-binary_sensor-active-color, var(--warning-color, #ff9800));
    }

    .state-pill.off {
      color: var(--state-binary_sensor-color, var(--success-color, #4caf50));
    }

    .state-pill.unavailable {
      color: var(--error-color, #f44336);
    }

    .state-pill.unavailable::before {
      /* Hide the dot for unavailable rows — the template renders an
       * <ha-icon> (mdi:alert-circle-outline) in its place. */
      display: none;
    }

    .state-pill.unavailable ha-icon {
      --mdc-icon-size: 14px;
    }

    .info-button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      padding: 0;
      border: none;
      background: transparent;
      color: var(--secondary-text-color, #757575);
      cursor: pointer;
      border-radius: 4px;
    }

    .info-button:hover {
      color: var(--primary-text-color);
      background: var(--secondary-background-color, rgba(0, 0, 0, 0.04));
    }

    .info-button:focus-visible {
      outline: 2px solid var(--primary-color, #03a9f4);
      outline-offset: 1px;
    }

    .info-button ha-icon {
      --mdc-icon-size: 18px;
    }

    .category-header .unavailable-count {
      margin-left: 4px;
      font-size: 12px;
      font-weight: normal;
      color: var(--error-color, #f44336);
      text-transform: none;
    }

    /* Responsive grid: ~180px minimum per cell, so the panel auto-fits
     * 2-3 columns on a laptop and falls back to 1 on narrow viewports
     * without a media-query breakpoint. The row gap is tighter than the
     * column gap so columns read as paired up rather than as a single
     * wall of text. */
    /* Sits above the footer buttons and spans the full row so the warning
       reads before the Save button it is guarding. */
    .notify-only-confirm {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      flex: 1 1 100%;
      font-size: 13px;
      line-height: 1.4;
      color: var(--error-color, #db4437);
      background: var(--error-color, #db4437);
      background: color-mix(in srgb, var(--error-color, #db4437) 8%, transparent);
      border: 1px solid var(--error-color, #db4437);
      border-radius: 4px;
      padding: 8px 10px;
      margin-bottom: 8px;
    }

    .notify-only-confirm ha-icon {
      --mdc-icon-size: 18px;
      flex-shrink: 0;
    }

    .alarm-list {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 8px 16px;
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

    .alarm-list input[type='radio'] {
      width: 16px;
      height: 16px;
      accent-color: var(--primary-color, #03a9f4);
    }

    /* Footer button styles — applied to <button slot="footer"> inside <abode-modal>.
     * The selector intentionally matches all slot="footer" buttons in this
     * shadow root, which today only exist inside <abode-modal>. */
    button[slot='footer'] {
      padding: 10px 20px;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.2s;
    }

    button[slot='footer'].cancel {
      background: transparent;
      color: var(--secondary-text-color);
    }

    button[slot='footer'].cancel:hover {
      background: var(--secondary-background-color);
    }

    button[slot='footer'].primary {
      background: var(--primary-color, #03a9f4);
      color: white;
    }

    button[slot='footer'].primary:hover:not(:disabled) {
      background: var(--primary-color-dark, #0288d1);
    }

    button[slot='footer'].primary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    button[slot='footer']:focus-visible {
      outline: 2px solid var(--primary-color);
      outline-offset: 2px;
    }

    .loading {
      text-align: center;
      padding: 24px;
      color: var(--secondary-text-color);
    }

    .retry-row {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
      padding: 32px 24px;
      text-align: center;
    }

    .retry-row .error-text {
      font-size: 14px;
      margin: 0;
    }

    .retry-row button {
      padding: 10px 20px;
      border: none;
      border-radius: 4px;
      background: var(--primary-color, #03a9f4);
      color: white;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.2s;
    }

    .retry-row button:hover {
      background: var(--primary-color-dark, #0288d1);
    }

    .retry-row button:focus-visible {
      outline: 2px solid var(--primary-color, #03a9f4);
      outline-offset: 2px;
    }
  `;

  async connectedCallback() {
    super.connectedCallback();
    // Each open must re-ask for confirmation. Today the parent conditionally
    // renders this element so lit recreates it every time and the field
    // initializer would suffice, but resetting here keeps the guard correct
    // if that ever becomes a persistent element toggled by an attribute.
    this._confirmNotificationOnly = false;
    // Populate from `this.action` synchronously *before* the async load so a
    // disconnect mid-fetch can't mutate _name/_modes/etc. on a detached
    // element. _populateForm only depends on the `action` prop, not on the
    // sensors/alarms being loaded, so it's safe to run first.
    if (this.action) {
      this._populateForm();
    }
    await this._loadEntities();
  }

  disconnectedCallback() {
    this._abort?.abort();
    this._abort = null;
    super.disconnectedCallback();
  }

  private async _loadEntities() {
    // Cancel any prior in-flight load so its late result can't overwrite
    // a fresher one (covers Retry-while-still-loading and reconnects).
    this._abort?.abort();
    const controller = new AbortController();
    this._abort = controller;
    const { signal } = controller;

    this._loading = true;
    this._loadError = null;
    try {
      const [sensors, alarms] = await Promise.all([
        fetchSensors(this.hass),
        fetchAlarms(this.hass),
      ]);
      if (signal.aborted) return;
      this._sensors = sensors;
      this._alarms = alarms;
      // Editing an action: auto-expand categories that contain at least
      // one already-selected sensor so the user can immediately see and
      // adjust their existing picks (#113). New actions stay fully
      // collapsed; user-initiated expansions later override this.
      if (this.action && this._selectedSensors.length > 0) {
        const seeded = new Set<string>();
        for (const [cat, list] of Object.entries(sensors)) {
          if ((list ?? []).some((s) => this._selectedSensors.includes(s.entity_id))) {
            seeded.add(cat);
          }
        }
        this._expandedCategories = seeded;
      }
    } catch (err) {
      if (signal.aborted) return;
      this._loadError = err instanceof Error ? err.message : 'Failed to load sensors and alarms';
    } finally {
      if (!signal.aborted) this._loading = false;
    }
  }

  private _populateForm() {
    if (!this.action) return;
    this._name = this.action.name;
    this._modes = [...this.action.modes];
    this._delaySeconds = this.action.delay_seconds;
    this._selectedSensors = [...this.action.sensor_entity_ids];
    // Single-select for alarms now. Backend still accepts an array
    // and existing storage may legitimately hold >1 alarm from before
    // the UI restriction (the Abode timeline only meaningfully fires
    // one alarm at a time anyway). Show the first one as selected;
    // on save we persist only that one — a lazy migration on edit.
    this._selectedAlarms = this.action.alarm_entity_ids.slice(0, 1);
  }

  private _toggleMode(mode: Mode) {
    this._modes = toggleIn(this._modes, mode);
    this._clearError('modes');
  }

  private _toggleSensor(entityId: string) {
    this._selectedSensors = toggleIn(this._selectedSensors, entityId);
    this._clearError('sensors');
  }

  // Fires HA's standard "open more-info dialog" event. `composed: true` is
  // required to escape this panel's shadow DOM; HA's root listener picks
  // it up and routes through ha-more-info-dialog. `stopPropagation` is
  // defensive — the button is a sibling of the row's `<label>`, so a
  // click landing on the button itself can't toggle the checkbox today,
  // but if a future refactor wraps the row in a wider click handler we
  // don't want "inspect this sensor" to also select it.
  private _openMoreInfo(entityId: string, e: Event) {
    e.stopPropagation();
    this.dispatchEvent(
      new CustomEvent('hass-more-info', {
        detail: { entityId },
        bubbles: true,
        composed: true,
      }),
    );
  }

  // Single-select replacement for the old toggle. Stays on the
  // `_selectedAlarms: string[]` shape (length 0 or 1) so the save
  // payload still matches the existing `alarm_entity_ids: string[]`
  // schema — no backend migration needed.
  private _selectAlarm(entityId: string) {
    this._selectedAlarms = [entityId];
    this._clearError('alarms');
  }

  // Notification-only mode — clears the alarm selection. Saves with
  // alarm_entity_ids=[] so _execute_action skips switch.turn_on and just
  // fires the abode_security.action_triggered event.
  private _clearAlarmSelection() {
    this._selectedAlarms = [];
    // Re-arm the confirmation: switching back to notification-only after
    // having picked an alarm is exactly the change worth double-checking.
    this._confirmNotificationOnly = false;
    this._clearError('alarms');
  }

  // Category keys are open-ended (HA `device_class`), so these helpers work
  // off plain `string` rather than the closed `SensorCategory` literal union.
  //
  // `subset` lets the search filter (#113) restrict the tri-state and
  // select-all to the *visible* sensors. Without it, clicking a header
  // while filtering would silently bulk-select hidden items too.
  private _isCategorySelected(category: string, subset?: readonly SensorEntity[]): boolean {
    if (!this._sensors) return false;
    const sensors = subset ?? this._sensors[category] ?? [];
    if (sensors.length === 0) return false;
    return sensors.every((s) => this._selectedSensors.includes(s.entity_id));
  }

  private _isCategoryPartial(category: string, subset?: readonly SensorEntity[]): boolean {
    if (!this._sensors) return false;
    const sensors = subset ?? this._sensors[category] ?? [];
    if (sensors.length === 0) return false;
    const selected = sensors.filter((s) => this._selectedSensors.includes(s.entity_id));
    return selected.length > 0 && selected.length < sensors.length;
  }

  private _toggleCategory(category: string, subset?: readonly SensorEntity[]) {
    if (!this._sensors) return;
    const sensors = subset ?? this._sensors[category] ?? [];
    const entityIds = sensors.map((s) => s.entity_id);

    if (this._isCategorySelected(category, sensors)) {
      // Deselect every visible sensor in this category.
      this._selectedSensors = this._selectedSensors.filter((s) => !entityIds.includes(s));
    } else {
      // Select every visible sensor in this category.
      const newIds = entityIds.filter((id) => !this._selectedSensors.includes(id));
      this._selectedSensors = [...this._selectedSensors, ...newIds];
    }
    this._clearError('sensors');
  }

  // Reassigning a fresh Set (not in-place mutation) is required for Lit's
  // identity-based dirty check to re-render.
  private _toggleCategoryExpanded(category: string) {
    const next = new Set(this._expandedCategories);
    if (next.has(category)) {
      next.delete(category);
    } else {
      next.add(category);
    }
    this._expandedCategories = next;
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
    // Alarm is intentionally optional: an empty selection means
    // "notification-only" — the trigger event fires without arming any switch.

    return Object.keys(this._errors).length === 0;
  }

  private async _handleSave() {
    // The Save button's `?disabled=${this._saving}` only reflects on the
    // next render — a fast double-click can fire two handlers before that
    // cycle completes. Guard inside the handler too so the second call is
    // a no-op (closes #27).
    if (this._saving) return;
    if (!this._validate()) return;

    // Notification-only is a legitimate configuration, but it must be a
    // deliberate one: confirm before the first save, then remember the
    // acknowledgement for this editing session.
    if (this._selectedAlarms.length === 0 && !this._confirmNotificationOnly) {
      this._confirmNotificationOnly = true;
      return;
    }

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
        // Not `instanceof Error`: the backend's `validation_error` message —
        // "…is a BURGLAR alarm, which Abode refuses to raise on request" —
        // arrives as a plain `{ code, message }` object and would otherwise
        // be replaced by the generic fallback.
        form: wsErrorMessage(err, 'Failed to save'),
      };
    } finally {
      this._saving = false;
    }
  }

  private _handleCancel() {
    this.dispatchEvent(new CustomEvent('cancel'));
  }

  render() {
    return html`
      <abode-modal
        heading=${this.action ? 'Edit Action' : 'New Action'}
        size="lg"
        @dismiss=${this._handleCancel}
      >
        ${this._loading
          ? html`<div class="loading">Loading...</div>`
          : this._loadError
            ? this._renderLoadError()
            : this._renderFormBody()}
        ${this._loading || this._loadError ? '' : this._renderFooter()}
      </abode-modal>
    `;
  }

  private _renderLoadError() {
    // type="button" defends against a future refactor wrapping the modal body
    // in a <form> — without it, the button would default to type="submit".
    return html`
      <div class="retry-row" role="alert">
        <span class="error-text">${this._loadError}</span>
        <button type="button" @click=${this._loadEntities}>Retry</button>
      </div>
    `;
  }

  private _renderFormBody() {
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
        ${this._errors.name ? html`<span class="error-text">${this._errors.name}</span>` : ''}
      </div>

      <div class="form-group">
        <label>Modes (at least one required)</label>
        <div class="checkbox-group">
          ${MODES.map(
            (mode) => html`
              <label>
                <input
                  type="checkbox"
                  .checked=${this._modes.includes(mode)}
                  @change=${() => this._toggleMode(mode)}
                />
                ${mode.charAt(0).toUpperCase() + mode.slice(1)}
              </label>
            `,
          )}
        </div>
        ${this._errors.modes ? html`<span class="error-text">${this._errors.modes}</span>` : ''}
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
        ${this._errors.sensors ? html`<span class="error-text">${this._errors.sensors}</span>` : ''}
      </div>

      <div class="form-group">
        <label>Alarm to trigger (optional)</label>
        ${this._renderAlarmSelection()}
        ${this._errors.alarms ? html`<span class="error-text">${this._errors.alarms}</span>` : ''}
      </div>

      ${this._errors.form
        ? html`<div class="error-text" style="margin-bottom: 16px;">${this._errors.form}</div>`
        : ''}
    `;
  }

  private _renderFooter() {
    const needsConfirm = this._confirmNotificationOnly && this._selectedAlarms.length === 0;
    return html`
      ${needsConfirm
        ? html`
            <div slot="footer" class="notify-only-confirm" role="alert">
              <ha-icon icon="mdi:alert" aria-hidden="true"></ha-icon>
              <span>
                No alarm selected — this action will only send a notification. It will
                <strong>not</strong> raise an alarm or contact your monitoring service. Press Save
                again to confirm.
              </span>
            </div>
          `
        : ''}
      <button slot="footer" class="cancel" @click=${this._handleCancel}>Cancel</button>
      <button slot="footer" class="primary" @click=${this._handleSave} ?disabled=${this._saving}>
        ${this._saving ? 'Saving...' : needsConfirm ? 'Save anyway' : 'Save'}
      </button>
    `;
  }

  private _renderSensorSelection() {
    const sensorsByCategory = this._sensors;
    if (!sensorsByCategory) {
      return html`<div class="loading">Loading sensors...</div>`;
    }

    // Drive categories from the response keys, not a frontend allowlist —
    // the backend keys by HA `device_class`, which is open-ended.
    // Order by usefulness (door/window/motion/smoke/…) instead of plain
    // alphabetical so the most commonly used categories surface first (#120).
    const nonEmptyCategories = Object.keys(sensorsByCategory)
      .filter((cat) => (sensorsByCategory[cat] ?? []).length > 0)
      .sort(compareSensorCategories);

    if (nonEmptyCategories.length === 0) {
      return html`<div class="loading">No sensors available</div>`;
    }

    const query = this._sensorSearch.trim().toLowerCase();
    const isFiltering = query.length > 0;

    // Precompute the filtered subset once per category so the header
    // count, items render, and select-all helpers all agree on what the
    // user can actually see. Also partition the filtered list so
    // unavailable sensors sort to the bottom (and are visually dimmed in
    // the row template) — picking a dead sensor was exactly the trap the
    // "Home Test" bug hit.
    // Same predicate the pill, header count, and actions-tab badge all
    // use — `unknown` is dead too, since the backend trigger filter
    // rejects any transition that isn't a clean off → on.
    const isDead = (s: SensorEntity): boolean =>
      isUnavailableState(getEntityState(this.hass, s.entity_id, s.state));
    const renderedCategories = nonEmptyCategories
      .map((category) => {
        const sensors = sensorsByCategory[category] ?? [];
        const filtered = isFiltering
          ? sensors.filter((s) => s.name.toLowerCase().includes(query))
          : sensors;
        // Stable partition preserves the backend's intra-group order
        // (alphabetical by friendly_name) within each half.
        const live = filtered.filter((s) => !isDead(s));
        const dead = filtered.filter((s) => isDead(s));
        const ordered = [...live, ...dead];
        const unavailableTotal = sensors.filter(isDead).length;
        return { category, sensors, filtered, ordered, unavailableTotal };
      })
      .filter(({ filtered }) => !isFiltering || filtered.length > 0);

    const searchInput = html`
      <input
        type="search"
        class="sensor-search"
        aria-label="Search sensors"
        placeholder="Search sensors…"
        autocomplete="off"
        spellcheck="false"
        .value=${this._sensorSearch}
        @input=${(e: Event) => {
          this._sensorSearch = (e.target as HTMLInputElement).value;
        }}
      />
    `;

    if (renderedCategories.length === 0) {
      return html`
        ${searchInput}
        <div class="loading">No sensors match “${this._sensorSearch}”</div>
      `;
    }

    return html`
      ${searchInput}
      <div class="sensor-categories">
        ${renderedCategories.map(
          ({ category, sensors, filtered, ordered, unavailableTotal }, index) => {
            // SensorsByCategory is keyed by `string`, so a backend key with
            // whitespace or other non-token characters would silently break
            // `aria-controls` (parsed as multiple ids) and produce an
            // invalid DOM id. Normalize defensively, and prefix with the
            // render index so two keys that sanitize to the same value
            // (e.g. "smoke detector" and "smoke-detector") still produce
            // unique ids.
            const safeKey = category.replace(/[^A-Za-z0-9_-]/g, '-');
            const itemsId = `sensor-cat-${index}-${safeKey}`;
            // Human-readable label used for both the visible header text
            // and the accessible name on the disclosure button so a
            // screen-reader announcement matches what sighted users see.
            // Categories the backend emits as semantic keys (#135) get a
            // curated label from CATEGORY_HUMAN_LABELS; everything else
            // falls back to the underscore-to-space conversion.
            const humanLabel = CATEGORY_HUMAN_LABELS[category] ?? category.replace(/_/g, ' ');
            // While filtering, force-expand matched categories so search
            // results aren't hidden behind a collapse the user can't see.
            const isExpanded = isFiltering || this._expandedCategories.has(category);
            const countLabel =
              filtered.length === sensors.length
                ? `(${sensors.length})`
                : `(${filtered.length}/${sensors.length})`;
            // Only show "K unavailable" when there's something to flag. The
            // count is over the *full* category (not the filter result) so
            // the user sees the same dead-sensor count whether or not they
            // typed a search query. The leading space is rendered as a
            // sibling text node rather than inside the red span — putting
            // it inside the span made the separator look like noise.
            const unavailableLabel =
              unavailableTotal > 0
                ? html` <span class="unavailable-count">${unavailableTotal} unavailable</span>`
                : nothing;
            return html`
              <div class="category">
                <div
                  class="category-header"
                  @click=${() => this._toggleCategory(category, filtered)}
                >
                  <input
                    type="checkbox"
                    .checked=${this._isCategorySelected(category, filtered)}
                    .indeterminate=${this._isCategoryPartial(category, filtered)}
                    @click=${(e: Event) => e.stopPropagation()}
                    @change=${() => this._toggleCategory(category, filtered)}
                  />
                  <span>${humanLabel} ${countLabel}${unavailableLabel}</span>
                  ${isFiltering
                    ? // Search has total control of expansion while active;
                      // rendering the chevron would let it accept clicks
                      // that silently mutate _expandedCategories without
                      // any visible effect, leaving the post-clear collapse
                      // state out of sync with what the user saw.
                      null
                    : html`
                        <button
                          type="button"
                          class="disclosure"
                          aria-expanded=${isExpanded ? 'true' : 'false'}
                          aria-controls=${isExpanded ? itemsId : nothing}
                          aria-label=${isExpanded
                            ? `Collapse ${humanLabel}`
                            : `Expand ${humanLabel}`}
                          @click=${(e: Event) => {
                            // The header itself handles select-all on click,
                            // so the disclosure must not bubble up —
                            // otherwise a user trying to peek inside would
                            // toggle their whole-category selection by
                            // accident.
                            e.stopPropagation();
                            this._toggleCategoryExpanded(category);
                          }}
                        >
                          <span aria-hidden="true">▸</span>
                        </button>
                      `}
                </div>
                ${isExpanded
                  ? html`
                      <div id=${itemsId} class="category-items">
                        ${ordered.map((sensor) => this._renderSensorRow(sensor, category))}
                      </div>
                    `
                  : null}
              </div>
            `;
          },
        )}
      </div>
    `;
  }

  private _renderSensorRow(sensor: SensorEntity, category: string) {
    // Pull from live hass.states so the pill updates when a sensor changes
    // without re-fetching. Falls back to the snapshot value from the WS
    // response so first-paint is correct in test harnesses and during the
    // brief window before HA's first state push.
    const state = getEntityState(this.hass, sensor.entity_id, sensor.state);
    const isUnavailable = isUnavailableState(state);
    const pillClass = isUnavailable ? 'unavailable' : state === 'on' ? 'on' : 'off';
    const pillLabel = describeState(state, category);
    return html`
      <div class="sensor-row ${isUnavailable ? 'unavailable' : ''}">
        <label>
          <input
            type="checkbox"
            .checked=${this._selectedSensors.includes(sensor.entity_id)}
            @change=${() => this._toggleSensor(sensor.entity_id)}
          />
          <span class="entity-name">${sensor.name}</span>
          <!-- Area column always rendered (even when empty) so the
               state-pill column lines up across rows that do and don't
               have an area assigned. Empty cells get aria-hidden="true"
               so screen readers skip them — the cell exists only for
               layout, not for semantics. ARIA attributes are enumerated
               (string "true"/"false"), not HTML boolean attributes, so
               we set the value explicitly when needed and omit the
               attribute entirely via Lit's nothing sentinel otherwise. -->
          <span class="entity-area" aria-hidden=${!sensor.area ? 'true' : nothing}>
            ${sensor.area ?? nothing}
          </span>
          <span class="state-pill ${pillClass}" aria-label="${sensor.name} state: ${pillLabel}">
            ${isUnavailable
              ? html`<ha-icon icon="mdi:alert-circle-outline" aria-hidden="true"></ha-icon>`
              : nothing}
            ${pillLabel}
          </span>
        </label>
        <button
          type="button"
          class="info-button"
          aria-label="More info for ${sensor.name}"
          title="More info"
          @click=${(e: Event) => this._openMoreInfo(sensor.entity_id, e)}
        >
          <ha-icon icon="mdi:information-outline"></ha-icon>
        </button>
      </div>
    `;
  }

  private _renderAlarmSelection() {
    if (this._alarms.length === 0) {
      return html`<div class="loading">No alarms available</div>`;
    }

    // Strip the redundant "Abode Alarm" prefix HA produces from device-scoped
    // friendly_names ("Abode Alarm CO Alarm" → "CO Alarm") and sort by the
    // resulting display label (#120). `entity_id` is left untouched so save
    // payloads are unaffected.
    const displayAlarms = this._alarms
      .map((alarm) => ({
        entity_id: alarm.entity_id,
        label: alarm.name.replace(/^Abode Alarm\s+/i, ''),
      }))
      .sort((a, b) => a.label.localeCompare(b.label));

    // Radios sharing the same `name` get native single-select
    // behaviour from the browser — selecting one auto-deselects the
    // others, so we don't need to track "previous selection" in JS.
    // The name is local to this shadow root so it won't collide with
    // anything in the host document.
    return html`
      <div class="alarm-list" role="radiogroup" aria-label="Alarm to trigger">
        <label>
          <input
            type="radio"
            name="abode-action-alarm"
            value=""
            .checked=${this._selectedAlarms.length === 0}
            @change=${() => this._clearAlarmSelection()}
          />
          None (notification only)
        </label>
        ${displayAlarms.map(
          (alarm) => html`
            <label>
              <input
                type="radio"
                name="abode-action-alarm"
                value=${alarm.entity_id}
                .checked=${this._selectedAlarms.includes(alarm.entity_id)}
                @change=${() => this._selectAlarm(alarm.entity_id)}
              />
              ${alarm.label}
            </label>
          `,
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
