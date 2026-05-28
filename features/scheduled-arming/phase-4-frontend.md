---
status: in_progress
---

# Phase 4: Frontend UI

Build the always-visible "Home schedules" section beneath the modes grid. Three new Lit components: `day-chip-picker` (reusable weekday widget), `schedule-row` (single inline-edit row), and `schedules-section` (list + Add button + WS API integration). Mount it in `modes-tab.ts`. Add typed WS wrappers in `api.ts`.

After this phase, the feature is fully shipped: a user can see, create, edit, enable/disable, and delete schedules from the panel UI, and the runtime from Phase 3 fires them.

## Context

The Phase 1–3 work is purely backend. This phase adds the discoverability layer the user actually interacts with. The user explicitly chose:

- **Always-visible section** below the modes grid (not modal, not expand-on-click).
- **Inline-edit rows**: row stays put, fields become editable.
- **"Add schedule" button** inserts a new row in edit mode.
- **Per-row Save** with inline validation errors (NOT batch save).
- **Native `<input type=time>`** + custom day-chip component (no third-party picker).
- **No hint on mode cards** — section below is the only source of truth.
- **Admin-only edit** — non-admins see the section read-only.

Read [./README.md](./README.md) — especially **Frontend** in Requirements. Re-read the existing `frontend/src/modes-tab.ts` and `frontend/src/action-editor.ts` for inline-edit patterns.

## Structure

```
frontend/src/
  schedules-section.ts            # new: section container, list of rows, Add button, error display
  schedule-row.ts                 # new: single row, view + edit modes, validation, Save/Cancel
  day-chip-picker.ts              # new: 7 chips, multi-select, ARIA-accessible
  api.ts                          # update: add fetchSchedules, createSchedule, updateSchedule, deleteSchedule, getSchedule
  types.ts                        # update: AbodeSchedule, Weekday, ScheduleCreateInput, ScheduleUpdateInput types
  modes-tab.ts                    # update: import & mount <abode-schedules-section> below the grid
  __tests__/
    day-chip-picker.test.ts       # new: web-test-runner component test
    schedule-row.test.ts          # new: edit flow, validation
    schedules-section.test.ts     # new: list rendering, add flow, WS interaction
tests/e2e/
  test_scheduled_arming.spec.ts   # new: Playwright happy-path E2E
```

## Implementation Checklist

### Baseline Test Verification

- [ ] `uv run pytest -m ""` — all backend tests pass after Phases 1–3.
- [ ] `cd frontend && npm test` — existing frontend tests pass.
- [ ] `./scripts/check.sh` — green.
- [ ] Manually verify Phase 3 runtime: create a schedule via WS (curl or `ha_call_service`), watch it fire. The UI doesn't exist yet but the WS API is fully functional.

### Sub-Phase A: Types + API client wrappers

Deployable unit: TypeScript types and `api.ts` functions that the new components will consume. No UI yet — just the contract.

#### Implementation

- [x] In `frontend/src/types.ts`, **widen the existing `HomeAssistant` interface** (at lines 18-21) to expose the current user — required by the section's admin-gating logic:
  ```typescript
  export interface HomeAssistant {
    callWS<T>(params: { type: string; [key: string]: unknown }): Promise<T>;
    states: Record<string, HassEntityState>;
    user?: {            // NEW: optional so existing fixtures keep compiling.
      is_admin: boolean;
      id?: string;
      name?: string;
    };
  }
  ```
- [x] In `frontend/src/types.ts` add:
  ```typescript
  export type Weekday = 'mon' | 'tue' | 'wed' | 'thu' | 'fri' | 'sat' | 'sun';
  export const WEEKDAYS: readonly Weekday[] = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];

  export interface AbodeSchedule {
    id: string;
    name: string;             // "" when omitted (never null)
    weekdays: Weekday[];
    arm_time: string;         // "HH:MM"
    disarm_time: string;
    enabled: boolean;
    created_at: string;       // ISO-8601 UTC, immutable
    last_armed_at: string | null;
    last_disarmed_at: string | null;
    last_skip_reason: string | null;  // one of SkipReason values from README
    last_error: string | null;
  }

  export interface ScheduleCreateInput {
    name?: string;
    weekdays: Weekday[];
    arm_time: string;
    disarm_time: string;
    enabled?: boolean;
  }

  export type ScheduleUpdateInput = Partial<ScheduleCreateInput> & { id: string };
  ```
