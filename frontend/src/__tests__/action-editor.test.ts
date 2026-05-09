/**
 * Tests for the ActionEditor component.
 *
 * Note: These tests focus on rendering behavior with pre-loaded data.
 * API integration is tested via E2E and integration tests.
 */

import { expect, fixture, html } from '@open-wc/testing';

import '../action-editor.js';
import type { ActionEditor } from '../action-editor.js';
import type { SensorEntity } from '../types.js';
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

      expect(el.shadowRoot?.textContent).to.include('New Action');
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

      expect(el.shadowRoot?.textContent).to.include('Edit Action');
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

    it('dispatches cancel event on Escape key', async () => {
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

      // Dispatch Escape key event
      const overlay = el.shadowRoot?.querySelector('.editor-overlay') as HTMLElement;
      overlay?.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));

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
    it('editor overlay has proper ARIA attributes', async () => {
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

      const dialog = el.shadowRoot?.querySelector('.editor-dialog');
      expect(dialog?.getAttribute('role')).to.equal('dialog');
      expect(dialog?.getAttribute('aria-modal')).to.equal('true');
    });
  });
});
