/**
 * Test helpers and mocks for frontend unit tests.
 */

import type { LitElement } from 'lit';
import type { HomeAssistant, AbodeAction, SensorsByCategory, AlarmEntity, AbodeMode } from '../types';

/**
 * Create a mock HomeAssistant object.
 *
 * By default, returns empty arrays/objects for known WS endpoints and
 * `{ success: true }` for unknown ones — keeps existing rendering tests
 * (which only need _something_ to come back from connectedCallback) terse.
 *
 * Pass `strict: true` to throw on any unmocked WS call. Use that in
 * mutation tests where a silent default response would mask a bug
 * (e.g., asserting `createAction` was called when in reality the
 * fall-through `{ success: true }` swallowed it).
 *
 * NOTE: `strict` only affects the *default* callWS. If you also pass a
 * `callWS` override, `strict` has no effect — your override replaces
 * the default entirely, and is responsible for its own un-mocked-call
 * handling (typically by `throw new Error(...)` in the fall-through).
 */
export function createMockHass(
  overrides: { strict?: boolean } & Partial<HomeAssistant> = {},
): HomeAssistant {
  const { strict = false, ...rest } = overrides;

  const defaultCallWS = async (params: { type: string }) => {
    if (params.type === 'abode_security/modes/list') {
      return { modes: [] };
    }
    if (params.type === 'abode_security/actions/list') {
      return { actions: [] };
    }
    if (params.type === 'abode_security/entities/sensors') {
      return { sensors: {} };
    }
    if (params.type === 'abode_security/entities/alarms') {
      return { alarms: [] };
    }
    if (strict) {
      throw new Error(`Unmocked WS call: ${params.type}`);
    }
    return { success: true };
  };

  return {
    callWS: defaultCallWS,
    ...rest,
  } as HomeAssistant;
}

/**
 * Create a mock action.
 */
export function createMockAction(overrides: Partial<AbodeAction> = {}): AbodeAction {
  return {
    id: 'test-action-id',
    name: 'Test Action',
    modes: ['home'],
    sensor_entity_ids: ['binary_sensor.door'],
    alarm_entity_ids: ['switch.panic_alarm'],
    enabled: true,
    delay_seconds: 0,
    last_triggered: null,
    trigger_count: 0,
    ...overrides,
  };
}

/**
 * Create mock sensors grouped by category.
 */
export function createMockSensors(): SensorsByCategory {
  return {
    door: [
      { entity_id: 'binary_sensor.front_door', name: 'Front Door', state: 'off' },
      { entity_id: 'binary_sensor.back_door', name: 'Back Door', state: 'off' },
    ],
    motion: [
      { entity_id: 'binary_sensor.living_room_motion', name: 'Living Room Motion', state: 'off' },
    ],
    window: [
      { entity_id: 'binary_sensor.kitchen_window', name: 'Kitchen Window', state: 'off' },
    ],
  };
}

/**
 * Create mock alarm entities.
 */
export function createMockAlarms(): AlarmEntity[] {
  return [
    { entity_id: 'switch.abode_panic_alarm', name: 'Panic Alarm', type: 'panic' },
    { entity_id: 'switch.abode_fire_alarm', name: 'Fire Alarm', type: 'fire' },
    { entity_id: 'switch.abode_medical_alarm', name: 'Medical Alarm', type: 'medical' },
  ];
}

/**
 * Create mock modes.
 */
export function createMockModes(): AbodeMode[] {
  return [
    { id: 'standby', name: 'Standby', icon: 'mdi:lock-open', action_count: 0, active: false },
    { id: 'home', name: 'Home', icon: 'mdi:home', action_count: 2, active: true },
    { id: 'away', name: 'Away', icon: 'mdi:shield-check', action_count: 1, active: false },
  ];
}

/**
 * Wait for the next render cycle.
 */
export async function nextFrame(): Promise<void> {
  return new Promise(resolve => requestAnimationFrame(() => resolve()));
}

/**
 * Wait for element to update.
 */
export async function elementUpdated(element: Element & { updateComplete?: Promise<unknown> }): Promise<void> {
  if (element.updateComplete) {
    await element.updateComplete;
  }
  await nextFrame();
}

/**
 * Inject test-only state onto a Lit element and wait for the next render.
 *
 * Collapses the recurring three-step pattern below into one call:
 *
 *     // @ts-expect-error - accessing private property for testing
 *     el._actions = actions;
 *     // @ts-expect-error - accessing private property for testing
 *     el._loading = false;
 *     await elementUpdated(el);
 *
 * Becomes:
 *
 *     await setState(el, { _actions: actions, _loading: false } as Partial<X>);
 *
 * The `as Partial<TheElement>` cast is required to bypass the
 * private-modifier compile error. It does NOT enforce strict
 * excess-property checks — a typo like `_actuons` will still type-check
 * (TypeScript treats `as` as a developer-asserted compatibility claim).
 * Treat it as a "this object is meant to be a state patch" hint, not as
 * a typo guard. Don't substitute `as any`, which loses even the basic
 * shape constraint and the helper's other type guarantees.
 *
 * Used by mutation-flow tests added in #31.
 */
export async function setState<T extends LitElement>(
  element: T,
  patch: Partial<T>,
): Promise<void> {
  // Single, intentional, type-erased assignment — the alternative is
  // sprinkling @ts-expect-error at every call site.
  Object.assign(element, patch);
  await elementUpdated(element);
}