- [x] In `frontend/src/api.ts` add (parallel to the existing actions functions):
  ```typescript
  export async function fetchSchedules(hass: HomeAssistant): Promise<AbodeSchedule[]> {
    const resp = await hass.callWS<{ schedules: AbodeSchedule[] }>({
      type: 'abode_security/schedules/list',
    });
    return resp.schedules;
  }
  export async function getSchedule(hass: HomeAssistant, id: string): Promise<AbodeSchedule> {
    return hass.callWS({ type: 'abode_security/schedules/get', id });
  }
  export async function createSchedule(hass: HomeAssistant, data: ScheduleCreateInput): Promise<AbodeSchedule> {
    return hass.callWS({ type: 'abode_security/schedules/create', ...data });
  }
  export async function updateSchedule(hass: HomeAssistant, data: ScheduleUpdateInput): Promise<AbodeSchedule> {
    return hass.callWS({ type: 'abode_security/schedules/update', ...data });
  }
  export async function deleteSchedule(hass: HomeAssistant, id: string): Promise<void> {
    await hass.callWS({ type: 'abode_security/schedules/delete', id });
  }
  ```

#### Tests

- [x] No new unit test for `api.ts` (it's a thin pass-through; existing convention doesn't unit-test these directly). Type-checking via `tsc` is the safety net.

### Sub-Phase B: `day-chip-picker.ts` widget

Deployable unit: a reusable Lit element rendering 7 weekday chips with multi-select. Keyboard accessible.

#### Implementation

- [x] Create `frontend/src/day-chip-picker.ts`:
  ```typescript
  import { LitElement, html, css } from 'lit';
  import { customElement, property } from 'lit/decorators.js';
  import { WEEKDAYS, type Weekday } from './types';

  @customElement('abode-day-chip-picker')
  export class DayChipPicker extends LitElement {
    @property({ type: Array }) selected: Weekday[] = [];
    @property({ type: Boolean }) disabled = false;

    static styles = css`/* chip styles — match existing badge styles in modes-tab.ts */`;

    private _toggle(day: Weekday) {
      if (this.disabled) return;
      const next = this.selected.includes(day)
        ? this.selected.filter(d => d !== day)
        : [...this.selected, day];
      this.dispatchEvent(new CustomEvent('change', { detail: { selected: next } }));
    }

    render() {
      return html`
        <div class="chips" role="group" aria-label="Weekdays">
          ${WEEKDAYS.map(day => html`
            <button
              type="button"
              class="chip ${this.selected.includes(day) ? 'active' : ''}"
              ?disabled=${this.disabled}
              aria-pressed=${this.selected.includes(day)}
              aria-label=${this._fullName(day)}
              title=${this._fullName(day)}
              @click=${() => this._toggle(day)}
            >${this._label(day)}</button>
          `)}
        </div>
      `;
    }

    private _label(day: Weekday): string {
      // Single-letter visible label. NOTE: Tue/Thu and Sat/Sun share a letter
      // visually — disambiguation MUST come from aria-label + title (below).
      // Do not "fix" by switching to 2-letter labels; the design calls for 1.
      return { mon: 'M', tue: 'T', wed: 'W', thu: 'T', fri: 'F', sat: 'S', sun: 'S' }[day];
    }

    private _fullName(day: Weekday): string {
      return { mon: 'Monday', tue: 'Tuesday', wed: 'Wednesday', thu: 'Thursday',
               fri: 'Friday', sat: 'Saturday', sun: 'Sunday' }[day];
    }
  }
  ```
- [x] Style chips to match the existing `.badge` style in `modes-tab.ts` for visual consistency.
- [x] Day labels are single letters; aria-label AND tooltip carry the full name so screen readers and hover users can disambiguate Tue/Thu and Sat/Sun. Tests must assert `aria-label` matches the full weekday name.

#### Tests

- [x] `frontend/src/__tests__/day-chip-picker.test.ts`:
  - Renders 7 chips.
  - Clicking a chip dispatches `change` with the toggled selection.
  - `disabled=true` blocks clicks.
  - `aria-pressed` reflects selection.
  - Keyboard: Tab focuses each chip; Space/Enter toggles.

### Sub-Phase C: `schedule-row.ts` component

Deployable unit: a single row that toggles between view and edit modes, validates inline, and emits save/delete events.

#### Implementation

