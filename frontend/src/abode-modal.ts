/**
 * <abode-modal> — shared modal dialog used by the actions tab and editor.
 *
 * Provides the overlay + box scaffolding, ARIA attributes, and overlay/Escape
 * dismiss behavior. Consumers fill the body via the default slot and the
 * footer (button row) via the `footer` slot.
 *
 * The internal `<h2>` gets a generated id and is wired up via `aria-labelledby`
 * on the dialog box, so consumers only need to pass the `heading` text.
 *
 * Known limitation: the Escape `keydown` listener lives on the overlay div,
 * which never receives focus on its own. Pressing Escape only works once
 * something inside the dialog has been tab-focused. Tracked as #28; the focus
 * move/trap/restore + document-level Escape listener will be added in the a11y
 * follow-up (#9 + #28 group). The `dismiss` event contract here stays the
 * same.
 *
 * @fires dismiss - Dispatched on overlay click (when dismissOnOverlay) or
 *                  Escape keydown (when dismissOnEscape) — see the focus
 *                  caveat above.
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

@customElement('abode-modal')
export class AbodeModal extends LitElement {
  @property({ type: String }) heading = '';
  @property({ type: String }) variant: 'dialog' | 'alertdialog' = 'dialog';
  @property({ type: String }) size: 'sm' | 'lg' = 'sm';
  @property({ type: Boolean, attribute: 'dismiss-on-overlay' }) dismissOnOverlay = true;
  @property({ type: Boolean, attribute: 'dismiss-on-escape' }) dismissOnEscape = true;

  @state() private _hasFooterContent = false;

  private readonly _headingId = `abode-modal-heading-${++modalIdSeq}`;

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
  `;

  private _onOverlayClick = (e: Event) => {
    if (!this.dismissOnOverlay) return;
    if (e.target === e.currentTarget) {
      this._dismiss();
    }
  };

  private _onKeydown = (e: KeyboardEvent) => {
    if (!this.dismissOnEscape) return;
    // Note: this fires only when a focused descendant of the overlay receives
    // the keydown — the overlay <div> itself isn't focusable. Tracked in #28.
    if (e.key === 'Escape') {
      this._dismiss();
    }
  };

  private _onFooterSlotChange = (e: Event) => {
    const slot = e.target as HTMLSlotElement;
    this._hasFooterContent = slot.assignedElements().length > 0;
  };

  private _dismiss() {
    this.dispatchEvent(new CustomEvent('dismiss', { bubbles: true, composed: true }));
  }

  render() {
    return html`
      <div
        class="modal-overlay"
        @click=${this._onOverlayClick}
        @keydown=${this._onKeydown}
      >
        <div
          class="modal-box"
          role=${this.variant}
          aria-modal="true"
          aria-labelledby=${this._headingId}
          data-size=${this.size}
        >
          <h2 id=${this._headingId}>${this.heading}</h2>
          <slot></slot>
          <div class="modal-footer" ?hidden=${!this._hasFooterContent}>
            <slot name="footer" @slotchange=${this._onFooterSlotChange}></slot>
          </div>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'abode-modal': AbodeModal;
  }
}
