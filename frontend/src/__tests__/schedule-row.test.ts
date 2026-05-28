import { expect, fixture, html } from '@open-wc/testing';
import '../schedule-row.js';
import type { ScheduleRow } from '../schedule-row.js';
import type { AbodeSchedule, ScheduleCreateInput } from '../types.js';
import { elementUpdated, setState } from './test-helpers.js';

function createMockSchedule(overrides: Partial<AbodeSchedule> = {}): AbodeSchedule {
  return {
    id: 'sched-1',
    name: '',
    weekdays: ['mon', 'tue', 'wed'],
    arm_time: '22:00',
    disarm_time: '06:00',
    enabled: true,
    created_at: '2026-01-01T00:00:00Z',
    last_armed_at: null,
    last_disarmed_at: null,
    last_skip_reason: null,
    last_error: null,
    ...overrides,
  };
}

describe('ScheduleRow', () => {
  describe('view mode', () => {
    it('renders arm and disarm times', async () => {
      const el = await fixture<ScheduleRow>(
        html`<abode-schedule-row
          .schedule=${createMockSchedule()}
          .canEdit=${true}
        ></abode-schedule-row>`,
      );
      await elementUpdated(el);
      expect(el.shadowRoot!.textContent).to.include('22:00');
      expect(el.shadowRoot!.textContent).to.include('06:00');
    });

    it('renders schedule name when set', async () => {
      const el = await fixture<ScheduleRow>(
        html`<abode-schedule-row
          .schedule=${createMockSchedule({ name: 'Weeknights' })}
          .canEdit=${false}
        ></abode-schedule-row>`,
      );
      await elementUpdated(el);
      expect(el.shadowRoot!.textContent).to.include('Weeknights');
    });

    it('shows edit and delete icons when canEdit=true', async () => {
      const el = await fixture<ScheduleRow>(
        html`<abode-schedule-row
          .schedule=${createMockSchedule()}
          .canEdit=${true}
        ></abode-schedule-row>`,
      );
      await elementUpdated(el);
      const editBtn = el.shadowRoot!.querySelector('[aria-label="Edit schedule"]');
      const deleteBtn = el.shadowRoot!.querySelector('[aria-label="Delete schedule"]');
      expect(editBtn).to.exist;
      expect(deleteBtn).to.exist;
    });

    it('hides edit and delete icons when canEdit=false', async () => {
      const el = await fixture<ScheduleRow>(
        html`<abode-schedule-row
          .schedule=${createMockSchedule()}
          .canEdit=${false}
        ></abode-schedule-row>`,
      );
      await elementUpdated(el);
      const editBtn = el.shadowRoot!.querySelector('[aria-label="Edit schedule"]');
      const deleteBtn = el.shadowRoot!.querySelector('[aria-label="Delete schedule"]');
      expect(editBtn).to.not.exist;
      expect(deleteBtn).to.not.exist;
    });

    it('shows error badge when last_error is set', async () => {
      const el = await fixture<ScheduleRow>(
        html`<abode-schedule-row
          .schedule=${createMockSchedule({ last_error: 'panel_unavailable' })}
          .canEdit=${false}
        ></abode-schedule-row>`,
      );
      await elementUpdated(el);
      const badge = el.shadowRoot!.querySelector('.error-badge');
      expect(badge).to.exist;
    });

    it('does not show error badge when last_error is null', async () => {
      const el = await fixture<ScheduleRow>(
        html`<abode-schedule-row
          .schedule=${createMockSchedule({ last_error: null })}
          .canEdit=${false}
        ></abode-schedule-row>`,
      );
      await elementUpdated(el);
      const badge = el.shadowRoot!.querySelector('.error-badge');
      expect(badge).to.not.exist;
    });

    it('applies .disabled class when schedule.enabled=false', async () => {
      const el = await fixture<ScheduleRow>(
        html`<abode-schedule-row
          .schedule=${createMockSchedule({ enabled: false })}
          .canEdit=${false}
        ></abode-schedule-row>`,
      );
      await elementUpdated(el);
      const viewRow = el.shadowRoot!.querySelector('.view-row');
      expect(viewRow!.classList.contains('disabled')).to.be.true;
    });

    it('enable toggle in view mode dispatches save with enabled toggled', async () => {
      const el = await fixture<ScheduleRow>(
        html`<abode-schedule-row
          .schedule=${createMockSchedule({ enabled: true })}
          .canEdit=${true}
        ></abode-schedule-row>`,
      );
      await elementUpdated(el);

      let savedDetail: { id: string; data: { enabled: boolean } } | null = null;
      el.addEventListener('save', (e: Event) => {
        savedDetail = (e as CustomEvent).detail;
      });

      const toggle = el.shadowRoot!.querySelector<HTMLInputElement>('input[type="checkbox"]');
      expect(toggle).to.exist;
      // Simulate unchecking the toggle
      toggle!.checked = false;
      toggle!.dispatchEvent(new Event('change', { bubbles: true }));
      await elementUpdated(el);

      expect(savedDetail).to.not.be.null;
      expect(savedDetail!.data.enabled).to.be.false;
      expect(savedDetail!.id).to.equal('sched-1');
    });

    it('enable toggle is disabled for non-admin (canEdit=false)', async () => {
      const el = await fixture<ScheduleRow>(
        html`<abode-schedule-row
          .schedule=${createMockSchedule()}
          .canEdit=${false}
        ></abode-schedule-row>`,
      );
      await elementUpdated(el);
      const toggle = el.shadowRoot!.querySelector<HTMLInputElement>('input[type="checkbox"]');
      expect(toggle!.disabled).to.be.true;
    });
  });

  describe('entering edit mode', () => {
    it('clicking edit button enters edit mode with draft populated from schedule', async () => {
      const el = await fixture<ScheduleRow>(
        html`<abode-schedule-row
          .schedule=${createMockSchedule({ arm_time: '21:00', disarm_time: '07:00' })}
          .canEdit=${true}
        ></abode-schedule-row>`,
      );
      await elementUpdated(el);
      const editBtn = el.shadowRoot!.querySelector<HTMLButtonElement>(
        '[aria-label="Edit schedule"]',
      );
      editBtn!.click();
      await elementUpdated(el);

      const armInput = el.shadowRoot!.querySelector<HTMLInputElement>('[aria-label="Arm time"]');
      const disarmInput = el.shadowRoot!.querySelector<HTMLInputElement>(
        '[aria-label="Disarm time"]',
      );
      expect(armInput).to.exist;
      expect(disarmInput).to.exist;
      // Verify draft was populated from the schedule's current values
      expect(armInput!.value).to.equal('21:00');
      expect(disarmInput!.value).to.equal('07:00');
    });
  });

  describe('validation', () => {
    it('shows error when saving with no weekdays selected', async () => {
      const el = await fixture<ScheduleRow>(
        html`<abode-schedule-row
          .schedule=${createMockSchedule({ weekdays: [] })}
          .canEdit=${true}
        ></abode-schedule-row>`,
      );
      await setState(el, {
        _editing: true,
        _draft: { name: '', weekdays: [], arm_time: '22:00', disarm_time: '06:00', enabled: true },
      } as Partial<ScheduleRow>);

      const saveBtn = el.shadowRoot!.querySelector<HTMLButtonElement>('.btn.primary');
      saveBtn!.click();
      await elementUpdated(el);

      const errorEl = el.shadowRoot!.querySelector('[role="alert"]');
      expect(errorEl).to.exist;
      expect(errorEl!.textContent).to.include('weekday');

      // No save event should have been dispatched
      let saved = false;
      el.addEventListener('save', () => {
        saved = true;
      });
      expect(saved).to.be.false;
    });

    it('shows error when arm time equals disarm time', async () => {
      const el = await fixture<ScheduleRow>(
        html`<abode-schedule-row
          .schedule=${createMockSchedule()}
          .canEdit=${true}
        ></abode-schedule-row>`,
      );
      await setState(el, {
        _editing: true,
        _draft: {
          name: '',
          weekdays: ['mon'],
          arm_time: '22:00',
          disarm_time: '22:00',
          enabled: true,
        },
      } as Partial<ScheduleRow>);

      const saveBtn = el.shadowRoot!.querySelector<HTMLButtonElement>('.btn.primary');
      saveBtn!.click();
      await elementUpdated(el);

      const errorEl = el.shadowRoot!.querySelector('[role="alert"]');
      expect(errorEl).to.exist;
      expect(errorEl!.textContent).to.include('differ');
    });

    it('dispatches save event with id and data for valid edit', async () => {
      const el = await fixture<ScheduleRow>(
        html`<abode-schedule-row
          .schedule=${createMockSchedule({ id: 'sched-abc' })}
          .canEdit=${true}
        ></abode-schedule-row>`,
      );
      await setState(el, {
        _editing: true,
        _draft: {
          name: 'Weeknights',
          weekdays: ['mon', 'tue'],
          arm_time: '22:00',
          disarm_time: '06:00',
          enabled: true,
        } as ScheduleCreateInput,
      } as Partial<ScheduleRow>);

      let savedDetail: { id: string; data: ScheduleCreateInput } | null = null;
      el.addEventListener('save', (e: Event) => {
        savedDetail = (e as CustomEvent).detail;
      });

      const saveBtn = el.shadowRoot!.querySelector<HTMLButtonElement>('.btn.primary');
      saveBtn!.click();
      await elementUpdated(el);

      expect(savedDetail).to.not.be.null;
      expect(savedDetail!.id).to.equal('sched-abc');
      expect(savedDetail!.data.name).to.equal('Weeknights');
      expect(savedDetail!.data.weekdays).to.deep.equal(['mon', 'tue']);
    });

    it('_saving=true disables the Save button', async () => {
      const el = await fixture<ScheduleRow>(
        html`<abode-schedule-row
          .schedule=${createMockSchedule()}
          .canEdit=${true}
        ></abode-schedule-row>`,
      );
      await setState(el, {
        _editing: true,
        _saving: true,
        _draft: {
          name: '',
          weekdays: ['mon'],
          arm_time: '22:00',
          disarm_time: '06:00',
          enabled: true,
        },
      } as Partial<ScheduleRow>);

      const saveBtn = el.shadowRoot!.querySelector<HTMLButtonElement>('.btn.primary');
      expect(saveBtn!.disabled).to.be.true;
    });
  });

  describe('cancel', () => {
    it('cancel button reverts to view mode and clears draft', async () => {
      const el = await fixture<ScheduleRow>(
        html`<abode-schedule-row
          .schedule=${createMockSchedule()}
          .canEdit=${true}
        ></abode-schedule-row>`,
      );
      await setState(el, {
        _editing: true,
        _draft: {
          name: '',
          weekdays: ['mon'],
          arm_time: '22:00',
          disarm_time: '06:00',
          enabled: true,
        },
      } as Partial<ScheduleRow>);

      const cancelBtn = el.shadowRoot!.querySelector<HTMLButtonElement>('.btn.secondary');
      cancelBtn!.click();
      await elementUpdated(el);

      // Should be back in view mode (no edit form)
      expect(el.shadowRoot!.querySelector('.edit-form')).to.not.exist;
      expect(el.shadowRoot!.querySelector('.view-row')).to.exist;
    });

    it('cancel resets _saving so Save button is not stuck disabled', async () => {
      const el = await fixture<ScheduleRow>(
        html`<abode-schedule-row
          .schedule=${createMockSchedule()}
          .canEdit=${true}
        ></abode-schedule-row>`,
      );
      await setState(el, {
        _editing: true,
        _saving: true,
        _draft: {
          name: '',
          weekdays: ['mon'],
          arm_time: '22:00',
          disarm_time: '06:00',
          enabled: true,
        },
      } as Partial<ScheduleRow>);

      // Verify Save button is currently disabled due to _saving
      const saveBtn = () => el.shadowRoot!.querySelector<HTMLButtonElement>('.btn.primary');
      expect(saveBtn()!.disabled).to.be.true;

      const cancelBtn = el.shadowRoot!.querySelector<HTMLButtonElement>('.btn.secondary');
      cancelBtn!.click();
      await elementUpdated(el);

      // After cancel, clicking edit again and entering edit mode should show enabled Save
      const editBtn = el.shadowRoot!.querySelector<HTMLButtonElement>(
        '[aria-label="Edit schedule"]',
      );
      editBtn!.click();
      await elementUpdated(el);
      expect(saveBtn()!.disabled).to.be.false;
    });
  });

  describe('new-row mode (id === "")', () => {
    it('starts in edit mode immediately', async () => {
      const el = await fixture<ScheduleRow>(
        html`<abode-schedule-row
          .schedule=${createMockSchedule({
            id: '',
            weekdays: [],
            arm_time: '22:00',
            disarm_time: '06:00',
          })}
          .canEdit=${true}
        ></abode-schedule-row>`,
      );
      await elementUpdated(el);
      expect(el.shadowRoot!.querySelector('.edit-form')).to.exist;
    });

    it('Cancel in new-row mode emits cancel-new instead of toggling edit', async () => {
      const el = await fixture<ScheduleRow>(
        html`<abode-schedule-row
          .schedule=${createMockSchedule({
            id: '',
            weekdays: [],
            arm_time: '22:00',
            disarm_time: '06:00',
          })}
          .canEdit=${true}
        ></abode-schedule-row>`,
      );
      await elementUpdated(el);

      let cancelNewFired = false;
      el.addEventListener('cancel-new', () => {
        cancelNewFired = true;
      });

      const cancelBtn = el.shadowRoot!.querySelector<HTMLButtonElement>('.btn.secondary');
      cancelBtn!.click();
      await elementUpdated(el);

      expect(cancelNewFired).to.be.true;
    });
  });

  describe('delete', () => {
    it('clicking delete dispatches delete event with id', async () => {
      const el = await fixture<ScheduleRow>(
        html`<abode-schedule-row
          .schedule=${createMockSchedule({ id: 'del-me' })}
          .canEdit=${true}
        ></abode-schedule-row>`,
      );
      await elementUpdated(el);

      let deleteDetail: { id: string } | null = null;
      el.addEventListener('delete', (e: Event) => {
        deleteDetail = (e as CustomEvent).detail;
      });

      const deleteBtn = el.shadowRoot!.querySelector<HTMLButtonElement>(
        '[aria-label="Delete schedule"]',
      );
      deleteBtn!.click();
      await elementUpdated(el);

      expect(deleteDetail).to.not.be.null;
      expect(deleteDetail!.id).to.equal('del-me');
    });
  });
});