- [x] Create `frontend/src/schedule-row.ts`:
  ```typescript
  @customElement('abode-schedule-row')
  export class ScheduleRow extends LitElement {
    @property({ attribute: false }) schedule!: AbodeSchedule;
    @property({ type: Boolean }) canEdit = false;
    @state() private _editing = false;
    @state() private _draft: ScheduleCreateInput | null = null;
    @state() private _error: string | null = null;
    @state() private _saving = false;

    // Events emitted:
    //   - save: { detail: { id?: string; data: ScheduleCreateInput } }
    //   - delete: { detail: { id: string } }
    //   - cancel-new: { detail: {} } — for the special "new row" case below

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
    }
    private _cancel()    { this._editing = false; this._draft = null; this._error = null; }

    private _validate(draft: ScheduleCreateInput): string | null {
      if (draft.weekdays.length === 0) return 'Pick at least one weekday';
      if (draft.arm_time === draft.disarm_time) return 'Arm and disarm times must differ';
      if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(draft.arm_time)) return 'Invalid arm time';
      if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(draft.disarm_time)) return 'Invalid disarm time';
      if ((draft.name?.length ?? 0) > 100) return 'Name too long (max 100)';
      return null;
    }

    private async _save() {
      if (!this._draft) return;
      const err = this._validate(this._draft);
      if (err) { this._error = err; return; }
      this._saving = true;
      this._error = null;
      this.dispatchEvent(new CustomEvent('save', { detail: { id: this.schedule.id, data: this._draft }}));
      // Parent flips _editing off after WS success.
    }

    // Render view-mode and edit-mode bodies.
  }
  ```
- [x] View mode renders: `[day chips read-only] [arm → disarm] [enable toggle] [edit icon] [delete icon]`. If `last_error` is non-null on the schedule, render a small warning badge.
- [x] Edit mode renders: `[day-chip-picker editable] [arm input[type=time]] [→] [disarm input[type=time]] [name input optional] [enable toggle] [Save] [Cancel]`.
- [x] Validation errors appear inline beneath the row's edit area with `role="alert"`.
- [x] When `canEdit=false` (non-admin), the edit/delete icons are hidden; view mode only.
- [x] Disabled schedules render with reduced opacity (parallel to `action-list li.disabled` in `modes-tab.ts`).

#### "New row" subtype

- [x] Same component handles the "add schedule" case: the section creates a synthetic `AbodeSchedule` with empty fields and `id=""`, sets `_editing=true` initially, and listens for `save` (calls `createSchedule`) or `cancel-new` (removes the synthetic row). When `schedule.id === ''`, the row is in "new" mode and Cancel emits `cancel-new` instead of just toggling `_editing`.

#### Tests

- [x] `frontend/src/__tests__/schedule-row.test.ts`:
  - View mode renders correctly with all fields.
  - Click edit → enters edit mode with draft initialized.
  - Validation: empty weekdays → error shown, no save event.
  - Validation: same arm/disarm → error shown.
  - Valid edit → `save` event dispatched with `{id, data}`.
  - Cancel → reverts to view mode, draft cleared.
  - `canEdit=false` → no edit/delete icons; clicking the row doesn't enter edit mode.
  - New-row mode (`id===''`) → Cancel emits `cancel-new`.
  - Disabled schedule renders with `.disabled` class.

### Sub-Phase D: `schedules-section.ts` container

Deployable unit: the section component that owns the list, fetches schedules on mount, handles Add/Save/Delete via WS, and surfaces section-level errors.

#### Implementation

