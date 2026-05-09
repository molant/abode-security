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
});
