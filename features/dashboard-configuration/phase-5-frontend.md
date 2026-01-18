---
status: pending
phase: 5
title: Frontend UI
---

# Phase 5: Frontend UI

## Overview

Build the Lit-based frontend panel with tabs for Modes and Actions, including the action editor form.

## Files to Create/Modify

- **Modify:** `frontend/src/abode-panel.ts` (expand existing shell)
- **Modify:** `frontend/src/types.ts` (add type definitions)
- **Create:** `frontend/src/modes-tab.ts`
- **Create:** `frontend/src/actions-tab.ts`
- **Create:** `frontend/src/action-editor.ts`

## Sub-Phase A: Types and WebSocket Helpers

### Tasks

- [ ] Update `frontend/src/types.ts` with all data types:

```typescript
export interface AbodeAction {
  id: string;
  name: string;
  modes: string[];
  sensor_entity_ids: string[];
  alarm_entity_ids: string[];
  enabled: boolean;
  delay_seconds: number;
  last_triggered: string | null;
  trigger_count: number;
}

export interface AbodeMode {
  id: string;
  name: string;
  icon: string;
  action_count: number;
  active: boolean;
}

export interface SensorEntity {
  entity_id: string;
  name: string;
  state: string;
}

export interface SensorsByCategory {
  door: SensorEntity[];
  window: SensorEntity[];
  motion: SensorEntity[];
  moisture: SensorEntity[];
  smoke: SensorEntity[];
  connectivity: SensorEntity[];
  other: SensorEntity[];
}

export interface AlarmEntity {
  entity_id: string;
  name: string;
  type: string;
}

export interface AbodeConfig {
  debounce_seconds: number;
}
```

- [ ] Create WebSocket helper functions in `abode-panel.ts` or separate file:

```typescript
async function fetchActions(hass: HomeAssistant): Promise<AbodeAction[]>
async function fetchModes(hass: HomeAssistant): Promise<AbodeMode[]>
async function fetchSensors(hass: HomeAssistant): Promise<SensorsByCategory>
async function fetchAlarms(hass: HomeAssistant): Promise<AlarmEntity[]>
async function createAction(hass: HomeAssistant, data: Partial<AbodeAction>): Promise<AbodeAction>
async function updateAction(hass: HomeAssistant, id: string, data: Partial<AbodeAction>): Promise<AbodeAction>
async function deleteAction(hass: HomeAssistant, id: string): Promise<void>
async function testAction(hass: HomeAssistant, id: string): Promise<void>
```

---

## Sub-Phase B: Main Panel with Tabs

### Tasks

- [ ] Expand `abode-panel.ts` to include tab navigation:
  - Tab bar with "Modes" and "Actions" tabs
  - Track active tab in component state
  - Render appropriate tab content

- [ ] Add HA WebSocket connection:
  - Access `hass` object from panel config
  - Use `hass.callWS()` for WebSocket commands

- [ ] Basic styling:
  - Use HA CSS variables for consistent theming
  - Tab bar styling
  - Content area padding

### Component Structure

```typescript
@customElement('abode-configuration-panel')
export class AbodeConfigurationPanel extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @state() private _activeTab: 'modes' | 'actions' = 'actions';
  @state() private _loading = true;
  @state() private _error: string | null = null;

  render() {
    return html`
      <div class="panel-content">
        <div class="header">
          <h1>Abode Configuration</h1>
        </div>
        <div class="tab-bar">
          <button
            class=${this._activeTab === 'modes' ? 'active' : ''}
            @click=${() => this._activeTab = 'modes'}
          >Modes</button>
          <button
            class=${this._activeTab === 'actions' ? 'active' : ''}
            @click=${() => this._activeTab = 'actions'}
          >Actions</button>
        </div>
        <div class="tab-content">
          ${this._loading ? html`<div class="loading">Loading...</div>` : ''}
          ${this._error ? html`<div class="error">${this._error}</div>` : ''}
          ${this._activeTab === 'modes'
            ? html`<abode-modes-tab .hass=${this.hass}></abode-modes-tab>`
            : html`<abode-actions-tab .hass=${this.hass}></abode-actions-tab>`
          }
        </div>
      </div>
    `;
  }
}
```

---

## Sub-Phase C: Modes Tab

### Tasks

- [ ] Create `modes-tab.ts` component:
  - Fetch modes on load
  - Display 3 mode cards (standby, home, away)
  - Show active indicator on current mode
  - Show action count per mode
  - List action names under each mode

