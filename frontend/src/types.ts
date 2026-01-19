/**
 * Type definitions for Abode Security frontend.
 */

// Home Assistant types
export interface HomeAssistant {
  callWS<T>(params: { type: string; [key: string]: unknown }): Promise<T>;
  states: { [entity_id: string]: HassState };
}

export interface HassState {
  entity_id: string;
  state: string;
  attributes: { friendly_name?: string; [key: string]: unknown };
}

// Panel types
export interface AbodePanel {
  mode: {
    area_1: 'standby' | 'home' | 'away';
    area_1_label: string;
  };
  online: string;
  battery: string;
}

export interface AbodeDevice {
  id: string;
  name: string;
  type: string;
  type_tag: string;
  status: string;
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

export interface SensorsByCategory {
  door: SensorEntity[];
  window: SensorEntity[];
  motion: SensorEntity[];
  moisture: SensorEntity[];
  smoke: SensorEntity[];
  connectivity: SensorEntity[];
  other: SensorEntity[];
}

export interface AlarmEntity {
  entity_id: string;
  name: string;
  type: string;
}

export interface AbodeConfig {
  debounce_seconds: number;
}
