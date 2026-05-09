/**
 * Type definitions for Abode Security frontend.
 */

// Home Assistant types
export interface HomeAssistant {
  callWS<T>(params: { type: string; [key: string]: unknown }): Promise<T>;
}

// Single source of truth for the closed set of mode IDs. Iterating MODES
// in render keeps the UI list and the type definition in lockstep — adding a
// fourth mode is a one-line change. `as const` narrows the array to a
// readonly tuple of literals so `Mode` derives a string-literal union.
export const MODES = ['standby', 'home', 'away'] as const;
export type Mode = (typeof MODES)[number];

// Action types
export interface AbodeAction {
  id: string;
  name: string;
  modes: Mode[];
  sensor_entity_ids: string[];
  alarm_entity_ids: string[];
  enabled: boolean;
  delay_seconds: number;
  last_triggered: string | null;
  trigger_count: number;
}

export interface AbodeMode {
  id: Mode;
  name: string;
  icon: string;
  action_count: number;
  active: boolean;
}

export interface SensorEntity {
  entity_id: string;
  name: string;
  state: string;
}

// Backend keys sensors by Home Assistant `device_class`, which is open-ended
// (garage_door, gas, heat, vibration, …). Use a string-keyed map so unknown
// categories surface in the editor instead of being silently dropped.
export type SensorsByCategory = Partial<Record<string, SensorEntity[]>>;

// Single source of truth for the well-known sensor categories. Backend can
// still return categories outside this set (see SensorsByCategory); these are
// the ones we recognize for typed iterators and label maps.
export const SENSOR_CATEGORIES = [
  'door',
  'window',
  'motion',
  'moisture',
  'smoke',
  'connectivity',
  'other',
] as const;
export type SensorCategory = (typeof SENSOR_CATEGORIES)[number];

export interface AlarmEntity {
  entity_id: string;
  name: string;
  type: string;
}

export interface AbodeConfig {
  debounce_seconds: number;
}
