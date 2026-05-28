import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { WEEKDAYS, type Weekday } from './types';

/**
 * A reusable weekday multi-select chip picker.
 *
 * Renders seven chips (Mon–Sun). Clicking a chip toggles it and dispatches
 * a `change` CustomEvent with `{ detail: { selected: Weekday[] } }`.
 *
 * Keyboard: each chip is a `<button>` so Tab/Shift-Tab cycles focus; Space
 * and Enter toggle the focused chip (native button behaviour).
 *
 * Accessibility: `role="group"` + `aria-label` on the container; `aria-pressed`
 * on each chip; visible single-letter labels with `aria-label` and `title`
 * carrying the full weekday name to disambiguate T (Tue/Thu) and S (Sat/Sun).
 */
@customElement('abode-day-chip-picker')
export class DayChipPicker extends LitElement {
  @property({ type: Array }) selected: Weekday[] = [];
  @property({ type: Boolean }) disabled = false;

  static styles = css`
    :host {
      display: block;
    }

    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
    }

    .chip {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 44px;
      height: 44px;
      padding: 0;
      border-radius: 50%;
      border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--secondary-background-color, #f5f5f5);
      color: var(--secondary-text-color);
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      transition:
        background 0.15s,
        color 0.15s,
        border-color 0.15s;
    }

    .chip.active {
      background: var(--primary-color, #03a9f4);
      color: white;
      border-color: var(--primary-color, #03a9f4);
    }

    .chip:focus-visible {
      outline: 2px solid var(--primary-color, #03a9f4);
      outline-offset: 2px;
    }

    .chip:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .chip:not(:disabled):hover:not(.active) {
      background: var(--primary-color, #03a9f4);
      color: white;
      border-color: var(--primary-color, #03a9f4);
      opacity: 0.7;
    }
  `;

  private _toggle(day: Weekday) {
    if (this.disabled) return;
    const next = this.selected.includes(day)
      ? this.selected.filter((d) => d !== day)
      : [...this.selected, day];
    this.dispatchEvent(
      new CustomEvent('change', { detail: { selected: next }, bubbles: true, composed: true }),
    );
  }

  render() {
    return html`
      <div class="chips" role="group" aria-label="Weekdays">
        ${WEEKDAYS.map(
          (day) => html`
            <button
              type="button"
              class="chip ${this.selected.includes(day) ? 'active' : ''}"
              ?disabled=${this.disabled}
              aria-pressed=${this.selected.includes(day) ? 'true' : 'false'}
              aria-label=${this._fullName(day)}
              title=${this._fullName(day)}
              @click=${() => this._toggle(day)}
            >
              ${this._label(day)}
            </button>
          `,
        )}
      </div>
    `;
  }

  private _label(day: Weekday): string {
    // Single-letter visible label. NOTE: Tue/Thu and Sat/Sun share a letter
    // visually — disambiguation MUST come from aria-label + title (see render).
    // Do not "fix" by switching to 2-letter labels; the design calls for 1.
    const map: Record<Weekday, string> = {
      mon: 'M',
      tue: 'T',
      wed: 'W',
      thu: 'T',
      fri: 'F',
      sat: 'S',
      sun: 'S',
    };
    return map[day];
  }

  private _fullName(day: Weekday): string {
    const map: Record<Weekday, string> = {
      mon: 'Monday',
      tue: 'Tuesday',
      wed: 'Wednesday',
      thu: 'Thursday',
      fri: 'Friday',
      sat: 'Saturday',
      sun: 'Sunday',
    };
    return map[day];
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'abode-day-chip-picker': DayChipPicker;
  }
}
