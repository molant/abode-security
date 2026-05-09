/**
 * Type definitions for Abode Security frontend.
 */

// Home Assistant types
export interface HomeAssistant {
  callWS<T>(params: { type: string; [key: string]: unknown }): Promise<T>;
}

// Action types
export interface AbodeAction {
  id: string;
  name: string;
  modes: string[];
  sensor_entity_ids: string[];
  alarm_entity_ids: string[];
  enabled: boolean;
  delay_seconds: number;
  last_triggered: string | null;
  trigger_count: number;
}

export interface AbodeMode {
  id: string;
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

// Legacy literal union of well-known categories. Kept for callsites that want
// a typed iterator or label map; not used as the key type of SensorsByCategory.
export type SensorCategory =
  | 'door'
  | 'window'
  | 'motion'
  | 'moisture'
  | 'smoke'
  | 'connectivity'
  | 'other';

export interface AlarmEntity {
  entity_id: string;
  name: string;
  type: string;
}

export interface AbodeConfig {
  debounce_seconds: number;
}
