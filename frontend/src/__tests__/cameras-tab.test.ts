/**
 * Tests for the CamerasTab component.
 */

import { expect, fixture, html } from '@open-wc/testing';
import sinon from 'sinon';

import '../cameras-tab.js';
import type { CamerasTab } from '../cameras-tab.js';
import type { AbodeCamera } from '../types.js';
import { createMockHass, elementUpdated, setState } from './test-helpers.js';

function createMockCamera(overrides: Partial<AbodeCamera> = {}): AbodeCamera {
  return {
    entity_id: 'camera.front',
    name: 'Front Camera',
    area: null,
    ...overrides,
  };
}

describe('CamerasTab', () => {
  describe('renders empty state when no cameras returned', () => {
    it('shows empty state message', async () => {
      const hass = createMockHass();
      const el = await fixture<CamerasTab>(html`
        <abode-cameras-tab .hass=${hass}></abode-cameras-tab>
      `);

      await setState(el, { _cameras: [], _loading: false } as Partial<CamerasTab>);

      expect(el.shadowRoot?.textContent).to.include('No cameras found in Home Assistant');
    });
  });

  describe('renders a card per camera with name and area chip', () => {
    it('renders camera card with name', async () => {
      const hass = createMockHass();
      const el = await fixture<CamerasTab>(html`
        <abode-cameras-tab .hass=${hass}></abode-cameras-tab>
      `);

      const cameras = [
        createMockCamera({ entity_id: 'camera.front', name: 'Front Camera', area: 'Living Room' }),
      ];
      await setState(el, { _cameras: cameras, _loading: false } as Partial<CamerasTab>);

      expect(el.shadowRoot?.textContent).to.include('Front Camera');
    });

    it('renders area chip when area is set', async () => {
      const hass = createMockHass();
      const el = await fixture<CamerasTab>(html`
        <abode-cameras-tab .hass=${hass}></abode-cameras-tab>
      `);

      await setState(el, {
        _cameras: [createMockCamera({ area: 'Kitchen' })],
        _loading: false,
      } as Partial<CamerasTab>);

      const chip = el.shadowRoot?.querySelector('.area-chip');
      expect(chip).to.exist;
      expect(chip?.textContent?.trim()).to.equal('Kitchen');
    });

    it('does not render area chip when area is null', async () => {
      const hass = createMockHass();
      const el = await fixture<CamerasTab>(html`
        <abode-cameras-tab .hass=${hass}></abode-cameras-tab>
      `);

      await setState(el, {
        _cameras: [createMockCamera({ area: null })],
        _loading: false,
      } as Partial<CamerasTab>);

      expect(el.shadowRoot?.querySelector('.area-chip')).to.not.exist;
    });

    it('renders an ha-camera-stream element per camera', async () => {
      const hass = createMockHass();
      const el = await fixture<CamerasTab>(html`
        <abode-cameras-tab .hass=${hass}></abode-cameras-tab>
      `);

      await setState(el, {
        _cameras: [createMockCamera()],
        _loading: false,
      } as Partial<CamerasTab>);

      expect(el.shadowRoot?.querySelector('ha-camera-stream')).to.exist;
    });
  });

  describe('shows an error and retry button when fetchCameras rejects', () => {
    it('shows error message and retry button', async () => {
      const hass = createMockHass();
      const el = await fixture<CamerasTab>(html`
        <abode-cameras-tab .hass=${hass}></abode-cameras-tab>
      `);

      await setState(el, {
        _error: 'Connection refused',
        _loading: false,
      } as Partial<CamerasTab>);

      expect(el.shadowRoot?.textContent).to.include('Connection refused');
      expect(el.shadowRoot?.querySelector('.retry-button')).to.exist;
    });
  });

  describe('scrolls and highlights selected camera when selectedCameraEntityId matches', () => {
    it('calls scrollIntoView on the matching card', async () => {
      const hass = createMockHass();
      const el = await fixture<CamerasTab>(html`
        <abode-cameras-tab .hass=${hass}></abode-cameras-tab>
      `);

      const cameras = [createMockCamera({ entity_id: 'camera.front', name: 'Front Camera' })];
      await setState(el, { _cameras: cameras, _loading: false } as Partial<CamerasTab>);

      const card = el.shadowRoot?.querySelector<HTMLElement>('[data-entity-id="camera.front"]');
      expect(card).to.exist;

      const scrollSpy = sinon.stub(card!, 'scrollIntoView');

      el.selectedCameraEntityId = 'camera.front';
      await elementUpdated(el);

      // Wait for requestAnimationFrame
      await new Promise((resolve) => requestAnimationFrame(resolve));

      expect(scrollSpy.calledOnce).to.be.true;
    });
  });

  describe('does not scroll or error when selectedCameraEntityId points to a missing camera', () => {
    it('renders normally when the selected entity is not in the list', async () => {
      const hass = createMockHass();
      const el = await fixture<CamerasTab>(html`
        <abode-cameras-tab .hass=${hass}></abode-cameras-tab>
      `);

      await setState(el, {
        _cameras: [createMockCamera({ entity_id: 'camera.other', name: 'Other' })],
        _loading: false,
      } as Partial<CamerasTab>);

      // Should not throw
      el.selectedCameraEntityId = 'camera.deleted';
      await elementUpdated(el);
      await new Promise((resolve) => requestAnimationFrame(resolve));

      // No error state, still shows the other camera
      expect(el.shadowRoot?.querySelector('.error')).to.not.exist;
      expect(el.shadowRoot?.textContent).to.include('Other');
    });
  });

  describe('tap on a card opens the more-info dialog', () => {
    it('dispatches a bubbling, composed hass-more-info event with the entity_id', async () => {
      const hass = createMockHass();
      const el = await fixture<CamerasTab>(html`
        <abode-cameras-tab .hass=${hass}></abode-cameras-tab>
      `);

      await setState(el, {
        _cameras: [createMockCamera({ entity_id: 'camera.front' })],
        _loading: false,
      } as Partial<CamerasTab>);

      const events: CustomEvent[] = [];
      el.addEventListener('hass-more-info', (ev) => events.push(ev as CustomEvent));

      const card = el.shadowRoot?.querySelector<HTMLElement>('[data-entity-id="camera.front"]');
      expect(card).to.exist;
      card!.click();

      expect(events).to.have.lengthOf(1);
      expect(events[0].detail).to.deep.equal({ entityId: 'camera.front' });
      expect(events[0].bubbles).to.be.true;
      expect(events[0].composed).to.be.true;
    });
  });

  describe('deep-link arrival auto-opens more-info', () => {
    it('fires hass-more-info once when the selected camera is present in the list', async () => {
      const hass = createMockHass();
      const el = await fixture<CamerasTab>(html`
        <abode-cameras-tab .hass=${hass}></abode-cameras-tab>
      `);

      const events: CustomEvent[] = [];
      el.addEventListener('hass-more-info', (ev) => events.push(ev as CustomEvent));

      await setState(el, {
        _cameras: [createMockCamera({ entity_id: 'camera.front' })],
        _loading: false,
      } as Partial<CamerasTab>);

      el.selectedCameraEntityId = 'camera.front';
      await elementUpdated(el);

      expect(events).to.have.lengthOf(1);
      expect(events[0].detail).to.deep.equal({ entityId: 'camera.front' });

      // Triggering another update for the same selection should not re-fire.
      el.requestUpdate();
      await elementUpdated(el);
      expect(events).to.have.lengthOf(1);
    });

    it('does not fire when the selected camera is missing from the list', async () => {
      const hass = createMockHass();
      const el = await fixture<CamerasTab>(html`
        <abode-cameras-tab .hass=${hass}></abode-cameras-tab>
      `);

      const events: CustomEvent[] = [];
      el.addEventListener('hass-more-info', (ev) => events.push(ev as CustomEvent));

      await setState(el, {
        _cameras: [createMockCamera({ entity_id: 'camera.other' })],
        _loading: false,
      } as Partial<CamerasTab>);

      el.selectedCameraEntityId = 'camera.deleted';
      await elementUpdated(el);

      expect(events).to.have.lengthOf(0);
    });
  });
});
