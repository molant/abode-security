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

      const sensors = createMockSensors();
      await setState(el, {
        _sensors: sensors,
        _alarms: createMockAlarms(),
        _loading: false,
        // Categories collapse by default (#113); expand all here so the
        // sensor-name substrings actually render to the shadow DOM.
        _expandedCategories: new Set(Object.keys(sensors)),
      } as Partial<ActionEditor>);

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
        garage_door: [{ entity_id: 'binary_sensor.garage', name: 'Garage Door', state: 'closed' }],
        gas: [{ entity_id: 'binary_sensor.gas_kitchen', name: 'Kitchen Gas', state: 'off' }],
      };
      await setState(el, {
        _sensors: wideSensors,
        _alarms: createMockAlarms(),
        _loading: false,
        // The category-headers-render assertion below is independent of the
        // collapse state, but the sensor-name assertions need items rendered.
        _expandedCategories: new Set(Object.keys(wideSensors)),
      } as Partial<ActionEditor>);

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

    it('renders semantic camera-detection categories with human labels', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);

      // Semantic categories are emitted by the backend for camera-style
      // smart-detect entities (UniFi Protect, Reolink, …) that have no
      // `device_class` but a recognizable translation_key (#135). The
      // picker has to render them with readable labels — "smoke_alarm"
      // alone wouldn't be enough.
      const semanticSensors: Record<string, SensorEntity[]> = {
        person: [
          {
            entity_id: 'binary_sensor.front_door_person_detected',
            name: 'Front Door Person',
            state: 'off',
          },
        ],
        vehicle: [
          {
            entity_id: 'binary_sensor.driveway_vehicle_detected',
            name: 'Driveway Vehicle',
            state: 'off',
          },
        ],
        smoke_alarm: [
          {
            entity_id: 'binary_sensor.kitchen_smoke_alarm_detected',
            name: 'Kitchen Smoke Alarm',
            state: 'off',
          },
        ],
        speaking: [
          {
            entity_id: 'binary_sensor.porch_speaking_detected',
            name: 'Porch Speaking',
            state: 'off',
          },
        ],
        object: [
          {
            entity_id: 'binary_sensor.backyard_object_detected',
            name: 'Backyard Object',
            state: 'off',
          },
        ],
      };

      await setState(el, {
        _sensors: semanticSensors,
        _alarms: createMockAlarms(),
        _loading: false,
        _expandedCategories: new Set(Object.keys(semanticSensors)),
      } as Partial<ActionEditor>);

      const categoryHeaders = Array.from(
        el.shadowRoot?.querySelectorAll('.category-header span') ?? [],
      ).map((s) => s.textContent ?? '');

      expect(
        categoryHeaders.some((l) => /\bperson detected\b/i.test(l)),
        `expected "Person detected" header, got: ${JSON.stringify(categoryHeaders)}`,
      ).to.equal(true);
      expect(
        categoryHeaders.some((l) => /\bvehicle detected\b/i.test(l)),
        `expected "Vehicle detected" header, got: ${JSON.stringify(categoryHeaders)}`,
      ).to.equal(true);
      expect(
        categoryHeaders.some((l) => /\bsmoke alarm detected\b/i.test(l)),
        `expected "Smoke alarm detected" header, got: ${JSON.stringify(categoryHeaders)}`,
      ).to.equal(true);
      expect(
        categoryHeaders.some((l) => /\bspeaking detected\b/i.test(l)),
        `expected "Speaking detected" header, got: ${JSON.stringify(categoryHeaders)}`,
      ).to.equal(true);
      expect(
        categoryHeaders.some((l) => /\bobject detected\b/i.test(l)),
        `expected "Object detected" header, got: ${JSON.stringify(categoryHeaders)}`,
      ).to.equal(true);
    });

    it('skips categories with zero sensors', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);

      // @ts-expect-error - accessing private property for testing
      el._sensors = {
        door: [{ entity_id: 'binary_sensor.front', name: 'Front Door', state: 'off' }],
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

    it('strips the "Abode Alarm" prefix and sorts alarms alphabetically (#120)', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);

      // Mirrors the real HA friendly_names that prompted #120.
      await setState(el, {
        _sensors: createMockSensors(),
        _alarms: [
          { entity_id: 'switch.abode_panic_alarm', name: 'Abode Alarm CO Alarm', type: 'panic' },
          {
            entity_id: 'switch.abode_smoke_co_alarm',
            name: 'Abode Alarm Smoke CO Alarm',
            type: 'fire',
          },
          { entity_id: 'switch.abode_smoke_alarm', name: 'Abode Alarm Smoke Alarm', type: 'fire' },
          {
            entity_id: 'switch.abode_burglar_alarm',
            name: 'Abode Alarm Burglar Alarm',
            type: 'panic',
          },
        ],
        _loading: false,
      } as Partial<ActionEditor>);

      const labels = Array.from(
        el.shadowRoot?.querySelectorAll<HTMLLabelElement>('.alarm-list label') ?? [],
      ).map((l) => l.textContent?.trim().replace(/\s+/g, ' ') ?? '');

      // The first row is the synthetic "None (notification only)" option.
      const alarmLabels = labels.slice(1);

      // Prefix stripped from every visible label.
      expect(alarmLabels.every((l) => !/Abode Alarm/i.test(l))).to.equal(
        true,
        `expected no "Abode Alarm" prefix in labels, got: ${JSON.stringify(alarmLabels)}`,
      );
      // Sorted alphabetically by the stripped label.
      expect(alarmLabels).to.deep.equal([
        'Burglar Alarm',
        'CO Alarm',
        'Smoke Alarm',
        'Smoke CO Alarm',
      ]);
    });

    it('renders the sensor area hint next to the name when present (#120)', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);

      const sensors: Record<string, SensorEntity[]> = {
        door: [
          {
            entity_id: 'binary_sensor.front_door',
            name: 'Front Door',
            state: 'off',
            area: 'Living Room',
          },
          // Sensor without area must still render without crashing or
          // showing a stray hint.
          { entity_id: 'binary_sensor.shed_door', name: 'Shed Door', state: 'off', area: null },
        ],
      };
      await setState(el, {
        _sensors: sensors,
        _alarms: createMockAlarms(),
        _loading: false,
        _expandedCategories: new Set(Object.keys(sensors)),
      } as Partial<ActionEditor>);

      const items = Array.from(
        el.shadowRoot?.querySelectorAll<HTMLLabelElement>('.category-items label') ?? [],
      );
      const frontDoor = items.find((l) => /Front Door/.test(l.textContent ?? ''));
      const shedDoor = items.find((l) => /Shed Door/.test(l.textContent ?? ''));

      expect(frontDoor?.querySelector('.entity-area')?.textContent).to.match(/Living Room/);
      // The area cell is always rendered (even when empty) so the
      // state-pill and info-button columns align across rows in the
      // grid layout (#119). Cells for sensors without an area should
      // be present but have no meaningful text content.
      const shedArea = shedDoor?.querySelector('.entity-area');
      expect(shedArea, 'expected an empty area cell, not its absence').to.exist;
      expect((shedArea?.textContent ?? '').trim()).to.equal('');
    });

    it('orders sensor categories by usefulness, others alphabetical at end (#120)', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);

      // Categories deliberately given in alphabetical order to prove the
      // priority comparator (not the input order) is what drives the render.
      const sensors: Record<string, SensorEntity[]> = {
        carbon_monoxide: [{ entity_id: 'binary_sensor.co', name: 'CO Sensor', state: 'off' }],
        door: [{ entity_id: 'binary_sensor.door', name: 'Front Door', state: 'off' }],
        moisture: [{ entity_id: 'binary_sensor.leak', name: 'Leak', state: 'off' }],
        motion: [{ entity_id: 'binary_sensor.motion', name: 'Living Motion', state: 'off' }],
        safety: [{ entity_id: 'binary_sensor.intrusion', name: 'Intrusion', state: 'off' }],
        smoke: [{ entity_id: 'binary_sensor.smoke', name: 'Smoke', state: 'off' }],
        window: [{ entity_id: 'binary_sensor.window', name: 'Kitchen Window', state: 'off' }],
      };
      await setState(el, {
        _sensors: sensors,
        _alarms: createMockAlarms(),
        _loading: false,
      } as Partial<ActionEditor>);

      const headers = Array.from(
        el.shadowRoot?.querySelectorAll('.category-header > span') ?? [],
      ).map((s) => (s.textContent ?? '').replace(/\s*\(\d+\)\s*$/, '').trim());

      // Priority categories come first, in the documented order. Unknown
      // categories (safety) sort alphabetically after. Underscores in the
      // device_class key render as spaces (`humanLabel` in action-editor).
      expect(headers).to.deep.equal([
        'door',
        'window',
        'motion',
        'smoke',
        'carbon monoxide',
        'moisture',
        'safety',
      ]);
    });

    it('falls through gracefully for alarm names without the "Abode Alarm" prefix (#120)', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);

      await setState(el, {
        _sensors: createMockSensors(),
        _alarms: [
          { entity_id: 'switch.abode_panic_alarm', name: 'Panic Alarm', type: 'panic' },
          { entity_id: 'switch.abode_fire_alarm', name: 'Fire Alarm', type: 'fire' },
        ],
        _loading: false,
      } as Partial<ActionEditor>);

      const labels = Array.from(
        el.shadowRoot?.querySelectorAll<HTMLLabelElement>('.alarm-list label') ?? [],
      ).map((l) => l.textContent?.trim().replace(/\s+/g, ' ') ?? '');

      // Drop the synthetic "None (notification only)" row.
      expect(labels.slice(1)).to.deep.equal(['Fire Alarm', 'Panic Alarm']);
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
      const retryButton = Array.from(el.shadowRoot?.querySelectorAll('button') ?? []).find((b) =>
        /retry/i.test(b.textContent ?? ''),
      );
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

    it('allows saving with no alarm selected (notification-only)', async () => {
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
      const ok = el._validate();
      expect(ok).to.equal(true);
      // @ts-expect-error - accessing private property for testing
      expect(el._errors.alarms).to.equal(undefined);
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
        <abode-action-editor .hass=${hass} .action=${existing}></abode-action-editor>
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
      // The action has two alarms in storage from before we restricted
      // the picker to single-select. The editor should coerce on
      // populate so the radio UI shows exactly one selected; the
      // second value is dropped only when the user saves (lazy
      // migration), not by mutating storage here.
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
        <abode-action-editor .hass=${hass} .action=${action}></abode-action-editor>
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
      // Single-select: only the first alarm survives in editor state.
      // @ts-expect-error - accessing private property for testing
      expect(el._selectedAlarms).to.deep.equal(['switch.abode_panic_alarm']);
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
      expect(el._selectedSensors).to.deep.equal(['binary_sensor.living_room_motion']);
    });
  });

  // --- #113 collapse + search -------------------------------------------
  // Sensor categories start collapsed; the disclosure button toggles each
  // independently. A search box filters items by name, auto-expands
  // categories that contain matches, and hides categories with zero
  // matches. Editing an existing action auto-expands categories that
  // already contain selected sensors so the user can see them.

  describe('sensor categories collapse + search (#113)', () => {
    const findHeaderForCategory = (el: ActionEditor, cat: string): HTMLElement | null => {
      const headers = Array.from(
        el.shadowRoot?.querySelectorAll<HTMLElement>('.category-header') ?? [],
      );
      return (
        headers.find((h) => {
          // Strip count suffix like " (2)" or " (1/2)" before matching.
          const label = (h.querySelector('span')?.textContent ?? '')
            .replace(/\s*\([^)]*\)\s*$/, '')
            .trim();
          return new RegExp(`^${cat.replace(/_/g, '[\\s_]')}$`, 'i').test(label);
        }) ?? null
      );
    };

    const findDisclosureForCategory = (el: ActionEditor, cat: string): HTMLButtonElement | null => {
      const header = findHeaderForCategory(el, cat);
      return header?.querySelector<HTMLButtonElement>('button.disclosure') ?? null;
    };

    it('starts with all sensor categories collapsed for a new action', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: createMockSensors(),
        _alarms: createMockAlarms(),
        _loading: false,
      } as Partial<ActionEditor>);

      // No `.category-items` rendered — all categories collapsed.
      const items = el.shadowRoot?.querySelectorAll('.category-items') ?? [];
      expect(items.length).to.equal(0, 'no category items should render when all collapsed');

      // All disclosure buttons should report aria-expanded="false".
      const disclosures = Array.from(el.shadowRoot?.querySelectorAll('button.disclosure') ?? []);
      expect(disclosures.length).to.be.greaterThan(0, 'expected disclosure buttons to exist');
      for (const d of disclosures) {
        expect(d.getAttribute('aria-expanded')).to.equal('false');
      }
    });

    it('auto-expands categories that contain selected sensors when editing', async () => {
      const action = createMockAction({
        // door has front+back; motion has living_room_motion; window is untouched.
        sensor_entity_ids: ['binary_sensor.front_door', 'binary_sensor.living_room_motion'],
        alarm_entity_ids: ['switch.abode_panic_alarm'],
      });
      const hass = createMockHass({
        callWS: ((params: { type: string }) => {
          if (params.type === 'abode_security/entities/sensors') {
            return Promise.resolve({ sensors: createMockSensors() });
          }
          if (params.type === 'abode_security/entities/alarms') {
            return Promise.resolve({ alarms: createMockAlarms() });
          }
          return Promise.resolve({ success: true });
        }) as HomeAssistant['callWS'],
      });

      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass} .action=${action}></abode-action-editor>
      `);
      // Let _loadEntities resolve and the seeding re-render.
      await aTimeout(0);
      await elementUpdated(el);

      expect(findDisclosureForCategory(el, 'door')?.getAttribute('aria-expanded')).to.equal(
        'true',
        'door has selections, should be expanded',
      );
      expect(findDisclosureForCategory(el, 'motion')?.getAttribute('aria-expanded')).to.equal(
        'true',
        'motion has selections, should be expanded',
      );
      expect(findDisclosureForCategory(el, 'window')?.getAttribute('aria-expanded')).to.equal(
        'false',
        'window has no selections, should stay collapsed',
      );
    });

    it('disclosure click toggles category expansion and aria-expanded', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: createMockSensors(),
        _alarms: createMockAlarms(),
        _loading: false,
      } as Partial<ActionEditor>);

      const disclosure = findDisclosureForCategory(el, 'door');
      expect(disclosure, 'expected a door disclosure button').to.exist;
      expect(disclosure!.getAttribute('aria-expanded')).to.equal('false');

      disclosure!.click();
      await elementUpdated(el);
      expect(disclosure!.getAttribute('aria-expanded')).to.equal('true');
      // Items now render in that category.
      const items = disclosure!.closest('.category')?.querySelector('.category-items');
      expect(items, 'category items should render when expanded').to.exist;

      disclosure!.click();
      await elementUpdated(el);
      expect(disclosure!.getAttribute('aria-expanded')).to.equal('false');
      // Items removed again.
      const itemsAfter = disclosure!.closest('.category')?.querySelector('.category-items');
      expect(itemsAfter, 'category items should disappear when collapsed again').to.not.exist;
    });

    it('clicking the disclosure does not change sensor selection', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: createMockSensors(),
        _alarms: createMockAlarms(),
        _loading: false,
        _selectedSensors: [],
      } as Partial<ActionEditor>);

      const disclosure = findDisclosureForCategory(el, 'door');
      disclosure!.click();
      await elementUpdated(el);

      // @ts-expect-error - accessing private property for testing
      expect(el._selectedSensors).to.deep.equal([]);
    });

    it('clicking the category header still toggles select-all when not filtering', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: createMockSensors(),
        _alarms: createMockAlarms(),
        _loading: false,
      } as Partial<ActionEditor>);

      const doorHeader = findHeaderForCategory(el, 'door');
      expect(doorHeader, 'expected a door header').to.exist;
      doorHeader!.click();
      await elementUpdated(el);

      // @ts-expect-error - accessing private property for testing
      expect(el._selectedSensors).to.have.members([
        'binary_sensor.front_door',
        'binary_sensor.back_door',
      ]);
    });

    it('filters sensor items by name when search has a query', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: createMockSensors(),
        _alarms: createMockAlarms(),
        _loading: false,
        _sensorSearch: 'front',
      } as Partial<ActionEditor>);

      // Only "Front Door" matches.
      const itemLabels = Array.from(
        el.shadowRoot?.querySelectorAll('.category-items label') ?? [],
      ).map((l) => l.textContent?.trim() ?? '');
      expect(itemLabels.length).to.equal(1);
      expect(itemLabels[0]).to.include('Front Door');

      // Non-matching categories should be hidden entirely (no header).
      expect(findHeaderForCategory(el, 'door'), 'door category visible').to.exist;
      expect(findHeaderForCategory(el, 'motion'), 'motion category hidden').to.not.exist;
      expect(findHeaderForCategory(el, 'window'), 'window category hidden').to.not.exist;
    });

    it('auto-expands a collapsed category when search matches an item inside it', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: createMockSensors(),
        _alarms: createMockAlarms(),
        _loading: false,
      } as Partial<ActionEditor>);
      // Confirm starting state is fully collapsed.
      expect(el.shadowRoot?.querySelectorAll('.category-items').length).to.equal(0);

      await setState(el, { _sensorSearch: 'motion' } as Partial<ActionEditor>);

      // Motion category becomes visible with its sensor.
      expect(el.shadowRoot?.textContent).to.include('Living Room Motion');
    });

    it('search is case-insensitive on the sensor name', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: createMockSensors(),
        _alarms: createMockAlarms(),
        _loading: false,
        _sensorSearch: 'BACK',
      } as Partial<ActionEditor>);

      const itemLabels = Array.from(
        el.shadowRoot?.querySelectorAll('.category-items label') ?? [],
      ).map((l) => l.textContent?.trim() ?? '');
      expect(itemLabels.length).to.equal(1);
      expect(itemLabels[0]).to.include('Back Door');
    });

    it('header select-all acts on filtered subset only while search is active', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: createMockSensors(),
        _alarms: createMockAlarms(),
        _loading: false,
        // Matches only front_door among the two door sensors.
        _sensorSearch: 'front',
      } as Partial<ActionEditor>);

      const doorHeader = findHeaderForCategory(el, 'door');
      doorHeader!.click();
      await elementUpdated(el);

      // Only the visible match was selected — back_door is filtered out and
      // must not be silently bulk-selected.
      // @ts-expect-error - accessing private property for testing
      expect(el._selectedSensors).to.deep.equal(['binary_sensor.front_door']);
    });

    it('keeps DOM ids unique when two category keys sanitize to the same safeKey', async () => {
      // Two distinct backend keys collapse to the same `safeKey` under
      // /[^A-Za-z0-9_-]/g → '-'. Without index-based disambiguation the
      // two `.category-items` containers would share an id and the
      // disclosure `aria-controls` would point at an ambiguous target
      // (#113).
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      const collidingKeys = ['smoke detector', 'smoke-detector'];
      const sensors: Record<string, SensorEntity[]> = {
        [collidingKeys[0]]: [
          { entity_id: 'binary_sensor.kitchen_smoke', name: 'Kitchen Smoke', state: 'off' },
        ],
        [collidingKeys[1]]: [
          { entity_id: 'binary_sensor.bedroom_smoke', name: 'Bedroom Smoke', state: 'off' },
        ],
      };
      await setState(el, {
        _sensors: sensors,
        _alarms: createMockAlarms(),
        _loading: false,
        _expandedCategories: new Set(collidingKeys),
      } as Partial<ActionEditor>);

      const itemContainers = Array.from(
        el.shadowRoot?.querySelectorAll<HTMLElement>('.category-items[id]') ?? [],
      );
      const ids = itemContainers.map((d) => d.id);
      expect(ids.length).to.equal(2);
      expect(new Set(ids).size).to.equal(
        2,
        `expected two unique ids for colliding sanitized keys, got: ${ids.join(', ')}`,
      );
    });

    it('humanizes underscores in the disclosure aria-label', async () => {
      // The visible header text replaces underscores with spaces, but
      // `aria-label` previously used the raw `category` — screen readers
      // would announce "Expand garage_door" instead of "Expand garage
      // door" (#113).
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      const sensors: Record<string, SensorEntity[]> = {
        garage_door: [{ entity_id: 'binary_sensor.garage', name: 'Garage Door', state: 'closed' }],
      };
      await setState(el, {
        _sensors: sensors,
        _alarms: createMockAlarms(),
        _loading: false,
      } as Partial<ActionEditor>);

      const disclosure = el.shadowRoot?.querySelector<HTMLButtonElement>('button.disclosure');
      expect(disclosure, 'expected a disclosure button').to.exist;
      expect(disclosure!.getAttribute('aria-label')).to.equal('Expand garage door');

      disclosure!.click();
      await elementUpdated(el);
      expect(disclosure!.getAttribute('aria-label')).to.equal('Collapse garage door');
    });

    it('sanitizes the category key when building aria-controls / items id', async () => {
      // Backend `device_class` keys are typically snake_case identifiers,
      // but the SensorsByCategory shape is keyed by `string` — a key with
      // a space or other non-token character would silently turn
      // `aria-controls` into a multi-id reference and create an invalid
      // DOM id. Sanitize defensively (#113).
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      const unsafeKey = 'smoke detector';
      const sensors: Record<string, SensorEntity[]> = {
        [unsafeKey]: [
          { entity_id: 'binary_sensor.kitchen_smoke', name: 'Kitchen Smoke', state: 'off' },
        ],
      };
      await setState(el, {
        _sensors: sensors,
        _alarms: createMockAlarms(),
        _loading: false,
        _expandedCategories: new Set([unsafeKey]),
      } as Partial<ActionEditor>);

      const disclosure = el.shadowRoot?.querySelector<HTMLButtonElement>('button.disclosure');
      expect(disclosure, 'expected a disclosure button').to.exist;
      const ariaControls = disclosure!.getAttribute('aria-controls') ?? '';
      // The reference must be a single token (no whitespace) and must
      // resolve to a real element in the same root.
      expect(ariaControls).to.not.match(/\s/, 'aria-controls must be a single id token');
      expect(ariaControls.length).to.be.greaterThan(0);
      const itemsContainer = el.shadowRoot?.getElementById(ariaControls);
      expect(itemsContainer, 'aria-controls must resolve to the items container').to.exist;
    });

    it('omits aria-controls on the disclosure while the category is collapsed', async () => {
      // The controlled element (`<div id=itemsId class="category-items">`)
      // is only rendered while expanded. Pointing `aria-controls` at a
      // missing id is invalid ARIA — omit the attribute until the
      // target exists (#113).
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: createMockSensors(),
        _alarms: createMockAlarms(),
        _loading: false,
      } as Partial<ActionEditor>);

      const disclosure = el.shadowRoot?.querySelector<HTMLButtonElement>('button.disclosure');
      expect(disclosure, 'expected a disclosure button').to.exist;
      expect(disclosure!.hasAttribute('aria-controls')).to.equal(
        false,
        'aria-controls must be absent while the controlled element is not in the DOM',
      );

      disclosure!.click();
      await elementUpdated(el);
      const controls = disclosure!.getAttribute('aria-controls');
      expect(controls, 'aria-controls must be set once the items container renders').to.not.equal(
        null,
      );
      const target = el.shadowRoot?.getElementById(controls!);
      expect(target, 'aria-controls must resolve to the items container').to.exist;
    });

    it('hides the disclosure button while a search query is active', async () => {
      // Regression: while filtering, `isExpanded` is
      // force-true via `isFiltering || ...`, so a chevron click had no
      // visible effect but silently mutated `_expandedCategories` —
      // clearing the search then restored a different collapse state than
      // the user thought they left. Hiding the button removes the trap.
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: createMockSensors(),
        _alarms: createMockAlarms(),
        _loading: false,
      } as Partial<ActionEditor>);

      // Baseline: disclosures present without a search query.
      const beforeCount = el.shadowRoot?.querySelectorAll('button.disclosure').length ?? 0;
      expect(beforeCount).to.be.greaterThan(0);

      await setState(el, { _sensorSearch: 'front' } as Partial<ActionEditor>);
      expect(el.shadowRoot?.querySelectorAll('button.disclosure').length).to.equal(
        0,
        'disclosure must be hidden while a search query is active',
      );

      await setState(el, { _sensorSearch: '' } as Partial<ActionEditor>);
      const afterCount = el.shadowRoot?.querySelectorAll('button.disclosure').length ?? 0;
      expect(afterCount).to.equal(
        beforeCount,
        'disclosure must return after the search query is cleared',
      );
    });
  });

  // The original "Home Test" bug looked correctly configured in the editor
  // — only after a separate diagnostic pass did we discover the four chosen
  // sensors had been unavailable for a week. These tests pin the UX
  // surface that would have made it obvious at picking time.
  describe('sensor availability surfacing', () => {
    // Construct a fixture where two sensors in the same category have
    // diverging live state in hass.states: the snapshot returned by the
    // WS endpoint says one is "off", but hass.states marks it
    // "unavailable". The component must render the live value (so
    // diagnostics stay current as sensors flap), not the snapshot.
    function buildFixtureSensors() {
      return {
        door: [
          { entity_id: 'binary_sensor.front_door', name: 'Front Door', state: 'off' },
          { entity_id: 'binary_sensor.back_door', name: 'Back Door', state: 'off' },
          { entity_id: 'binary_sensor.dead_door', name: 'Dead Door', state: 'off' },
        ],
      } as Record<string, SensorEntity[]>;
    }

    function buildHass(): HomeAssistant {
      return createMockHass({
        states: {
          'binary_sensor.front_door': {
            entity_id: 'binary_sensor.front_door',
            state: 'off',
          },
          'binary_sensor.back_door': {
            entity_id: 'binary_sensor.back_door',
            state: 'on',
          },
          'binary_sensor.dead_door': {
            entity_id: 'binary_sensor.dead_door',
            state: 'unavailable',
          },
        },
      });
    }

    it('renders a state pill per sensor with device-class-aware labels', async () => {
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${buildHass()}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: buildFixtureSensors(),
        _alarms: createMockAlarms(),
        _loading: false,
        _expandedCategories: new Set(['door']),
      } as Partial<ActionEditor>);

      const pills = Array.from(el.shadowRoot?.querySelectorAll('.state-pill') ?? []).map((p) => ({
        classes: p.className,
        text: (p.textContent ?? '').trim(),
      }));
      // door device_class label map: on=open, off=closed.
      expect(pills.some((p) => /open/i.test(p.text) && /\bon\b/.test(p.classes))).to.equal(
        true,
        `expected an "open" pill for the "on" sensor, got: ${JSON.stringify(pills)}`,
      );
      expect(pills.some((p) => /closed/i.test(p.text) && /\boff\b/.test(p.classes))).to.equal(
        true,
        `expected a "closed" pill for the "off" sensor, got: ${JSON.stringify(pills)}`,
      );
      expect(
        pills.some((p) => /unavailable/i.test(p.text) && /\bunavailable\b/.test(p.classes)),
      ).to.equal(
        true,
        `expected an "unavailable" pill for the offline sensor, got: ${JSON.stringify(pills)}`,
      );
    });

    it('partitions unavailable sensors to the bottom of each category', async () => {
      // Backend returns Dead Door first alphabetically — without the
      // partition step, the dead sensor would render above the live ones.
      const reordered = {
        door: [
          { entity_id: 'binary_sensor.dead_door', name: 'Dead Door', state: 'off' },
          { entity_id: 'binary_sensor.front_door', name: 'Front Door', state: 'off' },
          { entity_id: 'binary_sensor.back_door', name: 'Back Door', state: 'off' },
        ],
      } as Record<string, SensorEntity[]>;

      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${buildHass()}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: reordered,
        _alarms: createMockAlarms(),
        _loading: false,
        _expandedCategories: new Set(['door']),
      } as Partial<ActionEditor>);

      const names = Array.from(
        el.shadowRoot?.querySelectorAll('.sensor-row .entity-name') ?? [],
      ).map((n) => (n.textContent ?? '').trim());
      // Dead must be last; relative order of live sensors stays as the
      // backend supplied them.
      expect(names[names.length - 1]).to.equal('Dead Door');
      expect(names.indexOf('Front Door')).to.be.lessThan(names.indexOf('Dead Door'));
      expect(names.indexOf('Back Door')).to.be.lessThan(names.indexOf('Dead Door'));
    });

    it('appends an unavailable count to the category header when any sensor is offline', async () => {
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${buildHass()}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: buildFixtureSensors(),
        _alarms: createMockAlarms(),
        _loading: false,
        _expandedCategories: new Set(['door']),
      } as Partial<ActionEditor>);

      const header = el.shadowRoot?.querySelector('.category-header > span');
      // The count is over the whole category (3 sensors), one of which is
      // unavailable in hass.states. No comma between the totals — the
      // leading separator is a plain space so the red span only colours
      // the meaningful "N unavailable" string.
      expect(header?.textContent ?? '').to.match(/door\s*\(3\)\s+1\s*unavailable/i);
    });

    it('omits the unavailable count when all sensors in a category are healthy', async () => {
      // Same snapshot, but every entity is healthy in hass.states.
      const healthyHass = createMockHass({
        states: {
          'binary_sensor.front_door': {
            entity_id: 'binary_sensor.front_door',
            state: 'off',
          },
          'binary_sensor.back_door': {
            entity_id: 'binary_sensor.back_door',
            state: 'off',
          },
          'binary_sensor.dead_door': {
            entity_id: 'binary_sensor.dead_door',
            state: 'off',
          },
        },
      });
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${healthyHass}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: buildFixtureSensors(),
        _alarms: createMockAlarms(),
        _loading: false,
        _expandedCategories: new Set(['door']),
      } as Partial<ActionEditor>);

      const header = el.shadowRoot?.querySelector('.category-header > span');
      expect((header?.textContent ?? '').toLowerCase()).to.not.include('unavailable');
    });

    it('clicking the info button fires hass-more-info with the entity_id (and does not toggle the checkbox)', async () => {
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${buildHass()}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: buildFixtureSensors(),
        _alarms: createMockAlarms(),
        _loading: false,
        _expandedCategories: new Set(['door']),
      } as Partial<ActionEditor>);

      const events: CustomEvent[] = [];
      el.addEventListener('hass-more-info', (e) => events.push(e as CustomEvent));

      // Pick the row for the dead sensor — the realistic case the user
      // would click to inspect why nothing is firing.
      const rows = Array.from(el.shadowRoot?.querySelectorAll('.sensor-row') ?? []);
      const deadRow = rows.find((r) =>
        (r.querySelector('.entity-name')?.textContent ?? '').includes('Dead Door'),
      );
      expect(deadRow, 'expected a row for Dead Door').to.exist;
      const infoButton = deadRow!.querySelector<HTMLButtonElement>('button.info-button');
      expect(infoButton, 'expected an info button in the row').to.exist;

      // Sanity: the checkbox starts unchecked.
      const checkbox = deadRow!.querySelector<HTMLInputElement>('input[type="checkbox"]');
      expect(checkbox?.checked).to.equal(false);

      infoButton!.click();
      await elementUpdated(el);

      expect(events.length).to.equal(1);
      expect(events[0].detail).to.deep.equal({ entityId: 'binary_sensor.dead_door' });
      expect(events[0].bubbles).to.equal(true);
      expect(events[0].composed).to.equal(true);
      // The button is a sibling of the <label>, so the click must not
      // toggle the selection — otherwise an "inspect this sensor" click
      // silently adds it to the action.
      expect(checkbox?.checked).to.equal(false);
    });

    it('falls back to the snapshot state when hass.states does not yet have the entity', async () => {
      // A hass with an empty `states` map (e.g. cold-start) plus a
      // snapshot from fetchSensors that says "off" should render
      // "closed", not "unavailable".
      const coldHass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${coldHass}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: {
          door: [{ entity_id: 'binary_sensor.front_door', name: 'Front Door', state: 'off' }],
        },
        _alarms: createMockAlarms(),
        _loading: false,
        _expandedCategories: new Set(['door']),
      } as Partial<ActionEditor>);

      // Default fallback in getEntityState is "unavailable", but
      // _renderSensorRow passes sensor.state as the fallback, so the row
      // should still render as "closed" with no warning.
      const pill = el.shadowRoot?.querySelector('.state-pill');
      expect((pill?.className ?? '').toLowerCase()).to.include('off');
      expect((pill?.textContent ?? '').toLowerCase()).to.include('closed');
      const row = el.shadowRoot?.querySelector('.sensor-row');
      expect(row?.classList.contains('unavailable')).to.equal(
        false,
        'snapshot-driven row should not be marked unavailable',
      );
    });

    // Pinning the predicate consolidation from the review: `unknown` must
    // count as unavailable everywhere (pill, partition order, header
    // count) — otherwise we re-introduce the split-source-of-truth bug
    // where a red "unavailable" pill could coexist with a header that
    // says everything's fine. Centralised in `isUnavailableState` in
    // `types.ts`.
    it('treats `unknown` identically to `unavailable` across pill, partition, and header', async () => {
      const sensors = {
        door: [
          { entity_id: 'binary_sensor.alive', name: 'Alive Door', state: 'off' },
          { entity_id: 'binary_sensor.spooky', name: 'Spooky Door', state: 'off' },
        ],
      } as Record<string, SensorEntity[]>;
      const hass = createMockHass({
        states: {
          'binary_sensor.alive': { entity_id: 'binary_sensor.alive', state: 'off' },
          // Real-world cause: integration just came up, sensor entity
          // is registered but hasn't reported yet.
          'binary_sensor.spooky': { entity_id: 'binary_sensor.spooky', state: 'unknown' },
        },
      });
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: sensors,
        _alarms: createMockAlarms(),
        _loading: false,
        _expandedCategories: new Set(['door']),
      } as Partial<ActionEditor>);

      // Header count must include the `unknown` row.
      const header = el.shadowRoot?.querySelector('.category-header > span');
      expect(header?.textContent ?? '').to.match(/door\s*\(2\)\s+1\s*unavailable/i);

      // Spooky Door must render with the unavailable pill (red) and
      // sort to the bottom of the category.
      const names = Array.from(
        el.shadowRoot?.querySelectorAll('.sensor-row .entity-name') ?? [],
      ).map((n) => (n.textContent ?? '').trim());
      expect(names[names.length - 1]).to.equal('Spooky Door');

      const rows = Array.from(el.shadowRoot?.querySelectorAll('.sensor-row') ?? []);
      const spookyRow = rows.find((r) =>
        (r.querySelector('.entity-name')?.textContent ?? '').includes('Spooky Door'),
      );
      expect(spookyRow?.classList.contains('unavailable')).to.equal(true);
      const spookyPill = spookyRow?.querySelector('.state-pill');
      expect((spookyPill?.className ?? '').toLowerCase()).to.include('unavailable');
    });

    it('uses the device-class-specific label for motion (`detected` / `clear`)', async () => {
      const hass = createMockHass({
        states: {
          'binary_sensor.hall_motion': {
            entity_id: 'binary_sensor.hall_motion',
            state: 'on',
          },
          'binary_sensor.bath_motion': {
            entity_id: 'binary_sensor.bath_motion',
            state: 'off',
          },
        },
      });
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: {
          motion: [
            { entity_id: 'binary_sensor.hall_motion', name: 'Hall Motion', state: 'on' },
            { entity_id: 'binary_sensor.bath_motion', name: 'Bath Motion', state: 'off' },
          ],
        },
        _alarms: createMockAlarms(),
        _loading: false,
        _expandedCategories: new Set(['motion']),
      } as Partial<ActionEditor>);

      const pillTexts = Array.from(el.shadowRoot?.querySelectorAll('.state-pill') ?? []).map((p) =>
        (p.textContent ?? '').trim(),
      );
      // For motion, the on/off labels are "detected" / "clear" — not
      // the door-class "open" / "closed".
      expect(pillTexts.some((t) => /detected/i.test(t))).to.equal(
        true,
        `expected a "detected" pill, got: ${JSON.stringify(pillTexts)}`,
      );
      expect(pillTexts.some((t) => /clear/i.test(t))).to.equal(
        true,
        `expected a "clear" pill, got: ${JSON.stringify(pillTexts)}`,
      );
      // And critically — no "open"/"closed" should leak through.
      expect(pillTexts.some((t) => /\bopen\b/i.test(t))).to.equal(false);
    });

    it('falls through to the raw state value for unmapped device classes', async () => {
      // A device_class outside `STATE_LABELS` (e.g. `lock`) should render
      // the raw state — better than guessing a wrong label. The lock
      // device class isn't a binary_sensor in practice, but the
      // fall-through behaviour is what matters: any unknown class works
      // the same way.
      const hass = createMockHass({
        states: {
          'binary_sensor.weird': { entity_id: 'binary_sensor.weird', state: 'jammed' },
        },
      });
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: {
          tamper: [{ entity_id: 'binary_sensor.weird', name: 'Weird', state: 'jammed' }],
        },
        _alarms: createMockAlarms(),
        _loading: false,
        _expandedCategories: new Set(['tamper']),
      } as Partial<ActionEditor>);

      const pill = el.shadowRoot?.querySelector('.state-pill');
      expect((pill?.textContent ?? '').toLowerCase()).to.include('jammed');
    });

    // Parallel to actions-tab's "updates the badge count when hass.states
    // changes (live)" test — without this, a refactor that pre-computes
    // sensor state at load time (instead of reading hass.states at
    // render) would silently break the live-update path with no test
    // failure.
    it('updates pill, partition order, and header live when hass is reassigned', async () => {
      const sensors = {
        door: [
          { entity_id: 'binary_sensor.front', name: 'Front', state: 'off' },
          { entity_id: 'binary_sensor.back', name: 'Back', state: 'off' },
        ],
      } as Record<string, SensorEntity[]>;

      // Initial paint: Front is unavailable in hass.states.
      const initialHass = createMockHass({
        states: {
          'binary_sensor.front': {
            entity_id: 'binary_sensor.front',
            state: 'unavailable',
          },
          'binary_sensor.back': { entity_id: 'binary_sensor.back', state: 'off' },
        },
      });
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${initialHass}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: sensors,
        _alarms: createMockAlarms(),
        _loading: false,
        _expandedCategories: new Set(['door']),
      } as Partial<ActionEditor>);

      let names = Array.from(el.shadowRoot?.querySelectorAll('.sensor-row .entity-name') ?? []).map(
        (n) => (n.textContent ?? '').trim(),
      );
      expect(names[names.length - 1]).to.equal('Front', 'Front (unavailable) sorts last');
      let header = el.shadowRoot?.querySelector('.category-header > span');
      expect(header?.textContent ?? '').to.match(/door\s*\(2\)\s+1\s*unavailable/i);

      // HA pushes a state change: Front is back online. The whole hass
      // object gets reassigned (this is how HA's frontend propagates
      // state changes), which Lit's `@property` decorator turns into a
      // re-render. No subscribeEvents or refetch needed.
      el.hass = createMockHass({
        states: {
          'binary_sensor.front': { entity_id: 'binary_sensor.front', state: 'off' },
          'binary_sensor.back': { entity_id: 'binary_sensor.back', state: 'off' },
        },
      });
      await elementUpdated(el);

      names = Array.from(el.shadowRoot?.querySelectorAll('.sensor-row .entity-name') ?? []).map(
        (n) => (n.textContent ?? '').trim(),
      );
      // Healthy now — partition unchanged from backend order.
      expect(names).to.deep.equal(['Front', 'Back']);
      header = el.shadowRoot?.querySelector('.category-header > span');
      expect((header?.textContent ?? '').toLowerCase()).to.not.include('unavailable');
      const allPillsHealthy = Array.from(
        el.shadowRoot?.querySelectorAll('.state-pill') ?? [],
      ).every((p) => !(p.className ?? '').includes('unavailable'));
      expect(allPillsHealthy).to.equal(true);
    });
  });

  // The Abode timeline only meaningfully surfaces one alarm at a time
  // (911 dispatch is downstream of whichever alarm code fires), so the
  // picker enforces single-select. Backend storage still accepts an
  // array — these tests pin the editor-side semantics: radios, lazy
  // migration of legacy multi-alarm actions, validation copy.
  describe('alarm single-select', () => {
    it('renders alarms as radios in a shared group', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: createMockSensors(),
        _alarms: createMockAlarms(),
        _loading: false,
      } as Partial<ActionEditor>);

      const inputs = Array.from(
        el.shadowRoot?.querySelectorAll<HTMLInputElement>('.alarm-list input') ?? [],
      );
      expect(inputs.length).to.be.greaterThan(0);
      const types = new Set(inputs.map((i) => i.type));
      expect(types.has('radio')).to.equal(true, 'expected radio inputs');
      expect(types.has('checkbox')).to.equal(false, 'no checkboxes should remain');
      const names = new Set(inputs.map((i) => i.name));
      expect(names.size).to.equal(
        1,
        `all alarm radios must share a name attribute to get native single-select; got ${[...names]}`,
      );
    });

    it('clicking "None (notification only)" clears the alarm selection', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: createMockSensors(),
        _alarms: createMockAlarms(),
        _loading: false,
        _selectedAlarms: ['switch.abode_panic_alarm'],
      } as Partial<ActionEditor>);

      const noneRadio = Array.from(
        el.shadowRoot?.querySelectorAll<HTMLInputElement>('.alarm-list input[type=radio]') ?? [],
      ).find((r) => r.value === '');
      expect(noneRadio, 'expected a notification-only radio').to.exist;
      noneRadio!.click();
      await elementUpdated(el);

      // @ts-expect-error - accessing private property for testing
      expect(el._selectedAlarms).to.deep.equal([]);
    });

    it('selecting one alarm replaces a prior selection (no multi-select)', async () => {
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: createMockSensors(),
        _alarms: createMockAlarms(),
        _loading: false,
        _selectedAlarms: ['switch.abode_panic_alarm'],
      } as Partial<ActionEditor>);

      // Pick a different radio via its DOM change event — same path
      // the user takes. The change handler should *replace*, not toggle.
      const fireRadio = Array.from(
        el.shadowRoot?.querySelectorAll<HTMLInputElement>('.alarm-list input[type=radio]') ?? [],
      ).find((r) => r.value === 'switch.abode_fire_alarm');
      expect(fireRadio, 'expected a Fire Alarm radio').to.exist;
      fireRadio!.click();
      await elementUpdated(el);

      // @ts-expect-error - accessing private property for testing
      expect(el._selectedAlarms).to.deep.equal(['switch.abode_fire_alarm']);
    });

    it('applies a responsive grid layout to the alarm list', async () => {
      // Layout assertion: the .alarm-list container must use CSS grid
      // with auto-fit columns so the panel reflows from 1 to 2-3
      // columns based on width. Without this rule the list collapses
      // back to the old single-column flex layout.
      const hass = createMockHass();
      const el = await fixture<ActionEditor>(html`
        <abode-action-editor .hass=${hass}></abode-action-editor>
      `);
      await setState(el, {
        _sensors: createMockSensors(),
        _alarms: createMockAlarms(),
        _loading: false,
      } as Partial<ActionEditor>);

      const list = el.shadowRoot?.querySelector('.alarm-list');
      expect(list, 'expected an .alarm-list container').to.exist;
      const computed = getComputedStyle(list as Element);
      expect(computed.display).to.equal('grid');
      // grid-template-columns resolves to track sizes once laid out;
      // the panel sets `repeat(auto-fit, minmax(180px, 1fr))`, which
      // computed style serialises as one or more `<length>` track
      // sizes. We don't pin the exact pixel layout (depends on
      // viewport), only that the property is set to a non-empty,
      // non-`none` value — proving auto-fit is in effect.
      expect(computed.gridTemplateColumns).to.not.equal('');
      expect(computed.gridTemplateColumns).to.not.equal('none');
    });
  });
});
