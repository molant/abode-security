/**
 * <abode-modal> — shared modal dialog used by the actions tab and editor.
 *
 * Provides the overlay + box scaffolding, ARIA attributes, dismiss behavior,
 * and a11y focus management (move on open, trap via sentinels, restore on
 * close). Consumers fill the body via the default slot and the footer (button
 * row) via the `footer` slot.
 *
 * The internal `<h2>` gets a generated id and is wired up via `aria-labelledby`
 * on the dialog box, so consumers only need to pass the `heading` text.
 *
 * Focus model:
 * - On `firstUpdated`, focus moves to the first focusable descendant (slotted
 *   body or footer). If none exists, the modal box itself (`tabindex="-1"`)
 *   receives focus so keyboard users still land inside the dialog.
 * - On the first `connectedCallback`, the previously-focused element is
 *   captured; on `disconnectedCallback` focus is restored to it, but only if
 *   focus was either lost (active = `<body>`) or still inside the modal —
 *   so a consumer that moves focus elsewhere on `dismiss` is not stomped.
 * - Tab focus is trapped via a pair of `focus-sentinel` spans wrapping the
 *   modal box: tabbing past the end redirects to the first focusable, and
 *   shift+tabbing past the start redirects to the last.
 *
 * Escape model: a document-level `keydown` listener fires `dismiss` regardless
 * of where focus currently is, so Escape works immediately after open even if
 * no descendant has been tab-focused yet (closes #28). When multiple modals
 * are mounted, only the topmost (most recently connected) handles Escape, via
 * a module-level mount stack.
 *
 * @fires dismiss - Dispatched on overlay click (when dismissOnOverlay) or
 *                  Escape keydown anywhere in the document (when dismissOnEscape).
 *
 * @prop {string} heading                - Title text rendered above the body.
 * @prop {'dialog' | 'alertdialog'} variant - ARIA role on the dialog box; default 'dialog'.
 * @prop {'sm' | 'lg'} size              - 'sm' (max-width 400px) or 'lg' (max-width 600px, scrollable).
 * @prop {boolean} dismissOnOverlay      - Default true.
 * @prop {boolean} dismissOnEscape       - Default true.
 */

import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

let modalIdSeq = 0;

// Mount stack — only the topmost modal handles document-level Escape so
// stacked modals don't all dismiss on a single keypress.
const modalStack: AbodeModal[] = [];

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'textarea:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

@customElement('abode-modal')
export class AbodeModal extends LitElement {
  @property({ type: String }) heading = '';
  @property({ type: String }) variant: 'dialog' | 'alertdialog' = 'dialog';
  @property({ type: String }) size: 'sm' | 'lg' = 'sm';
  @property({ type: Boolean, attribute: 'dismiss-on-overlay' }) dismissOnOverlay = true;
  @property({ type: Boolean, attribute: 'dismiss-on-escape' }) dismissOnEscape = true;

  @state() private _hasFooterContent = false;

  private readonly _headingId = `abode-modal-heading-${++modalIdSeq}`;
  private _previouslyFocused: HTMLElement | null = null;

  static styles = css`
    :host {
      display: block;
    }

    .modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      padding: 16px;
    }

    .modal-box {
      background: var(--card-background-color, #fff);
      border-radius: 8px;
      padding: 24px;
      width: 100%;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }

    .modal-box[data-size='sm'] {
      max-width: 400px;
    }

    .modal-box[data-size='lg'] {
      max-width: 600px;
      max-height: 90vh;
      overflow-y: auto;
      border-radius: 12px;
    }

    h2 {
      margin: 0 0 16px 0;
      font-weight: 500;
      color: var(--primary-text-color);
    }

    .modal-box[data-size='sm'] h2 {
      font-size: 18px;
    }

    .modal-box[data-size='lg'] h2 {
      font-size: 20px;
      margin-bottom: 24px;
    }

    .modal-footer {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      margin-top: 24px;
    }

    .modal-box[data-size='lg'] .modal-footer {
      padding-top: 16px;
      border-top: 1px solid var(--divider-color, #e0e0e0);
    }

    ::slotted(p) {
      margin: 0 0 24px 0;
      color: var(--secondary-text-color);
      line-height: 1.5;
    }

    /* Focus sentinels are visually hidden but keep their place in the focus
     * order. When tab focus reaches them, the @focus handlers redirect into
     * the first/last real focusable so focus stays trapped inside the modal. */
    .focus-sentinel {
      position: absolute;
      width: 1px;
      height: 1px;
      overflow: hidden;
      opacity: 0;
      pointer-events: none;
    }

    .modal-box:focus {
      outline: none;
    }
  `;

