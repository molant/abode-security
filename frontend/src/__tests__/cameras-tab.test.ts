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
    device_id: 'device-1',
    paired_sensor_entity_ids: [],
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

      expect(el.shadowRoot?.textContent).to.include('No Abode cameras found');
    });
  });

  describe('renders a card per camera with name, area chip, and paired-sensors text', () => {
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

    it('renders paired sensors text using hass.states friendly_name', async () => {
      const hass = createMockHass({
        states: {
          'binary_sensor.front_motion': {
            entity_id: 'binary_sensor.front_motion',
            state: 'off',
            attributes: { friendly_name: 'Front Motion' },
          },
        },
      });
      const el = await fixture<CamerasTab>(html`
        <abode-cameras-tab .hass=${hass}></abode-cameras-tab>
      `);

      await setState(el, {
        _cameras: [
          createMockCamera({
            paired_sensor_entity_ids: ['binary_sensor.front_motion'],
          }),
        ],
        _loading: false,
      } as Partial<CamerasTab>);

      expect(el.shadowRoot?.textContent).to.include('Paired with:');
      expect(el.shadowRoot?.textContent).to.include('Front Motion');
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

  describe('does not error when paired_sensor_entity_ids is empty', () => {
    it('renders without paired sensors section when list is empty', async () => {
      const hass = createMockHass();
      const el = await fixture<CamerasTab>(html`
        <abode-cameras-tab .hass=${hass}></abode-cameras-tab>
      `);

      await setState(el, {
        _cameras: [createMockCamera({ paired_sensor_entity_ids: [] })],
        _loading: false,
      } as Partial<CamerasTab>);

      expect(el.shadowRoot?.querySelector('.paired-sensors')).to.not.exist;
      expect(el.shadowRoot?.querySelector('.camera-card')).to.exist;
    });
  });

  describe('refresh interval bumps the still URL cache buster', () => {
    it('advances _refreshToken when interval fires', async () => {
      const clock = sinon.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'Date'] });
      try {
        const hass = createMockHass();
        const el = await fixture<CamerasTab>(html`
          <abode-cameras-tab .hass=${hass}></abode-cameras-tab>
        `);
        await setState(el, {
          _cameras: [createMockCamera()],
          _loading: false,
        } as Partial<CamerasTab>);

        // @ts-expect-error accessing private for testing
        const tokenBefore: number = el._refreshToken;

        clock.tick(5001);
        await elementUpdated(el);

        // @ts-expect-error accessing private for testing
        const tokenAfter: number = el._refreshToken;
        expect(tokenAfter).to.be.greaterThan(tokenBefore);
      } finally {
        clock.restore();
      }
    });
  });

  describe('pauses refresh when document.visibilityState is hidden', () => {
    it('does not bump _refreshToken when tab is hidden', async () => {
      const clock = sinon.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'Date'] });
      Object.defineProperty(document, 'visibilityState', {
        configurable: true,
        value: 'hidden',
      });
      try {
        const hass = createMockHass();
        const el = await fixture<CamerasTab>(html`
          <abode-cameras-tab .hass=${hass}></abode-cameras-tab>
        `);
        await setState(el, {
          _cameras: [createMockCamera()],
          _loading: false,
        } as Partial<CamerasTab>);

        // @ts-expect-error accessing private for testing
        const tokenBefore: number = el._refreshToken;

        clock.tick(5001);
        await elementUpdated(el);

        // @ts-expect-error accessing private for testing
        const tokenAfter: number = el._refreshToken;
        expect(tokenAfter).to.equal(tokenBefore);
      } finally {
        clock.restore();
        Object.defineProperty(document, 'visibilityState', {
          configurable: true,
          value: 'visible',
        });
      }
    });
  });
});