### Component Structure

```typescript
@customElement('abode-modes-tab')
export class ModesTab extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @state() private _modes: AbodeMode[] = [];
  @state() private _actions: AbodeAction[] = [];
  @state() private _loading = true;

  async connectedCallback() {
    super.connectedCallback();
    await this._loadData();
  }

  render() {
    return html`
      <div class="modes-grid">
        ${this._modes.map(mode => html`
          <div class="mode-card ${mode.active ? 'active' : ''}">
            <ha-icon icon="${mode.icon}"></ha-icon>
            <h3>${mode.name}</h3>
            <span class="badge">${mode.action_count} actions</span>
            ${mode.active ? html`<span class="active-badge">Active</span>` : ''}
            <ul class="action-list">
              ${this._getActionsForMode(mode.id).map(a => html`<li>${a.name}</li>`)}
            </ul>
          </div>
        `)}
      </div>
    `;
  }
}
```

---

## Sub-Phase D: Actions Tab

### Tasks

- [ ] Create `actions-tab.ts` component:
  - Fetch actions on load
  - Display list of all actions
  - Each row shows: name, modes (chips), enabled toggle, edit/delete/test buttons
  - "Add Action" button at top

- [ ] Implement action toggle:
  - Call `updateAction` with `enabled: !current`
  - Show loading state on toggle

- [ ] Implement delete:
  - Confirmation dialog before delete
  - Call `deleteAction`
  - Remove from local list

- [ ] Implement test:
  - Show confirmation dialog: "This will trigger real alarms. Continue?"
  - On confirm: Call `testAction`
  - Show toast notification on success/failure

- [ ] Implement delete confirmation:
  - Show confirmation dialog: "Delete action '{name}'?"
  - On confirm: Call `deleteAction`

- [ ] Wire up edit/add to open action editor

### Component Structure

```typescript
@customElement('abode-actions-tab')
export class ActionsTab extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @state() private _actions: AbodeAction[] = [];
  @state() private _editingAction: AbodeAction | null = null;
  @state() private _showEditor = false;
  @state() private _showDeleteConfirm = false;
  @state() private _showTestConfirm = false;
  @state() private _pendingAction: AbodeAction | null = null;

  render() {
    return html`
      <div class="actions-header">
        <button @click=${this._addAction}>
          <ha-icon icon="mdi:plus"></ha-icon>
          Add Action
        </button>
      </div>

      ${this._actions.length === 0
        ? html`<div class="empty-state">No actions configured</div>`
        : html`
          <div class="actions-list">
            ${this._actions.map(action => html`
              <div class="action-row">
                <div class="action-info">
                  <span class="name">${action.name}</span>
                  <div class="modes">
                    ${action.modes.map(m => html`<span class="chip">${m}</span>`)}
                  </div>
                </div>
                <div class="action-controls">
                  <ha-switch
                    .checked=${action.enabled}
                    @change=${() => this._toggleAction(action)}
                  ></ha-switch>
                  <ha-icon-button
                    icon="mdi:play"
                    @click=${() => this._testAction(action)}
                    title="Test"
                  ></ha-icon-button>
                  <ha-icon-button
                    icon="mdi:pencil"
                    @click=${() => this._editAction(action)}
                    title="Edit"
                  ></ha-icon-button>
                  <ha-icon-button
                    icon="mdi:delete"
                    @click=${() => this._deleteAction(action)}
                    title="Delete"
                  ></ha-icon-button>
                </div>
              </div>
            `)}
          </div>
        `
      }

      <!-- Recent Triggers Section -->
      <div class="recent-triggers">
        <h3>Recent Triggers</h3>
        ${this._getRecentTriggers().map(action => html`
          <div class="trigger-item">
            <span class="trigger-name">${action.name}</span>
            <span class="trigger-time">${this._formatTime(action.last_triggered)}</span>
          </div>
        `)}
        ${this._getRecentTriggers().length === 0 ? html`
          <div class="empty-state">No recent triggers</div>
        ` : ''}
      </div>

      ${this._showEditor ? html`
        <abode-action-editor
          .hass=${this.hass}
          .action=${this._editingAction}
          @save=${this._handleSave}
          @cancel=${this._closeEditor}
        ></abode-action-editor>
      ` : ''}

      ${this._showDeleteConfirm ? html`
        <ha-dialog open @closed=${() => this._showDeleteConfirm = false}>
          <span slot="heading">Delete Action</span>
          <p>Delete action "${this._pendingAction?.name}"? This cannot be undone.</p>
          <ha-button slot="secondaryAction" @click=${() => this._showDeleteConfirm = false}>
            Cancel
          </ha-button>
          <ha-button slot="primaryAction" @click=${this._confirmDelete}>
            Delete
          </ha-button>
        </ha-dialog>
      ` : ''}

      ${this._showTestConfirm ? html`
        <ha-dialog open @closed=${() => this._showTestConfirm = false}>
          <span slot="heading">Test Action</span>
          <p>This will trigger real alarms. Are you sure you want to test "${this._pendingAction?.name}"?</p>
          <ha-button slot="secondaryAction" @click=${() => this._showTestConfirm = false}>
            Cancel
          </ha-button>
          <ha-button slot="primaryAction" @click=${this._confirmTest}>
            Test
          </ha-button>
        </ha-dialog>
      ` : ''}
    `;
  }

  private _getRecentTriggers(): AbodeAction[] {
    return this._actions
      .filter(a => a.last_triggered)
      .sort((a, b) => new Date(b.last_triggered!).getTime() - new Date(a.last_triggered!).getTime())
      .slice(0, 5);
  }
}
```

