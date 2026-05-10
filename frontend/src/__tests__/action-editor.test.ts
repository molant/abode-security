/**
 * Tests for the ActionEditor component.
 *
 * Note: These tests focus on rendering behavior with pre-loaded data.
 * API integration is tested via E2E and integration tests.
 */

import { aTimeout, expect, fixture, html } from '@open-wc/testing';

import '../action-editor.js';
import type { ActionEditor } from '../action-editor.js';
import type { HomeAssistant, SensorEntity } from '../types.js';
import {
  createMockHass,
  createMockAction,
  createMockSensors,
  createMockAlarms,
  elementUpdated,
  setState,
} from './test-helpers.js';

describe('ActionEditor', () => {
  describe('rendering', () => {
    it('renders create form when no action provided', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);

      // @ts-expect-error - accessing private property for testing
      el._sensors = createMockSensors();
      // @ts-expect-error - accessing private property for testing
      el._alarms = createMockAlarms();
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      // Heading is rendered inside <abode-modal>'s shadow root, so it's not in
      // textContent — read it off the heading attribute instead.
      const modal = el.shadowRoot?.querySelector('abode-modal');
      expect(modal?.getAttribute('heading')).to.equal('New Action');
    });

    it('renders edit form when action provided', async () => {
      const hass = createMockHass();
      const action = createMockAction({ name: 'Existing Action' });
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass} .action=${action}></abode-action-editor>
      `);

      // @ts-expect-error - accessing private property for testing
      el._sensors = createMockSensors();
      // @ts-expect-error - accessing private property for testing
      el._alarms = createMockAlarms();
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const modal = el.shadowRoot?.querySelector('abode-modal');
      expect(modal?.getAttribute('heading')).to.equal('Edit Action');
    });

    it('displays sensors grouped by category', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);

      // @ts-expect-error - accessing private property for testing
      el._sensors = createMockSensors();
      // @ts-expect-error - accessing private property for testing
      el._alarms = createMockAlarms();
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      // Should show sensor categories (first letter capitalized)
      expect(el.shadowRoot?.textContent).to.include('Door');
      expect(el.shadowRoot?.textContent).to.include('Motion');
    });

    it('renders categories returned by the backend even when not in the legacy allowlist', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);

      // Intentionally use device_class keys outside the legacy seven-name
      // allowlist — this is the shape the HA backend actually returns.
      const wideSensors: Record<string, SensorEntity[]> = {
        garage_door: [
          { entity_id: 'binary_sensor.garage', name: 'Garage Door', state: 'closed' },
        ],
        gas: [
          { entity_id: 'binary_sensor.gas_kitchen', name: 'Kitchen Gas', state: 'off' },
        ],
      };
      // @ts-expect-error - accessing private property for testing
      el._sensors = wideSensors;
      // @ts-expect-error - accessing private property for testing
      el._alarms = createMockAlarms();
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      // Both non-allowlisted categories should appear as category headers,
      // and each sensor inside should be selectable. Match case-insensitively
      // so a future title-case label map can't make this test brittle.
      const categoryHeaders = Array.from(
        el.shadowRoot?.querySelectorAll('.category-header span') ?? [],
      ).map((s) => s.textContent ?? '');
      expect(categoryHeaders.some((l) => /garage[\s_]door/i.test(l))).to.equal(
        true,
        `expected a "garage door" category header, got: ${JSON.stringify(categoryHeaders)}`,
      );
      expect(categoryHeaders.some((l) => /\bgas\b/i.test(l))).to.equal(
        true,
        `expected a "gas" category header, got: ${JSON.stringify(categoryHeaders)}`,
      );
      expect(el.shadowRoot?.textContent).to.include('Garage Door');
      expect(el.shadowRoot?.textContent).to.include('Kitchen Gas');
    });

    it('skips categories with zero sensors', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);

      // @ts-expect-error - accessing private property for testing
      el._sensors = {
        door: [
          { entity_id: 'binary_sensor.front', name: 'Front Door', state: 'off' },
        ],
        motion: [],
      };
      // @ts-expect-error - accessing private property for testing
      el._alarms = createMockAlarms();
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const categoryHeaders = Array.from(
        el.shadowRoot?.querySelectorAll('.category-header span') ?? [],
      ).map((s) => s.textContent ?? '');
      expect(categoryHeaders.some((l) => /\bdoor\b/i.test(l))).to.equal(true);
      expect(categoryHeaders.some((l) => /\bmotion\b/i.test(l))).to.equal(
        false,
        'empty motion category should be skipped',
      );
    });

    it('displays alarm options', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);

      // @ts-expect-error - accessing private property for testing
      el._sensors = createMockSensors();
      // @ts-expect-error - accessing private property for testing
      el._alarms = createMockAlarms();
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      expect(el.shadowRoot?.textContent).to.include('Panic Alarm');
      expect(el.shadowRoot?.textContent).to.include('Fire Alarm');
    });

    it('shows all three mode checkboxes', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);

      // @ts-expect-error - accessing private property for testing
      el._sensors = createMockSensors();
      // @ts-expect-error - accessing private property for testing
      el._alarms = createMockAlarms();
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      expect(el.shadowRoot?.textContent).to.include('Standby');
      expect(el.shadowRoot?.textContent).to.include('Home');
      expect(el.shadowRoot?.textContent).to.include('Away');
    });
  });

  describe('events', () => {
    it('dispatches cancel event when Cancel clicked', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);

      // @ts-expect-error - accessing private property for testing
      el._sensors = createMockSensors();
      // @ts-expect-error - accessing private property for testing
      el._alarms = createMockAlarms();
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      let cancelFired = false;
      el.addEventListener('cancel', () => {
        cancelFired = true;
      });

      const cancelButton = el.shadowRoot?.querySelector('.cancel') as HTMLButtonElement;
      cancelButton?.click();

      expect(cancelFired).to.be.true;
    });

    it('dispatches cancel event when modal dispatches dismiss', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);

      // @ts-expect-error - accessing private property for testing
      el._sensors = createMockSensors();
      // @ts-expect-error - accessing private property for testing
      el._alarms = createMockAlarms();
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      let cancelFired = false;
      el.addEventListener('cancel', () => {
        cancelFired = true;
      });

      // The modal owns Escape/overlay-click handling and emits `dismiss`;
      // the editor responds by firing `cancel`.
      const modal = el.shadowRoot?.querySelector('abode-modal') as HTMLElement;
      modal?.dispatchEvent(new CustomEvent('dismiss', { bubbles: true, composed: true }));

      expect(cancelFired).to.be.true;
    });
  });

  describe('delay control', () => {
    it('shows delay slider', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);

      // @ts-expect-error - accessing private property for testing
      el._sensors = createMockSensors();
      // @ts-expect-error - accessing private property for testing
      el._alarms = createMockAlarms();
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      const delaySlider = el.shadowRoot?.querySelector('input[type="range"]');
      expect(delaySlider).to.exist;
    });
  });

  describe('accessibility', () => {
    it('renders the editor inside <abode-modal> with the dialog variant', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);

      // @ts-expect-error - accessing private property for testing
      el._sensors = createMockSensors();
      // @ts-expect-error - accessing private property for testing
      el._alarms = createMockAlarms();
      // @ts-expect-error - accessing private property for testing
      el._loading = false;
      await elementUpdated(el);

      // role/aria-modal correctness is owned by <abode-modal> and covered in
      // abode-modal.test.ts. Here we verify the editor leaves the variant at
      // its default by not setting the attribute (no explicit `variant="..."`),
      // which means the modal renders the standard 'dialog' role rather than
      // the 'alertdialog' that confirms use.
      const modal = el.shadowRoot?.querySelector('abode-modal');
      expect(modal).to.exist;
      expect(modal?.hasAttribute('variant')).to.equal(false);
      // The modal's default property value is 'dialog'.
      expect((modal as unknown as { variant?: string })?.variant).to.equal('dialog');
    });
  });

  describe('lifecycle and async safety', () => {
    it('populates form fields synchronously on connect, before _loadEntities resolves (#10)', async () => {
      // Regression for the post-await `_populateForm()` race: previously
      // `_populateForm` ran *after* the load, so a disconnect mid-fetch
      // could let _name/_modes/etc. mutate on a detached element. Moving
      // _populateForm before the await means form fields are set
      // synchronously on connect (and never touched on a detached element).
      let resolveSensors!: (value: { sensors: unknown }) => void;
      const sensorsPromise = new Promise<{ sensors: unknown }>((resolve) => {
        resolveSensors = resolve;
      });

      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/entities/sensors') {
            return sensorsPromise;
          }
          if (params.type === 'abode_security/entities/alarms') {
            return Promise.resolve({ alarms: createMockAlarms() });
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const action = createMockAction({
        name: 'Pre-existing',
        modes: ['away', 'home'],
        delay_seconds: 30,
      });

      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass} .action=${action}></abode-action-editor>
      `);

      // The load is still pending — sensorsPromise has not resolved.
      // Form fields must already be populated from `action`.
      // @ts-expect-error - accessing private property for testing
      expect(el._name).to.equal('Pre-existing');
      // @ts-expect-error - accessing private property for testing
      expect(el._modes).to.deep.equal(['away', 'home']);
      // @ts-expect-error - accessing private property for testing
      expect(el._delaySeconds).to.equal(30);

      // Disconnect mid-load — the post-await populate path is gone, so
      // there's nothing to race against now. Resolve to keep the runner clean.
      el.remove();
      resolveSensors({ sensors: createMockSensors() });
      await sensorsPromise;
      await aTimeout(0);
    });

    it('does not mutate state after disconnection while _loadEntities is in flight (#10)', async () => {
      let resolveSensors!: (value: { sensors: unknown }) => void;
      const sensorsPromise = new Promise<{ sensors: unknown }>((resolve) => {
        resolveSensors = resolve;
      });

      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/entities/sensors') {
            return sensorsPromise;
          }
          if (params.type === 'abode_security/entities/alarms') {
            return Promise.resolve({ alarms: createMockAlarms() });
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);

      // _loadEntities is in flight, awaiting sensorsPromise.
      // Disconnect before the promise resolves.
      el.remove();

      // Resolve after disconnection — the result must be discarded.
      resolveSensors({
        sensors: { door: [{ entity_id: 'binary_sensor.x', name: 'X', state: 'off' }] },
      });
      await sensorsPromise;
      // Yield once more so the await chain in _loadEntities resumes and the
      // signal-aborted check runs before we assert.
      await aTimeout(0);

      // @ts-expect-error - accessing private property for testing
      expect(el._sensors).to.equal(null, 'sensors must not mutate after disconnect');
      // @ts-expect-error - accessing private property for testing
      expect(el._loading).to.equal(true, '_loading must remain true (state ignored)');
    });

    it('surfaces a load error and a Retry button when _loadEntities rejects (#26)', async () => {
      let calls = 0;
      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/entities/sensors') {
            calls += 1;
            // First call fails; subsequent (Retry) calls succeed so we can
            // also assert that Retry actually re-runs the load.
            if (calls === 1) {
              return Promise.reject(new Error('WS connection lost'));
            }
            return Promise.resolve({ sensors: createMockSensors() });
          }
          if (params.type === 'abode_security/entities/alarms') {
            return Promise.resolve({ alarms: createMockAlarms() });
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      // Let _loadEntities reject and the component re-render with the error.
      await aTimeout(0);
      await elementUpdated(el);

      // Error message should be in the shadow tree.
      const errorText = el.shadowRoot?.textContent ?? '';
      expect(errorText).to.include('WS connection lost');

      // A Retry button should be rendered.
      const retryButton = Array.from(
        el.shadowRoot?.querySelectorAll('button') ?? [],
      ).find((b) => /retry/i.test(b.textContent ?? ''));
      expect(retryButton, 'expected a Retry button after load failure').to.exist;

      // Clicking Retry re-runs the load; second call succeeds.
      retryButton!.click();
      await aTimeout(0);
      await elementUpdated(el);

      expect(calls).to.equal(2, 'Retry must re-invoke fetchSensors');
      // @ts-expect-error - accessing private property for testing
      expect(el._loadError).to.equal(null);
      // @ts-expect-error - accessing private property for testing
      expect(el._sensors).to.not.equal(null);
    });

    it('_handleSave fires only one create when invoked twice synchronously (#27)', async () => {
      let createCalls = 0;
      let resolveCreate!: () => void;
      const createPromise = new Promise<{ id: string }>((resolve) => {
        resolveCreate = () => resolve({ id: 'new-id' });
      });

      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/entities/sensors') {
            return Promise.resolve({ sensors: createMockSensors() });
          }
          if (params.type === 'abode_security/entities/alarms') {
            return Promise.resolve({ alarms: createMockAlarms() });
          }
          if (params.type === 'abode_security/actions/create') {
            createCalls += 1;
            return createPromise;
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      // Let _loadEntities resolve so _loading flips to false and the form renders.
      await aTimeout(0);
      await elementUpdated(el);

      // Set valid form state — validation requires name + at least one of each.
      // @ts-expect-error - accessing private property for testing
      el._name = 'Test';
      // @ts-expect-error - accessing private property for testing
      el._modes = ['home'];
      // @ts-expect-error - accessing private property for testing
      el._selectedSensors = ['binary_sensor.front_door'];
      // @ts-expect-error - accessing private property for testing
      el._selectedAlarms = ['switch.abode_panic_alarm'];

      // Fire two _handleSave invocations synchronously, before `_saving=true`
      // can reflect through render to the button's `disabled` attribute.
      // @ts-expect-error - accessing private method for testing
      const p1 = el._handleSave();
      // @ts-expect-error - accessing private method for testing
      const p2 = el._handleSave();

      resolveCreate();
      await Promise.all([p1, p2]);

      expect(createCalls).to.equal(1, 'second synchronous _handleSave must be a no-op');
    });

    it('_handleSave is a no-op when re-entered across a microtask boundary while save is in flight (#27)', async () => {
      // Variant of the above: the second call arrives after `await Promise.resolve()`,
      // which models a real fast double-click better than a strictly synchronous
      // pair (browser dispatches one click, microtasks run, then the second click
      // arrives). The handler must still early-return because `_saving` was set
      // synchronously by the first call.
      let createCalls = 0;
      let resolveCreate!: () => void;
      const createPromise = new Promise<{ id: string }>((resolve) => {
        resolveCreate = () => resolve({ id: 'new-id' });
      });

      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/entities/sensors') {
            return Promise.resolve({ sensors: createMockSensors() });
          }
          if (params.type === 'abode_security/entities/alarms') {
            return Promise.resolve({ alarms: createMockAlarms() });
          }
          if (params.type === 'abode_security/actions/create') {
            createCalls += 1;
            return createPromise;
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await aTimeout(0);
      await elementUpdated(el);

      // @ts-expect-error - accessing private property for testing
      el._name = 'Test';
      // @ts-expect-error - accessing private property for testing
      el._modes = ['home'];
      // @ts-expect-error - accessing private property for testing
      el._selectedSensors = ['binary_sensor.front_door'];
      // @ts-expect-error - accessing private property for testing
      el._selectedAlarms = ['switch.abode_panic_alarm'];

      // First click — kicks off save and suspends on createPromise.
      // @ts-expect-error - accessing private method for testing
      const p1 = el._handleSave();
      // Yield to microtasks; render still hasn't reflected `_saving=true`
      // to the DOM yet (Lit re-render is async).
      await Promise.resolve();
      // Second click arrives now. Must early-return because _saving is true.
      // @ts-expect-error - accessing private method for testing
      const p2 = el._handleSave();

      resolveCreate();
      await Promise.all([p1, p2]);

      expect(createCalls).to.equal(1, 'microtask-delayed second _handleSave must be a no-op');
    });
  });

  // --- #31 Mutation flow tests -------------------------------------------
  // Cover validation branches, save (create vs update vs error), and the
  // category tri-state (the most complex piece of UI in this file). Plus
  // _populateForm for edit mode. Tests against the now-stable post-PR8.5
  // code; no failing-first phase.

  describe('_validate (#31)', () => {
    // _validate reads only _name/_modes/_selectedSensors/_selectedAlarms +
    // writes _errors; _sensors, _alarms, and _loading are intentionally
    // omitted from these setState patches.
    it('flags empty name with the expected error', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _name: '   ', // whitespace-only fails .trim()
        _modes: ['home'],
        _selectedSensors: ['binary_sensor.front_door'],
        _selectedAlarms: ['switch.abode_panic_alarm'],
      } as Partial<ActionEditor>);

      // @ts-expect-error - calling private method for testing
      const ok = el._validate();
      expect(ok).to.equal(false);
      // @ts-expect-error - accessing private property for testing
      expect(el._errors.name).to.equal('Name is required');
    });

    it('flags missing modes', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _name: 'OK',
        _modes: [],
        _selectedSensors: ['binary_sensor.front_door'],
        _selectedAlarms: ['switch.abode_panic_alarm'],
      } as Partial<ActionEditor>);

      // @ts-expect-error - calling private method for testing
      el._validate();
      // @ts-expect-error - accessing private property for testing
      expect(el._errors.modes).to.equal('Select at least one mode');
    });

    it('flags missing sensors', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _name: 'OK',
        _modes: ['home'],
        _selectedSensors: [],
        _selectedAlarms: ['switch.abode_panic_alarm'],
      } as Partial<ActionEditor>);

      // @ts-expect-error - calling private method for testing
      el._validate();
      // @ts-expect-error - accessing private property for testing
      expect(el._errors.sensors).to.equal('Select at least one sensor');
    });

    it('flags missing alarms', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _name: 'OK',
        _modes: ['home'],
        _selectedSensors: ['binary_sensor.front_door'],
        _selectedAlarms: [],
      } as Partial<ActionEditor>);

      // @ts-expect-error - calling private method for testing
      el._validate();
      // @ts-expect-error - accessing private property for testing
      expect(el._errors.alarms).to.equal('Select at least one alarm');
    });

    it('clears a field error via _clearError', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _errors: { name: 'Name is required', modes: 'Select at least one mode' },
      } as Partial<ActionEditor>);

      // @ts-expect-error - calling private method for testing
      el._clearError('name');
      // @ts-expect-error - accessing private property for testing
      expect(el._errors.name).to.equal(undefined);
      // Other errors untouched.
      // @ts-expect-error - accessing private property for testing
      expect(el._errors.modes).to.equal('Select at least one mode');
    });
  });

  describe('_handleSave (#31)', () => {
    it('calls createAction when no action prop is set', async () => {
      let createPayload: Record<string, unknown> | null = null;
      const hass = createMockHass({
        callWS: ((params: Record<string, unknown> & { type: string }) => {
          if (params.type === 'abode_security/entities/sensors') {
            return Promise.resolve({ sensors: createMockSensors() });
          }
          if (params.type === 'abode_security/entities/alarms') {
            return Promise.resolve({ alarms: createMockAlarms() });
          }
          if (params.type === 'abode_security/actions/create') {
            createPayload = params;
            return Promise.resolve({ id: 'new-id' });
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await aTimeout(0);
      await elementUpdated(el);
      await setState(el, {
        _name: 'New One',
        _modes: ['home'],
        _delaySeconds: 5,
        _selectedSensors: ['binary_sensor.front_door'],
        _selectedAlarms: ['switch.abode_panic_alarm'],
      } as Partial<ActionEditor>);

      let saveFired = false;
      el.addEventListener('save', () => {
        saveFired = true;
      });

      // @ts-expect-error - calling private method for testing
      await el._handleSave();

      expect(createPayload).to.not.equal(null);
      expect(createPayload!.name).to.equal('New One');
      expect(createPayload!.modes).to.deep.equal(['home']);
      expect(createPayload!.delay_seconds).to.equal(5);
      expect(saveFired).to.equal(true);
    });

    it('calls updateAction with action_id when action prop is set', async () => {
      const existing = createMockAction({ id: 'existing-id', name: 'Old' });
      let updatePayload: Record<string, unknown> | null = null;
      const hass = createMockHass({
        callWS: ((params: Record<string, unknown> & { type: string }) => {
          if (params.type === 'abode_security/entities/sensors') {
            return Promise.resolve({ sensors: createMockSensors() });
          }
          if (params.type === 'abode_security/entities/alarms') {
            return Promise.resolve({ alarms: createMockAlarms() });
          }
          if (params.type === 'abode_security/actions/update') {
            updatePayload = params;
            return Promise.resolve(existing);
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ActionEditor>(html`
        <abode-action-editor
          .hass=${hass}
          .action=${existing}
        ></abode-action-editor>
      `);
      await aTimeout(0);
      await elementUpdated(el);
      // Override the populated form with edited values.
      await setState(el, {
        _name: 'Renamed',
        _modes: ['away'],
        _selectedSensors: ['binary_sensor.front_door'],
        _selectedAlarms: ['switch.abode_panic_alarm'],
      } as Partial<ActionEditor>);

      // @ts-expect-error - calling private method for testing
      await el._handleSave();

      expect(updatePayload).to.not.equal(null);
      expect(updatePayload!.action_id).to.equal('existing-id');
      expect(updatePayload!.name).to.equal('Renamed');
      expect(updatePayload!.modes).to.deep.equal(['away']);
    });

    it('sets _errors.form when the save WS rejects', async () => {
      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/entities/sensors') {
            return Promise.resolve({ sensors: createMockSensors() });
          }
          if (params.type === 'abode_security/entities/alarms') {
            return Promise.resolve({ alarms: createMockAlarms() });
          }
          if (params.type === 'abode_security/actions/create') {
            return Promise.reject(new Error('server rejected'));
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await aTimeout(0);
      await elementUpdated(el);
      await setState(el, {
        _name: 'Test',
        _modes: ['home'],
        _selectedSensors: ['binary_sensor.front_door'],
        _selectedAlarms: ['switch.abode_panic_alarm'],
      } as Partial<ActionEditor>);

      // @ts-expect-error - calling private method for testing
      await el._handleSave();

      // @ts-expect-error - accessing private property for testing
      expect(el._errors.form).to.equal('server rejected');
      // @ts-expect-error - accessing private property for testing
      expect(el._saving).to.equal(false, 'finally re-enables save button');
    });
  });

  describe('_populateForm (#31)', () => {
    it('populates state fields from the action prop on connect', async () => {
      const action = createMockAction({
        id: 'a1',
        name: 'Edited',
        modes: ['away', 'home'],
        delay_seconds: 15,
        sensor_entity_ids: ['binary_sensor.front_door'],
        alarm_entity_ids: ['switch.abode_panic_alarm', 'switch.abode_fire_alarm'],
      });
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor
          .hass=${hass}
          .action=${action}
        ></abode-action-editor>
      `);
      // _populateForm runs synchronously on connect (PR6 race fix), so
      // every field is populated before the load completes.
      // @ts-expect-error - accessing private property for testing
      expect(el._name).to.equal('Edited');
      // @ts-expect-error - accessing private property for testing
      expect(el._modes).to.deep.equal(['away', 'home']);
      // @ts-expect-error - accessing private property for testing
      expect(el._delaySeconds).to.equal(15);
      // @ts-expect-error - accessing private property for testing
      expect(el._selectedSensors).to.deep.equal(['binary_sensor.front_door']);
      // @ts-expect-error - accessing private property for testing
      expect(el._selectedAlarms).to.deep.equal([
        'switch.abode_panic_alarm',
        'switch.abode_fire_alarm',
      ]);
    });
  });

  describe('_toggleCategory tri-state (#31)', () => {
    // door has 2 sensors, motion has 1, window has 1 — see createMockSensors.
    const setupEditor = async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: createMockSensors(),
        _alarms: createMockAlarms(),
        _loading: false,
      } as Partial<ActionEditor>);
      return el;
    };

    it('reports neither selected nor partial when no sensors are picked', async () => {
      const el = await setupEditor();
      // @ts-expect-error - calling private method for testing
      expect(el._isCategorySelected('door')).to.equal(false);
      // @ts-expect-error - calling private method for testing
      expect(el._isCategoryPartial('door')).to.equal(false);
    });

    it('reports partial when some but not all sensors in a category are picked', async () => {
      const el = await setupEditor();
      await setState(el, {
        _selectedSensors: ['binary_sensor.front_door'],
      } as Partial<ActionEditor>);
      // door has 2 sensors, only 1 picked.
      // @ts-expect-error - calling private method for testing
      expect(el._isCategoryPartial('door')).to.equal(true);
      // @ts-expect-error - calling private method for testing
      expect(el._isCategorySelected('door')).to.equal(false);
    });

    it('reports selected when all sensors in a category are picked', async () => {
      const el = await setupEditor();
      await setState(el, {
        _selectedSensors: ['binary_sensor.front_door', 'binary_sensor.back_door'],
      } as Partial<ActionEditor>);
      // @ts-expect-error - calling private method for testing
      expect(el._isCategorySelected('door')).to.equal(true);
      // @ts-expect-error - calling private method for testing
      expect(el._isCategoryPartial('door')).to.equal(false);
    });

    it('toggleCategory selects every sensor when starting from empty/partial', async () => {
      const el = await setupEditor();
      await setState(el, {
        _selectedSensors: ['binary_sensor.front_door'], // partial
      } as Partial<ActionEditor>);
      // @ts-expect-error - calling private method for testing
      el._toggleCategory('door');
      await elementUpdated(el);
      // Strict deep-equal: catches both "didn't add the missing one" and
      // "accidentally added sensors from other categories" regressions.
      // @ts-expect-error - accessing private property for testing
      expect(el._selectedSensors).to.deep.equal([
        'binary_sensor.front_door',
        'binary_sensor.back_door',
      ]);
    });

    it('toggleCategory deselects all sensors in the category when starting from fully-selected', async () => {
      const el = await setupEditor();
      await setState(el, {
        _selectedSensors: [
          'binary_sensor.front_door',
          'binary_sensor.back_door',
          'binary_sensor.living_room_motion', // outside the door category
        ],
      } as Partial<ActionEditor>);
      // @ts-expect-error - calling private method for testing
      el._toggleCategory('door');
      await elementUpdated(el);
      // Door sensors removed, the motion sensor (outside the toggled
      // category) remains. This is the assertion that catches the
      // "filter accidentally removes all sensors" regression class.
      // @ts-expect-error - accessing private property for testing
      expect(el._selectedSensors).to.deep.equal([
        'binary_sensor.living_room_motion',
      ]);
    });
  });
});