  private _onOverlayClick = (e: Event) => {
    if (!this.dismissOnOverlay) return;
    if (e.target === e.currentTarget) {
      this._dismiss();
    }
  };

  private _onDocKeydown = (e: KeyboardEvent) => {
    if (!this.dismissOnEscape) return;
    // Only the topmost mounted modal handles Escape — see modalStack.
    if (modalStack[modalStack.length - 1] !== this) return;
    if (e.key === 'Escape') {
      this._dismiss();
    }
  };

  private _onFooterSlotChange = (e: Event) => {
    const slot = e.target as HTMLSlotElement;
    this._hasFooterContent = slot.assignedElements().length > 0;
  };

  private _onSentinelStartFocus = () => {
    // User shift-tabbed off the first focusable: redirect to the last.
    this._redirectFocus('last');
  };

  private _onSentinelEndFocus = () => {
    // User tabbed off the last focusable: redirect to the first.
    this._redirectFocus('first');
  };

  private _redirectFocus(target: 'first' | 'last') {
    const focusable = this._getFocusable();
    if (focusable.length === 0) {
      this._focusBox();
      return;
    }
    const el = target === 'first' ? focusable[0] : focusable[focusable.length - 1];
    el.focus();
  }

  private _getFocusable(): HTMLElement[] {
    // Real focusables live in slotted content (consumer's tree), not the
    // modal's shadow root, so iterate the slots' assignedElements.
    const slots = this.shadowRoot?.querySelectorAll<HTMLSlotElement>(
      'slot:not([name]), slot[name="footer"]',
    );
    if (!slots) return [];
    const out: HTMLElement[] = [];
    for (const slot of slots) {
      for (const el of slot.assignedElements({ flatten: true })) {
        if (!(el instanceof HTMLElement)) continue;
        if (el.matches(FOCUSABLE_SELECTOR)) out.push(el);
        out.push(...el.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));
      }
    }
    // Native form elements match the CSS selector regardless of tabindex, so
    // a consumer that sets `tabindex="-1"` on a button to take it out of tab
    // order would still land here. Filter on the resolved `tabIndex` so the
    // sentinel never redirects to an element the user can't actually reach.
    return out.filter((el) => el.tabIndex >= 0);
  }

  private _focusBox() {
    const box = this.shadowRoot?.querySelector('.modal-box') as HTMLElement | null;
    box?.focus();
  }

  private _dismiss() {
    this.dispatchEvent(new CustomEvent('dismiss', { bubbles: true, composed: true }));
  }

  connectedCallback() {
    super.connectedCallback();
    // Capture only on the first connect — re-attaches (Lit moves, HMR) shouldn't
    // overwrite the legitimate trigger element with whatever happened to be
    // focused later (which could be the modal box itself).
    if (this._previouslyFocused === null) {
      this._previouslyFocused = document.activeElement as HTMLElement | null;
    }
    modalStack.push(this);
    document.addEventListener('keydown', this._onDocKeydown);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    document.removeEventListener('keydown', this._onDocKeydown);
    const idx = modalStack.indexOf(this);
    if (idx !== -1) modalStack.splice(idx, 1);

    // Restore focus only if it was lost (defaulted to <body>) or still inside
    // the disconnecting modal subtree — don't fight a consumer that moved
    // focus elsewhere in their dismiss handler.
    const active = document.activeElement as HTMLElement | null;
    const focusLost =
      !active || active === document.body || this.contains(active);
    if (focusLost) {
      this._previouslyFocused?.focus?.();
    }
    this._previouslyFocused = null;
  }

  protected firstUpdated() {
    const focusable = this._getFocusable();
    if (focusable.length > 0) {
      focusable[0].focus();
    } else {
      this._focusBox();
    }
  }

  render() {
    return html`
      <div class="modal-overlay" @click=${this._onOverlayClick}>
        <span
          class="focus-sentinel focus-sentinel-start"
          tabindex="0"
          @focus=${this._onSentinelStartFocus}
        ></span>
        <div
          class="modal-box"
          role=${this.variant}
          aria-modal="true"
          aria-labelledby=${this._headingId}
          data-size=${this.size}
          tabindex="-1"
        >
          <h2 id=${this._headingId}>${this.heading}</h2>
          <slot></slot>
          <div class="modal-footer" ?hidden=${!this._hasFooterContent}>
            <slot name="footer" @slotchange=${this._onFooterSlotChange}></slot>
          </div>
        </div>
        <span
          class="focus-sentinel focus-sentinel-end"
          tabindex="0"
          @focus=${this._onSentinelEndFocus}
        ></span>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'abode-modal': AbodeModal;
  }
}