---

## Sub-Phase E: Action Editor

### Tasks

- [ ] Create `action-editor.ts` component:
  - Modal/dialog overlay
  - Form fields:
    - Name input (required)
    - Modes checkboxes (at least one required)
    - Delay slider/input (0-60 seconds)
    - Sensor selection (grouped by category)
    - Alarm selection (checkboxes)
  - Save/Cancel buttons

- [ ] Fetch sensors and alarms on open

- [ ] Implement form validation:
  - Name not empty
  - At least one mode selected
  - At least one sensor selected
  - At least one alarm selected
  - Show validation errors inline

- [ ] Handle save:
  - If editing existing action, call `updateAction`
  - If creating new action, call `createAction`
  - Close editor on success
  - Show error toast on failure

### Component Structure

```typescript
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

  async connectedCallback() {
    super.connectedCallback();
    await this._loadEntities();
    if (this.action) {
      this._populateForm();
    }
  }

  render() {
    return html`
      <div class="editor-overlay" @click=${this._handleOverlayClick}>
        <div class="editor-dialog">
          <h2>${this.action ? 'Edit Action' : 'New Action'}</h2>

          <div class="form-group">
            <label>Name</label>
            <input
              type="text"
              .value=${this._name}
              @input=${(e: Event) => this._name = (e.target as HTMLInputElement).value}
              class=${this._errors.name ? 'error' : ''}
            />
            ${this._errors.name ? html`<span class="error-text">${this._errors.name}</span>` : ''}
          </div>

          <div class="form-group">
            <label>Modes (at least one required)</label>
            <div class="checkbox-group">
              ${['standby', 'home', 'away'].map(mode => html`
                <label>
                  <input
                    type="checkbox"
                    .checked=${this._modes.includes(mode)}
                    @change=${() => this._toggleMode(mode)}
                  />
                  ${mode.charAt(0).toUpperCase() + mode.slice(1)}
                </label>
              `)}
            </div>
            ${this._errors.modes ? html`<span class="error-text">${this._errors.modes}</span>` : ''}
          </div>

          <div class="form-group">
            <label>Delay (seconds): ${this._delaySeconds}</label>
            <input
              type="range"
              min="0"
              max="60"
              .value=${String(this._delaySeconds)}
              @input=${(e: Event) => this._delaySeconds = Number((e.target as HTMLInputElement).value)}
            />
          </div>

          <div class="form-group">
            <label>Sensors</label>
            ${this._renderSensorSelection()}
            ${this._errors.sensors ? html`<span class="error-text">${this._errors.sensors}</span>` : ''}
          </div>

          <div class="form-group">
            <label>Alarms to trigger</label>
            ${this._renderAlarmSelection()}
            ${this._errors.alarms ? html`<span class="error-text">${this._errors.alarms}</span>` : ''}
          </div>

          <div class="button-row">
            <button @click=${this._handleCancel}>Cancel</button>
            <button class="primary" @click=${this._handleSave} ?disabled=${this._saving}>
              ${this._saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    `;
  }

  private _renderSensorSelection() {
    if (!this._sensors) return html`<div class="loading">Loading sensors...</div>`;

    const categories = ['door', 'window', 'motion', 'moisture', 'smoke', 'connectivity', 'other'];
    return html`
      <div class="sensor-categories">
        ${categories.map(category => {
          const sensors = this._sensors![category as keyof SensorsByCategory] || [];
          if (sensors.length === 0) return '';
          return html`
            <div class="category">
              <div class="category-header">
                <input
                  type="checkbox"
                  @change=${() => this._toggleCategory(category)}
                  .checked=${this._isCategorySelected(category)}
                />
                <span>${category} (${sensors.length})</span>
              </div>
              <div class="category-items">
                ${sensors.map(sensor => html`
                  <label>
                    <input
                      type="checkbox"
                      .checked=${this._selectedSensors.includes(sensor.entity_id)}
                      @change=${() => this._toggleSensor(sensor.entity_id)}
                    />
                    ${sensor.name}
                  </label>
                `)}
              </div>
            </div>
          `;
        })}
      </div>
    `;
  }

  private _renderAlarmSelection() {
    if (this._alarms.length === 0) return html`<div class="loading">Loading alarms...</div>`;

    return html`
      <div class="alarm-list">
        ${this._alarms.map(alarm => html`
          <label>
            <input
              type="checkbox"
              .checked=${this._selectedAlarms.includes(alarm.entity_id)}
              @change=${() => this._toggleAlarm(alarm.entity_id)}
            />
            ${alarm.name}
          </label>
        `)}
      </div>
    `;
  }

  private _validate(): boolean {
    this._errors = {};

    if (!this._name.trim()) {
      this._errors.name = 'Name is required';
    }
    if (this._modes.length === 0) {
      this._errors.modes = 'Select at least one mode';
    }
    if (this._selectedSensors.length === 0) {
      this._errors.sensors = 'Select at least one sensor';
    }
    if (this._selectedAlarms.length === 0) {
      this._errors.alarms = 'Select at least one alarm';
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
    } catch (error) {
      // Show error toast
      console.error('Failed to save action:', error);
    } finally {
      this._saving = false;
    }
  }
}
```

---

## Sub-Phase F: Accessibility

### Tasks

- [ ] Add proper ARIA labels to all interactive elements
- [ ] Implement keyboard navigation:
  - Tab through action list items
  - Enter/Space to toggle, edit
  - Escape to close dialogs/editor
- [ ] Add focus management:
  - Focus first field when editor opens
  - Return focus to trigger element when dialog closes
- [ ] Ensure color contrast meets WCAG 2.1 AA standards

---

## Sub-Phase G: Build and Test

### Tasks

- [ ] Ensure all components import correctly
- [ ] Run `npm run build` in frontend directory
- [ ] Verify `custom_components/abode_security/www/abode-security-panel.js` is updated
- [ ] Test in dev environment:
  - Panel loads in sidebar
  - Tabs switch correctly
  - Modes tab shows modes and actions
  - Actions tab shows action list
  - Recent triggers section displays correctly
  - Add/edit action opens editor
  - Form validation works
  - Save creates/updates action
  - Delete shows confirmation, then removes action
  - Test shows confirmation, then triggers action
  - Toggle enables/disables action

---

## Sub-Phase H: E2E Tests

### File: `tests/e2e/test_actions_panel.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Actions Panel', () => {
  test.beforeEach(async ({ page }) => {
    // Login and navigate to panel
    await page.goto('http://localhost:8123');
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/lovelace/**');
    await page.click('text=Abode');
  });

  test('panel loads with tabs', async ({ page }) => {
    await expect(page.locator('text=Modes')).toBeVisible();
    await expect(page.locator('text=Actions')).toBeVisible();
  });

  test('can switch between tabs', async ({ page }) => {
    await page.click('text=Modes');
    await expect(page.locator('.mode-card')).toHaveCount(3);

    await page.click('text=Actions');
    await expect(page.locator('.actions-list')).toBeVisible();
  });

  test('can create new action', async ({ page }) => {
    await page.click('text=Actions');
    await page.click('text=Add Action');

    // Fill form
    await page.fill('input[type="text"]', 'Test Action');
    await page.click('text=Home');
    await page.click('text=Front Door'); // sensor
    await page.click('text=Panic Alarm'); // alarm

    await page.click('text=Save');

    // Verify action appears in list
    await expect(page.locator('text=Test Action')).toBeVisible();
  });

  test('delete shows confirmation dialog', async ({ page }) => {
    // Assuming an action exists
    await page.click('text=Actions');
    await page.click('[title="Delete"]');

    await expect(page.locator('text=Delete action')).toBeVisible();
    await expect(page.locator('text=cannot be undone')).toBeVisible();
  });

  test('test action shows confirmation dialog', async ({ page }) => {
    await page.click('text=Actions');
    await page.click('[title="Test"]');

    await expect(page.locator('text=trigger real alarms')).toBeVisible();
  });

  test('form validation prevents empty name', async ({ page }) => {
    await page.click('text=Actions');
    await page.click('text=Add Action');

    // Try to save without name
    await page.click('text=Home');
    await page.click('text=Front Door');
    await page.click('text=Panic Alarm');
    await page.click('text=Save');

    await expect(page.locator('text=Name is required')).toBeVisible();
  });

  test('recent triggers section shows triggered actions', async ({ page }) => {
    await page.click('text=Actions');
    await expect(page.locator('text=Recent Triggers')).toBeVisible();
  });

  // Mobile viewport test
  test('responsive layout on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.click('text=Modes');

    // Cards should stack vertically
    const cards = page.locator('.mode-card');
    const firstBox = await cards.first().boundingBox();
    const secondBox = await cards.nth(1).boundingBox();

    // Second card should be below first (not side by side)
    expect(secondBox!.y).toBeGreaterThan(firstBox!.y);
  });
});
```

---

## Sub-Phase I: Frontend Unit Tests

### Setup

Add to `frontend/package.json`:
```json
{
  "devDependencies": {
    "@open-wc/testing": "^3.1.0",
    "@web/test-runner": "^0.15.0"
  },
  "scripts": {
    "test": "web-test-runner"
  }
}
```

Create `frontend/web-test-runner.config.js`:
```javascript
export default {
  files: 'src/__tests__/**/*.test.ts',
  nodeResolve: true,
};
```

### File: `frontend/src/__tests__/actions-tab.test.ts`

```typescript
import { fixture, html, expect } from '@open-wc/testing';
import '../actions-tab';
import { ActionsTab } from '../actions-tab';

describe('ActionsTab', () => {
  it('renders empty state when no actions', async () => {
    const el = await fixture<ActionsTab>(html`
      <abode-actions-tab></abode-actions-tab>
    `);

    expect(el.shadowRoot!.textContent).to.include('No actions configured');
  });

  it('dispatches delete-request event on delete click', async () => {
    const el = await fixture<ActionsTab>(html`
      <abode-actions-tab></abode-actions-tab>
    `);

    // Set up action data
    el._actions = [{
      id: 'test-1',
      name: 'Test Action',
      modes: ['home'],
      sensor_entity_ids: ['binary_sensor.door'],
      alarm_entity_ids: ['switch.panic'],
      enabled: true,
      delay_seconds: 0,
      last_triggered: null,
      trigger_count: 0,
    }];
    await el.updateComplete;

    // Click delete
    const deleteBtn = el.shadowRoot!.querySelector('[title="Delete"]');
    deleteBtn!.click();
    await el.updateComplete;

    // Confirmation dialog should show
    expect(el._showDeleteConfirm).to.be.true;
  });

  it('filters recent triggers correctly', async () => {
    const el = await fixture<ActionsTab>(html`
      <abode-actions-tab></abode-actions-tab>
    `);

    el._actions = [
      { id: '1', name: 'A', last_triggered: '2024-01-01T10:00:00Z', trigger_count: 1 },
      { id: '2', name: 'B', last_triggered: null, trigger_count: 0 },
      { id: '3', name: 'C', last_triggered: '2024-01-02T10:00:00Z', trigger_count: 2 },
    ] as any;

    const recent = el._getRecentTriggers();
    expect(recent).to.have.length(2);
    expect(recent[0].name).to.equal('C'); // Most recent first
  });
});
```

---

## Verification

```bash
# Build frontend
cd frontend && npm run build

# Run frontend unit tests
cd frontend && npm test

# Start dev environment
./scripts/dev.sh

# In browser:
# 1. Navigate to Abode in sidebar
# 2. Check modes tab displays correctly
# 3. Check actions tab displays correctly
# 4. Create a new action
# 5. Edit the action
# 6. Toggle enable/disable
# 7. Test the action (confirm dialog appears)
# 8. Delete the action (confirm dialog appears)

# Run E2E tests
npm run test:e2e
```

## Notes

- Use HA's built-in components where available (`ha-icon`, `ha-switch`, `ha-icon-button`)
- Follow HA's theming with CSS variables (`--primary-color`, `--primary-text-color`, etc.)
- Toast notifications for success/error feedback
- Loading spinner during async operations
- Mobile-responsive layout (cards stack on small screens)