- [x] Create `frontend/src/schedules-section.ts`:
  ```typescript
  @customElement('abode-schedules-section')
  export class SchedulesSection extends LitElement {
    @property({ attribute: false }) hass!: HomeAssistant;
    @state() private _schedules: AbodeSchedule[] = [];
    @state() private _loading = true;
    @state() private _error: string | null = null;
    @state() private _newRow: AbodeSchedule | null = null;  // when "Add schedule" clicked

    private _abort: AbortController | null = null;

    connectedCallback() {
      super.connectedCallback();
      // Lit's connectedCallback is synchronous (matches the DOM lifecycle).
      // Kick off the fetch as a fire-and-forget; _load handles its own errors.
      void this._load();
    }

    disconnectedCallback() {
      this._abort?.abort();
      super.disconnectedCallback();
    }

    private get _isAdmin(): boolean {
      // HA exposes the current user on `hass.user` as `CurrentUser` (see
      // `home-assistant-js-websocket/dist/types.d.ts`). The flag is
      // `is_admin: boolean`. This is a UX hint only — the WS endpoint enforces
      // `@require_admin` server-side (see Phase 1). If `hass.user` is
      // undefined (rare, but possible during HA reload), treat as non-admin.
      //
      // IMPORTANT: the local `HomeAssistant` interface in
      // `frontend/src/types.ts:18-21` currently declares only `callWS` and
      // `states`. Extend it in this phase to add
      // `user?: { is_admin: boolean; id?: string; name?: string }` so this
      // access type-checks. Keep the field optional so existing test fixtures
      // that omit it continue to compile.
      //
      // Precedent note: other components in `frontend/src/` (e.g.
      // `cameras-tab.ts:176`) skip the client-side admin check and instead
      // catch the server-side `unauthorized` error. That approach is also
      // acceptable; the choice here is to hide controls upfront to avoid
      // dead-end UX, since `schedules/list` is open and rendering the section
      // for non-admins is the common path.
      return Boolean(this.hass.user?.is_admin);
    }

    private async _load() {
      // Mirror `frontend/src/modes-tab.ts:309-335` exactly. The shape:
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
      // The synthetic row is a sentinel for the "new schedule" UI state. It
      // satisfies the `AbodeSchedule` shape so `<abode-schedule-row>` can
      // consume it uniformly; the server-managed fields (`id`, `created_at`)
      // are placeholders that `createSchedule` overwrites on save.
      this._newRow = {
        id: '',
        name: '',
        weekdays: [],
        arm_time: '22:00',
        disarm_time: '06:00',
        enabled: true,
        created_at: '',  // placeholder — server stamps the real value on create
        last_armed_at: null,
        last_disarmed_at: null,
        last_skip_reason: null,
        last_error: null,
      };
    }

    private async _onSave(e: CustomEvent) {
      const { id, data } = e.detail;
      try {
        if (!id) {
          const created = await createSchedule(this.hass, data);
          this._schedules = [...this._schedules, created];
          this._newRow = null;
        } else {
          const updated = await updateSchedule(this.hass, { id, ...data });
          this._schedules = this._schedules.map(s => s.id === id ? updated : s);
        }
        // child row toggles back to view mode on next render (data prop changes)
      } catch (err) {
        // Forward to child row error state via event redispatch, OR
        // surface as a section-level error banner. Simplest: section-level banner.
        this._error = err instanceof Error ? err.message : 'Failed to save';
      }
    }

    private async _onDelete(e: CustomEvent) { /* confirm dialog → deleteSchedule */ }

    render() {
      return html`
        <section class="schedules-section" aria-labelledby="schedules-heading">
          <h2 id="schedules-heading">Home schedules</h2>
          ${this._loading ? html`<div>Loading…</div>` : ''}
          ${this._error ? html`<div role="alert" class="error">${this._error}</div>` : ''}
          ${this._schedules.length === 0 && !this._newRow ? html`
            <p class="empty">No schedules yet. Add one to arm Home automatically.</p>
          ` : ''}
          ${this._schedules.map(s => html`
            <abode-schedule-row
              .schedule=${s}
              .canEdit=${this._isAdmin}
              @save=${this._onSave}
              @delete=${this._onDelete}
            ></abode-schedule-row>
          `)}
          ${this._newRow ? html`
            <abode-schedule-row
              .schedule=${this._newRow}
              .canEdit=${true}
              @save=${this._onSave}
              @cancel-new=${() => this._newRow = null}
            ></abode-schedule-row>
          ` : ''}
          ${this._isAdmin && !this._newRow ? html`
            <button class="add-button" @click=${this._addNewRow}>+ Add schedule</button>
          ` : ''}
        </section>
      `;
    }
  }
  ```
- [x] Confirm-before-delete pattern: reuse `abode-modal` like `modes-tab.ts` does for the mode-switch confirm. Heading "Delete schedule?", body "This will stop the automatic arming at the configured times. The action does not affect the current panel state."
- [x] **Optimistic concurrency**: when a WS update returns the updated schedule, replace the local copy. If the user is mid-edit on another row when the section re-fetches (rare, but possible via `hass-tagged` reactivity), preserve the in-progress draft. Simplest implementation: only refresh on explicit mount; do not subscribe to WS push updates in v1.
- [x] Listen to WS events (`abode_security.schedule_fired` etc.) for **live `last_armed_at` / `last_disarmed_at` updates** on rows? **Out of scope for v1** — keep the section's data fresh only on mount. The row's "last fired" UI is just `last_armed_at`/`last_disarmed_at` from the stored schedule.

