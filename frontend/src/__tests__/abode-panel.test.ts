/**
 * Tests for the AbodeConfigurationPanel top-level panel.
 *
 * Focus: tab bar wiring — order, default selection, click switching.
 * Child tabs (modes-tab, actions-tab) have their own test files; here we
 * only assert the panel mounts the right one for the active tab.
 */

import { expect, fixture, html } from '@open-wc/testing';

import '../abode-panel.js';
import type { AbodeConfigurationPanel } from '../abode-panel.js';
import { createMockHass, elementUpdated } from './test-helpers.js';

describe('AbodeConfigurationPanel', () => {
  describe('tab bar (#120)', () => {
    it('renders the Modes tab first, then Actions, then Cameras', async () => {
      const hass = createMockHass();
      const el = await fixture<AbodeConfigurationPanel>(html`
        <abode-configuration-panel .hass=${hass}></abode-configuration-panel>
      `);
      await elementUpdated(el);

      const buttons = Array.from(
        el.shadowRoot?.querySelectorAll<HTMLButtonElement>('.tab-bar button[role="tab"]') ?? [],
      );
      const labels = buttons.map((b) => b.textContent?.trim() ?? '');
      expect(labels).to.deep.equal(['Modes', 'Actions', 'Cameras']);
    });

    it('defaults to the Modes tab being active', async () => {
      const hass = createMockHass();
      const el = await fixture<AbodeConfigurationPanel>(html`
        <abode-configuration-panel .hass=${hass}></abode-configuration-panel>
      `);
      await elementUpdated(el);

      const modesBtn = el.shadowRoot?.querySelector<HTMLButtonElement>('#modes-tab');
      const actionsBtn = el.shadowRoot?.querySelector<HTMLButtonElement>('#actions-tab');
      expect(modesBtn?.getAttribute('aria-selected')).to.equal('true');
      expect(actionsBtn?.getAttribute('aria-selected')).to.equal('false');
      expect(el.shadowRoot?.querySelector('abode-modes-tab')).to.exist;
      expect(el.shadowRoot?.querySelector('abode-actions-tab')).to.not.exist;
    });

    it('switches to the Actions tab on click', async () => {
      const hass = createMockHass();
      const el = await fixture<AbodeConfigurationPanel>(html`
        <abode-configuration-panel .hass=${hass}></abode-configuration-panel>
      `);
      await elementUpdated(el);

      const actionsBtn = el.shadowRoot?.querySelector<HTMLButtonElement>('#actions-tab');
      actionsBtn?.click();
      await elementUpdated(el);

      expect(actionsBtn?.getAttribute('aria-selected')).to.equal('true');
      expect(el.shadowRoot?.querySelector('abode-actions-tab')).to.exist;
      expect(el.shadowRoot?.querySelector('abode-modes-tab')).to.not.exist;
    });

    it('switches to the Cameras tab on click', async () => {
      const hass = createMockHass();
      const el = await fixture<AbodeConfigurationPanel>(html`
        <abode-configuration-panel .hass=${hass}></abode-configuration-panel>
      `);
      await elementUpdated(el);

      const camerasBtn = el.shadowRoot?.querySelector<HTMLButtonElement>('#cameras-tab');
      camerasBtn?.click();
      await elementUpdated(el);

      expect(camerasBtn?.getAttribute('aria-selected')).to.equal('true');
      expect(el.shadowRoot?.querySelector('abode-cameras-tab')).to.exist;
      expect(el.shadowRoot?.querySelector('abode-modes-tab')).to.not.exist;
    });
  });
});
