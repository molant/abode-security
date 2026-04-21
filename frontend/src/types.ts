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

// Backend omits categories with zero sensors, so all keys are optional.
export type SensorCategory =
  | 'door'
  | 'window'
  | 'motion'
  | 'moisture'
  | 'smoke'
  | 'connectivity'
  | 'other';

export type SensorsByCategory = Partial<Record<SensorCategory, SensorEntity[]>>;

export interface AlarmEntity {
  entity_id: string;
  name: string;
  type: string;
}

export interface AbodeConfig {
  debounce_seconds: number;
}