#### Tests

- [x] `frontend/src/__tests__/schedules-section.test.ts`:
  - Initial mount fetches schedules; renders empty-state if list is empty.
  - "Add schedule" button visible for admin, hidden for non-admin.
  - Click "Add schedule" → new row in edit mode appears at the bottom.
  - New-row save → calls `createSchedule`, appends to list, removes the new row.
  - New-row cancel → removes the new row, does not call WS.
  - Existing-row save → calls `updateSchedule`, replaces in list.
  - Delete with confirm → calls `deleteSchedule`, removes from list.
  - WS error on create → section-level error banner shown.
  - Non-admin view → edit/delete icons hidden on all rows; no Add button. (Inject the admin/non-admin distinction via a test `hass` fixture: `hass.user = { is_admin: false }` for non-admin, `{ is_admin: true }` for admin. The interface widening from Sub-Phase A makes both compile.)

### Sub-Phase E: Mount in `modes-tab.ts`

Deployable unit: the section actually appears beneath the modes grid.

#### Implementation

- [ ] In `frontend/src/modes-tab.ts`:
  - Import `'./schedules-section'`.
  - Add `<abode-schedules-section .hass=${this.hass}></abode-schedules-section>` immediately after `<div class="modes-grid">…</div>` in the `render()` method (around line 484).
  - Adjust styles: the section needs ~24px of top margin separating it from the modes grid.
- [ ] No changes to mode card content — the user explicitly said no card-level hints.

#### Tests

- [ ] Existing `modes-tab.ts` tests continue to pass (regression check).
- [ ] Add one mount test: `modes-tab` renders both `.modes-grid` and `<abode-schedules-section>`.

### Sub-Phase F: E2E test

Deployable unit: a Playwright spec that exercises the happy path.

#### Implementation

- [ ] Create `tests/e2e/test_scheduled_arming.spec.ts` (mirror existing E2E layout):
  - Setup: dev stack via `./scripts/dev.sh` (the e2e suite already launches it).
  - Log in as admin.
  - Navigate to `/abode_security`.
  - Verify the "Home schedules" section renders with empty state.
  - Click "+ Add schedule".
  - Select Mon, Tue, Wed weekdays.
  - Set arm time `22:00`, disarm `06:00`.
  - Click Save.
  - Verify the row appears in the list with the correct summary.
  - Edit the row → change name to "Weeknights" → Save.
  - Verify name displayed.
  - Toggle enabled off → verify visual state.
  - Delete the row → confirm in dialog → verify row gone.
- [ ] **Non-admin E2E is optional, not required.** No non-admin fixture exists today in `tests/e2e/fixtures/` (only `auth.ts` for the `admin/admin` user). If you decide to add one, create a new HA user via the WS API in a setup step rather than baking credentials into the fixture; otherwise, cover the non-admin path in the `web-test-runner` unit tests for `schedules-section.test.ts` (which already mock `hass.user.is_admin`) and skip the E2E variant.

### Documentation (End of Phase)

- [ ] `docs/ARCHITECTURE.md` — add a short subsection under the "Frontend" section describing the schedules UI components.
- [ ] `docs/notifications.md` — finalize the "Notifying on schedule events" section started in Phase 3.
- [ ] `CLAUDE.md` — no change needed (commands unchanged).
- [ ] Take a screenshot of the populated section (manually, via the dev stack) and add to `docs/` under a new `screenshots/` folder if the project conventions support it. Reference from `README.md` (top-level) under the "Features" list if such a list exists.

### Build Verification

