/**
 * Tests for the <abode-modal> component.
 */

import { expect, fixture, html } from '@open-wc/testing';

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
      const el = await fixture<AbodeModal>(html`
        <abode-modal heading="Heading"></abode-modal>
      `);
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
      const el = await fixture<AbodeModal>(html`
        <abode-modal heading="Heading"></abode-modal>
      `);
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
      const el = await fixture<AbodeModal>(html`
        <abode-modal heading="Heading"></abode-modal>
      `);
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
      const el = await fixture<AbodeModal>(html`
        <abode-modal heading="Heading"></abode-modal>
      `);
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
      const el = await fixture<AbodeModal>(html`
        <abode-modal heading="Heading"></abode-modal>
      `);
      await elementUpdated(el);

      let dismissed = false;
      el.addEventListener('dismiss', () => {
        dismissed = true;
      });

      const box = el.shadowRoot?.querySelector('.modal-box') as HTMLElement;
      box?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, composed: true }),
      );
      box?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'a', bubbles: true, composed: true }),
      );

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
});
