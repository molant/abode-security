/**
 * Tests for the <abode-modal> component.
 */

import { aTimeout, expect, fixture, html } from '@open-wc/testing';

import '../abode-modal.js';
import type { AbodeModal } from '../abode-modal.js';
import { elementUpdated } from './test-helpers.js';

describe('AbodeModal', () => {
  describe('rendering', () => {
    it('renders the heading prop', async () => {
      const el = await fixture<AbodeModal>(html`
        <abode-modal heading="Delete Action"></abode-modal>
      `);
      await elementUpdated(el);

      expect(el.shadowRoot?.textContent).to.include('Delete Action');
    });

    it('projects default slot content into the body', async () => {
      const el = await fixture<AbodeModal>(html`
        <abode-modal heading="Heading">
          <p data-testid="body">Body paragraph</p>
        </abode-modal>
      `);
      await elementUpdated(el);

      // Verify projection actually happens: the shadow's default <slot> must
      // have the light-DOM <p> as an assigned element. Asserting only that
      // the light-DOM child exists wouldn't catch a missing shadow <slot>.
      const defaultSlot = el.shadowRoot?.querySelector(
        'slot:not([name])',
      ) as HTMLSlotElement | null;
      expect(defaultSlot, 'default slot must be present in shadow').to.exist;
      const assigned = defaultSlot!.assignedElements();
      expect(assigned.length).to.equal(1);
      expect(assigned[0].getAttribute('data-testid')).to.equal('body');
    });

    it('projects content into the footer slot', async () => {
      const el = await fixture<AbodeModal>(html`
        <abode-modal heading="Heading">
          <p>Body</p>
          <div slot="footer" data-testid="footer">
            <button>Cancel</button>
            <button>OK</button>
          </div>
        </abode-modal>
      `);
      await elementUpdated(el);

      const footerSlot = el.shadowRoot?.querySelector(
        'slot[name="footer"]',
      ) as HTMLSlotElement | null;
      expect(footerSlot, 'footer slot must be present in shadow').to.exist;
      const assigned = footerSlot!.assignedElements();
      expect(assigned.length).to.equal(1);
      expect(assigned[0].getAttribute('data-testid')).to.equal('footer');
      expect(assigned[0].querySelectorAll('button').length).to.equal(2);
    });

    it('hides the footer wrapper when no footer content is slotted', async () => {
      const el = await fixture<AbodeModal>(html`
        <abode-modal heading="Heading">
          <p>Body only, no footer</p>
        </abode-modal>
      `);
      await elementUpdated(el);

      const footer = el.shadowRoot?.querySelector('.modal-footer') as HTMLElement | null;
      expect(footer).to.exist;
      // The hidden attribute is the source of truth here; some browsers also
      // reflect display:none, but we only need to verify the attribute toggle.
      expect(footer!.hasAttribute('hidden')).to.equal(true);
    });

    it('shows the footer wrapper when footer content is slotted', async () => {
      const el = await fixture<AbodeModal>(html`
        <abode-modal heading="Heading">
          <p>Body</p>
          <button slot="footer">OK</button>
        </abode-modal>
      `);
      await elementUpdated(el);

      const footer = el.shadowRoot?.querySelector('.modal-footer') as HTMLElement | null;
      expect(footer).to.exist;
      expect(footer!.hasAttribute('hidden')).to.equal(false);
    });
  });

  describe('aria attributes', () => {
    it('defaults to role="dialog" and aria-modal="true"', async () => {
      const el = await fixture<AbodeModal>(html` <abode-modal heading="Heading"></abode-modal> `);
      await elementUpdated(el);

      const box = el.shadowRoot?.querySelector('.modal-box');
      expect(box?.getAttribute('role')).to.equal('dialog');
      expect(box?.getAttribute('aria-modal')).to.equal('true');
    });

    it('uses role="alertdialog" when variant="alertdialog"', async () => {
      const el = await fixture<AbodeModal>(html`
        <abode-modal heading="Heading" variant="alertdialog"></abode-modal>
      `);
      await elementUpdated(el);

      const box = el.shadowRoot?.querySelector('.modal-box');
      expect(box?.getAttribute('role')).to.equal('alertdialog');
    });

    it('points aria-labelledby at the heading element', async () => {
      const el = await fixture<AbodeModal>(html` <abode-modal heading="Heading"></abode-modal> `);
      await elementUpdated(el);

      const box = el.shadowRoot?.querySelector('.modal-box');
      const labelledBy = box?.getAttribute('aria-labelledby');
      expect(labelledBy).to.be.a('string').and.to.have.length.greaterThan(0);
      const heading = el.shadowRoot?.getElementById(labelledBy!);
      expect(heading?.textContent).to.equal('Heading');
    });
  });

  describe('dismiss', () => {
    it('dispatches dismiss when overlay clicked (target === overlay)', async () => {
      const el = await fixture<AbodeModal>(html` <abode-modal heading="Heading"></abode-modal> `);
      await elementUpdated(el);

      let dismissed = false;
      el.addEventListener('dismiss', () => {
        dismissed = true;
      });

      const overlay = el.shadowRoot?.querySelector('.modal-overlay') as HTMLElement;
      overlay?.dispatchEvent(new MouseEvent('click', { bubbles: true, composed: true }));

      expect(dismissed).to.equal(true);
    });

    it('does NOT dispatch dismiss when clicking inside the dialog body', async () => {
      const el = await fixture<AbodeModal>(html`
        <abode-modal heading="Heading">
          <p data-testid="body">Body</p>
        </abode-modal>
      `);
      await elementUpdated(el);

      let dismissed = false;
      el.addEventListener('dismiss', () => {
        dismissed = true;
      });

      // Click the dialog box itself — overlay's click handler should ignore it
      // because target !== currentTarget.
      const box = el.shadowRoot?.querySelector('.modal-box') as HTMLElement;
      box?.dispatchEvent(new MouseEvent('click', { bubbles: true, composed: true }));

      expect(dismissed).to.equal(false);
    });

    it('dispatches dismiss on Escape keydown bubbling from a descendant', async () => {
      const el = await fixture<AbodeModal>(html` <abode-modal heading="Heading"></abode-modal> `);
      await elementUpdated(el);

      let dismissed = false;
      el.addEventListener('dismiss', () => {
        dismissed = true;
      });

      // Real keydown originates on a focused descendant and bubbles up to the
      // overlay handler — dispatch from .modal-box with bubbles+composed so the
      // test mirrors the actual browser flow rather than the listener's host.
      const box = el.shadowRoot?.querySelector('.modal-box') as HTMLElement;
      box?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, composed: true }),
      );

      expect(dismissed).to.equal(true);
    });

    it('does not dispatch dismiss on non-Escape keys', async () => {
      const el = await fixture<AbodeModal>(html` <abode-modal heading="Heading"></abode-modal> `);
      await elementUpdated(el);

      let dismissed = false;
      el.addEventListener('dismiss', () => {
        dismissed = true;
      });

      const box = el.shadowRoot?.querySelector('.modal-box') as HTMLElement;
      box?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, composed: true }),
      );
      box?.dispatchEvent(new KeyboardEvent('keydown', { key: 'a', bubbles: true, composed: true }));

      expect(dismissed).to.equal(false);
    });

    it('dismissOnOverlay=false disables overlay-click dismiss', async () => {
      const el = await fixture<AbodeModal>(html`
        <abode-modal heading="Heading" .dismissOnOverlay=${false}></abode-modal>
      `);
      await elementUpdated(el);

      let dismissed = false;
      el.addEventListener('dismiss', () => {
        dismissed = true;
      });

      const overlay = el.shadowRoot?.querySelector('.modal-overlay') as HTMLElement;
      overlay?.dispatchEvent(new MouseEvent('click', { bubbles: true, composed: true }));

      expect(dismissed).to.equal(false);
    });

    it('dismissOnEscape=false disables Escape dismiss', async () => {
      const el = await fixture<AbodeModal>(html`
        <abode-modal heading="Heading" .dismissOnEscape=${false}></abode-modal>
      `);
      await elementUpdated(el);

      let dismissed = false;
      el.addEventListener('dismiss', () => {
        dismissed = true;
      });

      const box = el.shadowRoot?.querySelector('.modal-box') as HTMLElement;
      box?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, composed: true }),
      );

      expect(dismissed).to.equal(false);
    });
  });

  describe('size variant', () => {
    it('applies the size attribute to the modal box for styling', async () => {
      const small = await fixture<AbodeModal>(html`
        <abode-modal heading="S" size="sm"></abode-modal>
      `);
      await elementUpdated(small);
      expect(small.shadowRoot?.querySelector('.modal-box[data-size="sm"]')).to.exist;

      const large = await fixture<AbodeModal>(html`
        <abode-modal heading="L" size="lg"></abode-modal>
      `);
      await elementUpdated(large);
      expect(large.shadowRoot?.querySelector('.modal-box[data-size="lg"]')).to.exist;
    });
  });

  describe('focus management', () => {
    let trigger: HTMLButtonElement;

    beforeEach(() => {
      // Simulates the element that opens the dialog and should receive focus
      // back when the modal closes.
      trigger = document.createElement('button');
      trigger.id = 'opener';
      trigger.textContent = 'Open dialog';
      document.body.appendChild(trigger);
      trigger.focus();
    });

    afterEach(() => {
      trigger.remove();
    });

    it('moves focus to the first focusable descendant on open', async () => {
      expect(document.activeElement?.id).to.equal('opener');

      const el = await fixture<AbodeModal>(html`
        <abode-modal heading="Heading">
          <button id="first-body">First body</button>
          <button id="second-body">Second body</button>
          <button slot="footer" id="cancel">Cancel</button>
        </abode-modal>
      `);
      await elementUpdated(el);
      await aTimeout(0);

      expect(document.activeElement?.id).to.equal('first-body');
    });

    it('focuses the modal box (tabindex=-1) when no focusable descendant exists', async () => {
      const el = await fixture<AbodeModal>(html`
        <abode-modal heading="Heading">
          <p>Text only, no focusable controls.</p>
        </abode-modal>
      `);
      await elementUpdated(el);
      await aTimeout(0);

      const box = el.shadowRoot?.querySelector('.modal-box') as HTMLElement;
      expect(box.getAttribute('tabindex')).to.equal('-1');
      // Active element should be the host (or its shadow box) — verify focus
      // is at least within the modal subtree rather than back on the trigger.
      expect(document.activeElement === el || document.activeElement === box).to.equal(
        true,
        `expected focus inside the modal, got: ${document.activeElement?.tagName}#${(document.activeElement as HTMLElement)?.id}`,
      );
    });

    it('restores focus to the previously-focused element on disconnect', async () => {
      const el = await fixture<AbodeModal>(html`
        <abode-modal heading="Heading">
          <button id="first-body">First body</button>
        </abode-modal>
      `);
      await elementUpdated(el);
      await aTimeout(0);

      // Modal moved focus into itself; remove the modal and verify focus returns.
      el.remove();
      await aTimeout(0);

      expect(document.activeElement?.id).to.equal('opener');
    });

    it('redirects focus to the first focusable when the end sentinel gets focus (Tab past the last)', async () => {
      const el = await fixture<AbodeModal>(html`
        <abode-modal heading="Heading">
          <button id="first-body">First</button>
          <button slot="footer" id="cancel">Cancel</button>
        </abode-modal>
      `);
      await elementUpdated(el);
      await aTimeout(0);

      const endSentinel = el.shadowRoot?.querySelector('.focus-sentinel-end') as HTMLElement;
      expect(endSentinel, 'end sentinel must be present').to.exist;
      endSentinel.focus();

      // Focus should have been redirected to the first focusable.
      expect(document.activeElement?.id).to.equal('first-body');
    });

    it('redirects focus to the last focusable when the start sentinel gets focus (Shift+Tab past the first)', async () => {
      const el = await fixture<AbodeModal>(html`
        <abode-modal heading="Heading">
          <button id="first-body">First</button>
          <button slot="footer" id="cancel">Cancel</button>
        </abode-modal>
      `);
      await elementUpdated(el);
      await aTimeout(0);

      const startSentinel = el.shadowRoot?.querySelector('.focus-sentinel-start') as HTMLElement;
      expect(startSentinel, 'start sentinel must be present').to.exist;
      startSentinel.focus();

      // Focus should be redirected to the last focusable.
      expect(document.activeElement?.id).to.equal('cancel');
    });

    it('skips focusable elements with explicit tabindex="-1"', async () => {
      const el = await fixture<AbodeModal>(html`
        <abode-modal heading="Heading">
          <button id="skip" tabindex="-1">Should be skipped</button>
          <button id="real">Real focusable</button>
          <button slot="footer" id="footer-skip" tabindex="-1">Skip footer</button>
          <button slot="footer" id="footer-real">Footer real</button>
        </abode-modal>
      `);
      await elementUpdated(el);
      await aTimeout(0);

      // Initial focus must land on the first tabbable button, not the -1 one.
      expect(document.activeElement?.id).to.equal('real');

      // End sentinel must wrap to the same first tabbable, not the skipped one.
      const endSentinel = el.shadowRoot?.querySelector('.focus-sentinel-end') as HTMLElement;
      endSentinel.focus();
      expect(document.activeElement?.id).to.equal('real');

      // Start sentinel must wrap to the last tabbable (footer-real), not footer-skip.
      const startSentinel = el.shadowRoot?.querySelector('.focus-sentinel-start') as HTMLElement;
      startSentinel.focus();
      expect(document.activeElement?.id).to.equal('footer-real');
    });
  });

  describe('document-level Escape', () => {
    it('dispatches dismiss on Escape from document, even with no descendant focused', async () => {
      const el = await fixture<AbodeModal>(html` <abode-modal heading="Heading"></abode-modal> `);
      await elementUpdated(el);

      // Move focus outside the modal so the overlay listener can't catch it.
      const outside = document.createElement('button');
      document.body.appendChild(outside);
      outside.focus();

      let dismissed = false;
      el.addEventListener('dismiss', () => {
        dismissed = true;
      });

      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));

      expect(dismissed).to.equal(true);
      outside.remove();
    });

    it('does not dispatch dismiss from document Escape when dismissOnEscape=false', async () => {
      const el = await fixture<AbodeModal>(html`
        <abode-modal heading="Heading" .dismissOnEscape=${false}></abode-modal>
      `);
      await elementUpdated(el);

      let dismissed = false;
      el.addEventListener('dismiss', () => {
        dismissed = true;
      });

      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));

      expect(dismissed).to.equal(false);
    });

    it('removes the document listener on disconnect (no dismiss after removal)', async () => {
      const el = await fixture<AbodeModal>(html` <abode-modal heading="Heading"></abode-modal> `);
      await elementUpdated(el);

      let dismissed = false;
      el.addEventListener('dismiss', () => {
        dismissed = true;
      });

      el.remove();
      // Now press Escape — listener should be gone.
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));

      expect(dismissed).to.equal(false);
    });

    it('only the topmost modal dismisses on Escape when stacked', async () => {
      const a = await fixture<AbodeModal>(html` <abode-modal heading="A"></abode-modal> `);
      await elementUpdated(a);
      const b = await fixture<AbodeModal>(html` <abode-modal heading="B"></abode-modal> `);
      await elementUpdated(b);

      let aDismissed = false;
      let bDismissed = false;
      a.addEventListener('dismiss', () => (aDismissed = true));
      b.addEventListener('dismiss', () => (bDismissed = true));

      // b mounted second → it's topmost. Only b should dismiss.
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));

      expect(bDismissed).to.equal(true);
      expect(aDismissed).to.equal(false);
    });
  });
});
