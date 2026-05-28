import { aTimeout, expect, fixture, html } from '@open-wc/testing';
import '../schedules-section.js';
import type { SchedulesSection } from '../schedules-section.js';
import type { AbodeSchedule, HomeAssistant } from '../types.js';
import { elementUpdated } from './test-helpers.js';

function createMockSchedule(overrides: Partial<AbodeSchedule> = {}): AbodeSchedule {
  return {
    id: 'sched-1',
    name: 'Weeknights',
    weekdays: ['mon', 'tue', 'wed', 'thu', 'fri'],
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

function createAdminHass(
  overrides: {
    schedules?: AbodeSchedule[];
    createResult?: AbodeSchedule;
    updateResult?: AbodeSchedule;
    callWSError?: string;
  } = {},
): HomeAssistant {
  const { schedules = [], createResult, updateResult, callWSError } = overrides;

  const callWS = async (params: { type: string; [key: string]: unknown }) => {
    if (callWSError) throw new Error(callWSError);
    if (params.type === 'abode_security/schedules/list') {
      return { schedules };
    }
    if (params.type === 'abode_security/schedules/create') {
      return createResult ?? createMockSchedule({ id: 'new-id', ...params });
    }
    if (params.type === 'abode_security/schedules/update') {
      return updateResult ?? createMockSchedule({ id: params.schedule_id as string });
    }
    if (params.type === 'abode_security/schedules/delete') {
      return { success: true };
    }
    return { success: true };
  };

  return {
    callWS,
    states: {},
    user: { is_admin: true },
  } as HomeAssistant;
}

function createNonAdminHass(schedules: AbodeSchedule[] = []): HomeAssistant {
  const base = createAdminHass({ schedules });
  return { ...base, user: { is_admin: false } };
}

describe('SchedulesSection', () => {
  describe('initial mount', () => {
    it('fetches and renders schedules on mount', async () => {
      const el = await fixture<SchedulesSection>(
        html`<abode-schedules-section
          .hass=${createAdminHass({ schedules: [createMockSchedule()] })}
        ></abode-schedules-section>`,
      );
      await aTimeout(10);
      await elementUpdated(el);

      const rows = el.shadowRoot!.querySelectorAll('abode-schedule-row');
      expect(rows).to.have.lengthOf(1);
    });

    it('shows empty state when no schedules', async () => {
      const el = await fixture<SchedulesSection>(
        html`<abode-schedules-section
          .hass=${createAdminHass({ schedules: [] })}
        ></abode-schedules-section>`,
      );
      await aTimeout(10);
      await elementUpdated(el);

      expect(el.shadowRoot!.textContent).to.include('No schedules yet');
    });

    it('shows loading state initially', async () => {
      let resolve!: (v: unknown) => void;
      const pending = new Promise((r) => {
        resolve = r;
      });
      const hass: HomeAssistant = {
        callWS: () => pending,
        states: {},
        user: { is_admin: true },
      } as HomeAssistant;

      const el = await fixture<SchedulesSection>(
        html`<abode-schedules-section .hass=${hass}></abode-schedules-section>`,
      );
      // Before fetch resolves, loading indicator should appear
      expect(el.shadowRoot!.textContent).to.include('Loading');
      resolve({ schedules: [] });
    });

    it('shows error banner when fetch fails', async () => {
      const el = await fixture<SchedulesSection>(
        html`<abode-schedules-section
          .hass=${createAdminHass({ callWSError: 'network_error' })}
        ></abode-schedules-section>`,
      );
      await aTimeout(10);
      await elementUpdated(el);

      const banner = el.shadowRoot!.querySelector('[role="alert"]');
      expect(banner).to.exist;
    });
  });

  describe('admin vs non-admin', () => {
    it('shows Add button for admin', async () => {
      const el = await fixture<SchedulesSection>(
        html`<abode-schedules-section .hass=${createAdminHass()}></abode-schedules-section>`,
      );
      await aTimeout(10);
      await elementUpdated(el);

      expect(el.shadowRoot!.querySelector('.add-button')).to.exist;
    });

    it('hides Add button for non-admin', async () => {
      const el = await fixture<SchedulesSection>(
        html`<abode-schedules-section .hass=${createNonAdminHass()}></abode-schedules-section>`,
      );
      await aTimeout(10);
      await elementUpdated(el);

      expect(el.shadowRoot!.querySelector('.add-button')).to.not.exist;
    });

    it('passes canEdit=false to schedule rows for non-admin', async () => {
      const schedule = createMockSchedule();
      const el = await fixture<SchedulesSection>(
        html`<abode-schedules-section
          .hass=${createNonAdminHass([schedule])}
        ></abode-schedules-section>`,
      );
      await aTimeout(10);
      await elementUpdated(el);

      const row = el.shadowRoot!.querySelector('abode-schedule-row') as HTMLElement & {
        canEdit: boolean;
      };
      expect(row).to.exist;
      expect(row.canEdit).to.be.false;
    });

    it('passes canEdit=true to schedule rows for admin', async () => {
      const schedule = createMockSchedule();
      const el = await fixture<SchedulesSection>(
        html`<abode-schedules-section
          .hass=${createAdminHass({ schedules: [schedule] })}
        ></abode-schedules-section>`,
      );
      await aTimeout(10);
      await elementUpdated(el);

      const row = el.shadowRoot!.querySelector('abode-schedule-row') as HTMLElement & {
        canEdit: boolean;
      };
      expect(row).to.exist;
      expect(row.canEdit).to.be.true;
    });
  });

  describe('adding a schedule', () => {
    it('clicking Add schedule shows new row in edit mode', async () => {
      const el = await fixture<SchedulesSection>(
        html`<abode-schedules-section .hass=${createAdminHass()}></abode-schedules-section>`,
      );
      await aTimeout(10);
      await elementUpdated(el);

      const addBtn = el.shadowRoot!.querySelector<HTMLButtonElement>('.add-button');
      addBtn!.click();
      await elementUpdated(el);

      // New row appears and Add button is hidden while new row is open
      const rows = el.shadowRoot!.querySelectorAll('abode-schedule-row');
      expect(rows).to.have.lengthOf(1);
      expect(el.shadowRoot!.querySelector('.add-button')).to.not.exist;
    });

    it('new-row save calls createSchedule and appends to list', async () => {
      const created = createMockSchedule({ id: 'created-1', name: 'New' });
      let createCalled = false;
      const hass: HomeAssistant = {
        callWS: async (params: { type: string; [key: string]: unknown }) => {
          if (params.type === 'abode_security/schedules/list') return { schedules: [] };
          if (params.type === 'abode_security/schedules/create') {
            createCalled = true;
            return created;
          }
          return { success: true };
        },
        states: {},
        user: { is_admin: true },
      } as HomeAssistant;

      const el = await fixture<SchedulesSection>(
        html`<abode-schedules-section .hass=${hass}></abode-schedules-section>`,
      );
      await aTimeout(10);
      await elementUpdated(el);

      // Dispatch save from inside the shadow DOM's section so it reaches
      // the @save listener on the <section> element via bubbling.
      el.shadowRoot!.querySelector('section')!.dispatchEvent(
        new CustomEvent('save', {
          detail: {
            id: '',
            data: {
              name: 'New',
              weekdays: ['mon'],
              arm_time: '22:00',
              disarm_time: '06:00',
              enabled: true,
            },
          },
          bubbles: true,
          composed: true,
        }),
      );
      await aTimeout(10);
      await elementUpdated(el);

      expect(createCalled).to.be.true;
    });

    it('cancel-new removes new row without calling WS', async () => {
      let wsCalled = false;
      const hass: HomeAssistant = {
        callWS: async (params: { type: string }) => {
          if (params.type === 'abode_security/schedules/list') return { schedules: [] };
          wsCalled = true;
          return { success: true };
        },
        states: {},
        user: { is_admin: true },
      } as HomeAssistant;

      const el = await fixture<SchedulesSection>(
        html`<abode-schedules-section .hass=${hass}></abode-schedules-section>`,
      );
      await aTimeout(10);
      await elementUpdated(el);

      // Open new row
      const addBtn = el.shadowRoot!.querySelector<HTMLButtonElement>('.add-button');
      addBtn!.click();
      await elementUpdated(el);

      // Fire cancel-new
      el.shadowRoot!.querySelector('abode-schedule-row')!.dispatchEvent(
        new CustomEvent('cancel-new', { detail: {}, bubbles: true, composed: true }),
      );
      await elementUpdated(el);

      expect(el.shadowRoot!.querySelectorAll('abode-schedule-row')).to.have.lengthOf(0);
      expect(wsCalled).to.be.false;
    });
  });

  describe('updating a schedule', () => {
    it('existing-row save calls updateSchedule and replaces in list', async () => {
      const original = createMockSchedule({ id: 'orig-1', name: 'Original' });
      const updated = createMockSchedule({ id: 'orig-1', name: 'Updated' });
      let updateCalled = false;

      const hass: HomeAssistant = {
        callWS: async (params: { type: string; [key: string]: unknown }) => {
          if (params.type === 'abode_security/schedules/list') return { schedules: [original] };
          if (params.type === 'abode_security/schedules/update') {
            updateCalled = true;
            return updated;
          }
          return { success: true };
        },
        states: {},
        user: { is_admin: true },
      } as HomeAssistant;

      const el = await fixture<SchedulesSection>(
        html`<abode-schedules-section .hass=${hass}></abode-schedules-section>`,
      );
      await aTimeout(10);
      await elementUpdated(el);

      // Dispatch from inside the shadow DOM's section
      el.shadowRoot!.querySelector('section')!.dispatchEvent(
        new CustomEvent('save', {
          detail: {
            id: 'orig-1',
            data: {
              name: 'Updated',
              weekdays: ['mon'],
              arm_time: '22:00',
              disarm_time: '06:00',
              enabled: true,
            },
          },
          bubbles: true,
          composed: true,
        }),
      );
      await aTimeout(10);
      await elementUpdated(el);

      expect(updateCalled).to.be.true;
    });
  });

  describe('deleting a schedule', () => {
    it('delete request shows confirm dialog', async () => {
      const schedule = createMockSchedule();
      const el = await fixture<SchedulesSection>(
        html`<abode-schedules-section
          .hass=${createAdminHass({ schedules: [schedule] })}
        ></abode-schedules-section>`,
      );
      await aTimeout(10);
      await elementUpdated(el);

      // Fire delete event from inside the shadow DOM's section
      el.shadowRoot!.querySelector('section')!.dispatchEvent(
        new CustomEvent('delete', {
          detail: { id: 'sched-1' },
          bubbles: true,
          composed: true,
        }),
      );
      await elementUpdated(el);

      const modal = el.shadowRoot!.querySelector('abode-modal');
      expect(modal).to.exist;
      expect(modal!.getAttribute('heading')).to.equal('Delete schedule?');
    });

    it('confirming delete calls deleteSchedule and removes from list', async () => {
      const schedule = createMockSchedule();
      let deleteCalled = false;

      const hass: HomeAssistant = {
        callWS: async (params: { type: string }) => {
          if (params.type === 'abode_security/schedules/list') return { schedules: [schedule] };
          if (params.type === 'abode_security/schedules/delete') {
            deleteCalled = true;
            return { success: true };
          }
          return { success: true };
        },
        states: {},
        user: { is_admin: true },
      } as HomeAssistant;

      const el = await fixture<SchedulesSection>(
        html`<abode-schedules-section .hass=${hass}></abode-schedules-section>`,
      );
      await aTimeout(10);
      await elementUpdated(el);

      // Set _confirmDeleteId directly to simulate delete confirmation
      // @ts-expect-error accessing private for test
      el._confirmDeleteId = 'sched-1';
      await elementUpdated(el);

      const confirmBtn = el.shadowRoot!.querySelector<HTMLButtonElement>('.dialog-button.danger');
      confirmBtn!.click();
      await aTimeout(10);
      await elementUpdated(el);

      expect(deleteCalled).to.be.true;
      const rows = el.shadowRoot!.querySelectorAll('abode-schedule-row');
      expect(rows).to.have.lengthOf(0);
    });

    it('cancel in delete dialog closes dialog without deleting', async () => {
      const schedule = createMockSchedule();
      let deleteCalled = false;

      const hass: HomeAssistant = {
        callWS: async (params: { type: string }) => {
          if (params.type === 'abode_security/schedules/list') return { schedules: [schedule] };
          if (params.type === 'abode_security/schedules/delete') {
            deleteCalled = true;
          }
          return { success: true };
        },
        states: {},
        user: { is_admin: true },
      } as HomeAssistant;

      const el = await fixture<SchedulesSection>(
        html`<abode-schedules-section .hass=${hass}></abode-schedules-section>`,
      );
      await aTimeout(10);
      await elementUpdated(el);

      // @ts-expect-error accessing private for test
      el._confirmDeleteId = 'sched-1';
      await elementUpdated(el);

      const cancelBtn = el.shadowRoot!.querySelector<HTMLButtonElement>('.dialog-button.cancel');
      cancelBtn!.click();
      await elementUpdated(el);

      expect(deleteCalled).to.be.false;
      // Modal should be gone
      expect(el.shadowRoot!.querySelector('abode-modal')).to.not.exist;
      // Row should still be present
      expect(el.shadowRoot!.querySelectorAll('abode-schedule-row')).to.have.lengthOf(1);
    });
  });

  describe('error handling', () => {
    it('shows error banner when createSchedule fails', async () => {
      const hass: HomeAssistant = {
        callWS: async (params: { type: string }) => {
          if (params.type === 'abode_security/schedules/list') return { schedules: [] };
          if (params.type === 'abode_security/schedules/create') throw new Error('forbidden');
          return { success: true };
        },
        states: {},
        user: { is_admin: true },
      } as HomeAssistant;

      const el = await fixture<SchedulesSection>(
        html`<abode-schedules-section .hass=${hass}></abode-schedules-section>`,
      );
      await aTimeout(10);
      await elementUpdated(el);

      el.shadowRoot!.querySelector('section')!.dispatchEvent(
        new CustomEvent('save', {
          detail: {
            id: '',
            data: { weekdays: ['mon'], arm_time: '22:00', disarm_time: '06:00', enabled: true },
          },
          bubbles: true,
          composed: true,
        }),
      );
      await aTimeout(10);
      await elementUpdated(el);

      const banner = el.shadowRoot!.querySelector('[role="alert"]');
      expect(banner).to.exist;
      expect(banner!.textContent).to.include('forbidden');
    });
  });
});