- [ ] `uv run ruff check . && uv run mypy custom_components && uv run pyright` — all green.
- [ ] `uv run pytest -m ""` — all backend tests pass.
- [ ] `uv run pytest -m integration` — passes.
- [ ] `cd frontend && npm test` — all frontend component tests pass.
- [ ] `cd frontend && npm run build` — Rollup bundle builds without errors or warnings.
- [ ] `./scripts/test-e2e.sh` — Playwright suite passes including the new spec.
- [ ] Scan all test outputs for `WARNING` / `ERROR` lines and uncaught exceptions even when exit codes are 0.
- [ ] `./scripts/check.sh` — green.
- [ ] HACS validation step (existing `validate.yaml` workflow runs on PR; locally it's covered by `./scripts/check.sh`).

### Manual Verification with MCP Tools

After E2E passes, exercise the UI end-to-end manually:

- [ ] Start `./scripts/dev.sh`. Open http://localhost:8123/abode_security in a browser.
- [ ] Verify the "Home schedules" section renders below the mode cards with the empty state.
- [ ] Click "+ Add schedule", fill in a schedule firing in ~2 minutes, save.
- [ ] Use `mcp__home-assistant__ha_get_state` on the alarm_control_panel entity → confirm it transitions to `armed_home` at the right time.
- [ ] Use `mcp__home-assistant__ha_get_logs` to verify `Schedule '<name>' fired arm` log line.
- [ ] Wait for the disarm time, verify entity goes back to `disarmed`.
- [ ] Manually disarm the panel via the panel UI mid-window → verify the row's "last fired" updates correctly on next refresh and the disarm timer was cancelled (check logs for `manual_override`).
- [ ] Log in as a non-admin HA user → verify the schedules section is read-only (no Add button, no edit/delete icons).
- [ ] Verify keyboard accessibility: tab through the section, ensure focus is visible and all controls are reachable.
- [ ] Verify mobile rendering (HA Companion app or browser narrow viewport): rows stack cleanly; day chips remain tappable (≥44px target).

> **Browser MCP unavailable**: at spec time the `mcp__browsermcp__*` server was offline. The Playwright E2E suite (`./scripts/test-e2e.sh`) is the canonical visual verification. If browser MCP is restored before this phase ships, it can supplement — but do not block on it.

## Technical Details

### Component composition

```
<abode-modes-tab>
  <div class="modes-grid">…three mode cards…</div>
  <abode-schedules-section>
    <h2>Home schedules</h2>
    <abode-schedule-row>            // for each existing schedule
      <abode-day-chip-picker .selected=... ?disabled />
      <input type="time" />
      <input type="time" />
      …
    </abode-schedule-row>
    <abode-schedule-row>            // new-row when adding
    <button>+ Add schedule</button>
  </abode-schedules-section>
</abode-modes-tab>
```

### Accessibility

- `<button>` for all clickables (never `<div onclick>`).
- `role="group"` + `aria-label` on the day-chip cluster.
- `aria-pressed` on each chip.
- `role="alert"` on validation/error messages.
- Native `<input type="time">` provides built-in keyboard + screen reader support; do not wrap.
- Confirm-delete modal uses `variant="alertdialog"` (same as the mode-switch confirm in `modes-tab.ts`).
- Focus management: when entering edit mode, focus the first interactive element (day-chip-picker's first chip). When closing the confirm modal, focus returns to the delete button.

### What this phase explicitly does NOT include

- ❌ No live push updates of `last_armed_at` / `last_disarmed_at` via WS subscriptions — section refreshes only on mount.
- ❌ No "next fire time" countdown display — derivable client-side but not in v1.
- ❌ No schedule history view (which schedules fired when) — defer; user can build a logbook automation listening on the events.
- ❌ No drag-to-reorder — schedules display in created_at order.
- ❌ No bulk enable/disable/copy — single-row operations only.
- ❌ No timezone picker — uses HA's timezone implicitly.
- ❌ No second mode-card-level hint — explicitly out of scope per the user's Round 3 answer.

## Constraints

- **No new npm dependencies.** Use only what `package.json` already declares plus Lit / `@open-wc/testing` already pulled in.
- **Native `<input type="time">`** is mandatory for time entry. Do not wrap in a custom widget.
- **Day-chip-picker is reusable.** Do not bake schedule-specific logic into it.
- **Per-row save** is the contract: the section never has a global "Save changes" button.
- **Inline validation** must run client-side BEFORE calling the WS endpoint. The WS endpoint is the second line of defense.
- **Admin gating in the UI is a UX layer**, not a security boundary. The WS endpoints (Phase 1) enforce `@require_admin`. The frontend simply hides controls non-admins can't use.
- **Match existing style tokens**: `--primary-color`, `--secondary-background-color`, `--divider-color`, etc. used in `modes-tab.ts`. No hard-coded colors except as fallbacks.
- **Mobile-friendly**: rows must stack/wrap gracefully under 480px viewport width. Touch targets ≥44px.
- **Tests use `@open-wc/testing` with `web-test-runner`** following `frontend/web-test-runner.config.mjs`. Playwright is for E2E only.
- **Reactivity**: when the section receives a new `hass` prop reassignment (HA does this on every state change), the section should NOT refetch schedules on every reassignment — only on initial mount. The `last_armed_at` field updating in the store won't reflect in the row until the next mount; that's acceptable per the user's set-and-forget UX preference.
