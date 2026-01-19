/**
 * Test helpers and mocks for frontend unit tests.
 */

import type { HomeAssistant, AbodeAction, SensorsByCategory, AlarmEntity, AbodeMode } from '../types';

/**
 * Create a mock HomeAssistant object.
 */
export function createMockHass(overrides: Partial<HomeAssistant> = {}): HomeAssistant {
  return {
    callWS: async () => ({ success: true }),
    states: {},
    ...overrides,
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
