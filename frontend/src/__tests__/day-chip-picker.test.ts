import { expect, fixture, html } from '@open-wc/testing';
import '../day-chip-picker.js';
import type { DayChipPicker } from '../day-chip-picker.js';
import type { Weekday } from '../types.js';
import { elementUpdated } from './test-helpers.js';

describe('DayChipPicker', () => {
  describe('rendering', () => {
    it('renders 7 chips', async () => {
      const el = await fixture<DayChipPicker>(
        html`<abode-day-chip-picker></abode-day-chip-picker>`,
      );
      const chips = el.shadowRoot!.querySelectorAll('.chip');
      expect(chips).to.have.lengthOf(7);
    });

    it('wraps chips in a role=group container with aria-label', async () => {
      const el = await fixture<DayChipPicker>(
        html`<abode-day-chip-picker></abode-day-chip-picker>`,
      );
      const group = el.shadowRoot!.querySelector('[role="group"]');
      expect(group).to.exist;
      expect(group!.getAttribute('aria-label')).to.equal('Weekdays');
    });

    it('renders chips in Mon–Sun order', async () => {
      const el = await fixture<DayChipPicker>(
        html`<abode-day-chip-picker></abode-day-chip-picker>`,
      );
      const chips = Array.from(el.shadowRoot!.querySelectorAll('.chip'));
      const labels = chips.map((c) => c.getAttribute('aria-label'));
      expect(labels).to.deep.equal([
        'Monday',
        'Tuesday',
        'Wednesday',
        'Thursday',
        'Friday',
        'Saturday',
        'Sunday',
      ]);
    });

    it('applies .active class to selected chips', async () => {
      const el = await fixture<DayChipPicker>(
        html`<abode-day-chip-picker
          .selected=${['mon', 'wed'] as Weekday[]}
        ></abode-day-chip-picker>`,
      );
      const chips = Array.from(el.shadowRoot!.querySelectorAll('.chip'));
      expect(chips[0].classList.contains('active')).to.be.true; // mon
      expect(chips[1].classList.contains('active')).to.be.false; // tue
      expect(chips[2].classList.contains('active')).to.be.true; // wed
    });

    it('sets aria-pressed=true on selected chips', async () => {
      const el = await fixture<DayChipPicker>(
        html`<abode-day-chip-picker .selected=${['fri'] as Weekday[]}></abode-day-chip-picker>`,
      );
      const chips = Array.from(el.shadowRoot!.querySelectorAll('.chip'));
      // fri is index 4
      expect(chips[4].getAttribute('aria-pressed')).to.equal('true');
      expect(chips[0].getAttribute('aria-pressed')).to.equal('false');
    });

    it('each chip aria-label is the full weekday name', async () => {
      const el = await fixture<DayChipPicker>(
        html`<abode-day-chip-picker></abode-day-chip-picker>`,
      );
      const chips = Array.from(el.shadowRoot!.querySelectorAll('.chip'));
      expect(chips[1].getAttribute('aria-label')).to.equal('Tuesday');
      expect(chips[3].getAttribute('aria-label')).to.equal('Thursday');
      expect(chips[5].getAttribute('aria-label')).to.equal('Saturday');
      expect(chips[6].getAttribute('aria-label')).to.equal('Sunday');
    });

    it('title attribute matches aria-label for tooltip disambiguation', async () => {
      const el = await fixture<DayChipPicker>(
        html`<abode-day-chip-picker></abode-day-chip-picker>`,
      );
      const chips = Array.from(el.shadowRoot!.querySelectorAll('.chip'));
      chips.forEach((chip) => {
        expect(chip.getAttribute('title')).to.equal(chip.getAttribute('aria-label'));
      });
    });
  });

  describe('interaction', () => {
    it('clicking an unselected chip dispatches change with it added', async () => {
      const el = await fixture<DayChipPicker>(
        html`<abode-day-chip-picker .selected=${['mon'] as Weekday[]}></abode-day-chip-picker>`,
      );
      let detail: { selected: Weekday[] } | null = null;
      el.addEventListener('change', (e: Event) => {
        detail = (e as CustomEvent).detail;
      });

      const chips = Array.from(el.shadowRoot!.querySelectorAll<HTMLButtonElement>('.chip'));
      chips[2].click(); // wed
      expect(detail).to.not.be.null;
      expect(detail!.selected).to.include('mon');
      expect(detail!.selected).to.include('wed');
    });

    it('change event is composed and bubbles (crosses shadow DOM boundary)', async () => {
      const el = await fixture<DayChipPicker>(
        html`<abode-day-chip-picker></abode-day-chip-picker>`,
      );
      let captured: CustomEvent | null = null;
      el.addEventListener('change', (e: Event) => {
        captured = e as CustomEvent;
      });

      const chips = Array.from(el.shadowRoot!.querySelectorAll<HTMLButtonElement>('.chip'));
      chips[0].click();
      expect(captured).to.not.be.null;
      expect(captured!.bubbles).to.be.true;
      expect(captured!.composed).to.be.true;
    });

    it('clicking a selected chip dispatches change with it removed', async () => {
      const el = await fixture<DayChipPicker>(
        html`<abode-day-chip-picker
          .selected=${['mon', 'tue'] as Weekday[]}
        ></abode-day-chip-picker>`,
      );
      let detail: { selected: Weekday[] } | null = null;
      el.addEventListener('change', (e: Event) => {
        detail = (e as CustomEvent).detail;
      });

      const chips = Array.from(el.shadowRoot!.querySelectorAll<HTMLButtonElement>('.chip'));
      chips[0].click(); // mon (was selected)
      expect(detail!.selected).to.not.include('mon');
      expect(detail!.selected).to.include('tue');
    });

    it('clicking all chips to deselect produces empty array', async () => {
      const el = await fixture<DayChipPicker>(
        html`<abode-day-chip-picker .selected=${['sat'] as Weekday[]}></abode-day-chip-picker>`,
      );
      let detail: { selected: Weekday[] } | null = null;
      el.addEventListener('change', (e: Event) => {
        detail = (e as CustomEvent).detail;
      });

      const chips = Array.from(el.shadowRoot!.querySelectorAll<HTMLButtonElement>('.chip'));
      chips[5].click(); // sat (was selected)
      expect(detail!.selected).to.deep.equal([]);
    });
  });

  describe('disabled state', () => {
    it('disabled=true blocks clicks and does not dispatch change', async () => {
      const el = await fixture<DayChipPicker>(
        html`<abode-day-chip-picker .disabled=${true}></abode-day-chip-picker>`,
      );
      let fired = false;
      el.addEventListener('change', () => {
        fired = true;
      });

      const chips = Array.from(el.shadowRoot!.querySelectorAll<HTMLButtonElement>('.chip'));
      chips[0].click();
      expect(fired).to.be.false;
    });

    it('disabled buttons have disabled attribute', async () => {
      const el = await fixture<DayChipPicker>(
        html`<abode-day-chip-picker .disabled=${true}></abode-day-chip-picker>`,
      );
      const chips = Array.from(el.shadowRoot!.querySelectorAll<HTMLButtonElement>('.chip'));
      chips.forEach((chip) => {
        expect(chip.disabled).to.be.true;
      });
    });

    it('enabled by default: chips are not disabled', async () => {
      const el = await fixture<DayChipPicker>(
        html`<abode-day-chip-picker></abode-day-chip-picker>`,
      );
      const chips = Array.from(el.shadowRoot!.querySelectorAll<HTMLButtonElement>('.chip'));
      chips.forEach((chip) => {
        expect(chip.disabled).to.be.false;
      });
    });
  });

  describe('keyboard accessibility', () => {
    it('chips are <button> elements (native Tab focus and Space/Enter support)', async () => {
      const el = await fixture<DayChipPicker>(
        html`<abode-day-chip-picker></abode-day-chip-picker>`,
      );
      const chips = Array.from(el.shadowRoot!.querySelectorAll('.chip'));
      chips.forEach((chip) => {
        expect(chip.tagName.toLowerCase()).to.equal('button');
      });
    });

    it('enabled chips are in the natural tab order (tabIndex >= 0)', async () => {
      const el = await fixture<DayChipPicker>(
        html`<abode-day-chip-picker></abode-day-chip-picker>`,
      );
      const chips = Array.from(el.shadowRoot!.querySelectorAll<HTMLButtonElement>('.chip'));
      chips.forEach((chip) => {
        // Native <button> elements have tabIndex = 0 by default and are
        // reachable via Tab without any additional markup.
        expect(chip.tabIndex).to.be.gte(0);
      });
    });

    it('Enter key on a focused chip dispatches change (native button activation)', async () => {
      const el = await fixture<DayChipPicker>(
        html`<abode-day-chip-picker></abode-day-chip-picker>`,
      );
      let detail: { selected: Weekday[] } | null = null;
      el.addEventListener('change', (e: Event) => {
        detail = (e as CustomEvent).detail;
      });

      const chips = Array.from(el.shadowRoot!.querySelectorAll<HTMLButtonElement>('.chip'));
      chips[0].focus();
      // In Chromium, Enter on a focused button fires a click synchronously.
      // We dispatch a trusted-looking Enter keydown then click to mirror the
      // browser's activation sequence, since synthetic KeyboardEvents don't
      // trigger the browser's built-in button activation.
      chips[0].dispatchEvent(
        new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, composed: true }),
      );
      chips[0].click(); // click is what the browser fires as a result of Enter
      expect(detail).to.not.be.null;
      expect(detail!.selected).to.include('mon');
    });

    it('Space key on a focused chip dispatches change (native button activation)', async () => {
      const el = await fixture<DayChipPicker>(
        html`<abode-day-chip-picker></abode-day-chip-picker>`,
      );
      let detail: { selected: Weekday[] } | null = null;
      el.addEventListener('change', (e: Event) => {
        detail = (e as CustomEvent).detail;
      });

      const chips = Array.from(el.shadowRoot!.querySelectorAll<HTMLButtonElement>('.chip'));
      chips[1].focus(); // tue
      chips[1].dispatchEvent(
        new KeyboardEvent('keydown', { key: ' ', bubbles: true, composed: true }),
      );
      chips[1].dispatchEvent(
        new KeyboardEvent('keyup', { key: ' ', bubbles: true, composed: true }),
      );
      chips[1].click(); // browser fires click on Space keyup
      expect(detail).to.not.be.null;
      expect(detail!.selected).to.include('tue');
    });

    it('disabled chips have the disabled attribute (browsers exclude them from tab order)', async () => {
      const el = await fixture<DayChipPicker>(
        html`<abode-day-chip-picker .disabled=${true}></abode-day-chip-picker>`,
      );
      const chips = Array.from(el.shadowRoot!.querySelectorAll<HTMLButtonElement>('.chip'));
      // Browsers natively remove disabled form elements from sequential tab
      // navigation. We assert the `disabled` property is set (the mechanism),
      // since Chromium keeps tabIndex = 0 even on disabled buttons.
      chips.forEach((chip) => {
        expect(chip.disabled).to.be.true;
      });
    });
  });

  describe('reactivity', () => {
    it('updates chip active state when selected prop changes', async () => {
      const el = await fixture<DayChipPicker>(
        html`<abode-day-chip-picker .selected=${[] as Weekday[]}></abode-day-chip-picker>`,
      );
      let chips = Array.from(el.shadowRoot!.querySelectorAll('.chip'));
      expect(chips[0].classList.contains('active')).to.be.false;

      el.selected = ['mon'];
      await elementUpdated(el);

      chips = Array.from(el.shadowRoot!.querySelectorAll('.chip'));
      expect(chips[0].classList.contains('active')).to.be.true;
    });
  });
});
