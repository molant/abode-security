/**
 * WebSocket API helpers for Abode Security frontend.
 */

import type {
  HomeAssistant,
  AbodeAction,
  AbodeCamera,
  AbodeMode,
  Mode,
  SensorsByCategory,
  AlarmEntity,
} from './types';

/**
 * Fetch all actions.
 */
export async function fetchActions(hass: HomeAssistant): Promise<AbodeAction[]> {
  const response = await hass.callWS<{ actions: AbodeAction[] }>({
    type: 'abode_security/actions/list',
  });
  return response.actions;
}

/**
 * Fetch all modes with their action counts, plus the alarm panel entity_id
 * the frontend should watch for live state reactivity (#124).
 *
 * `panel_entity_id` is null when no abode alarm_control_panel is registered
 * (e.g. accounts without an alarm device). It is also optional in the type
 * so older backends (and test fixtures) that omit the field round-trip
 * cleanly — consumers must fall back to the cached `active` flag in that
 * case.
 */
export interface ModesListResponse {
  modes: AbodeMode[];
  panel_entity_id?: string | null;
}

export async function fetchModes(hass: HomeAssistant): Promise<ModesListResponse> {
  return hass.callWS<ModesListResponse>({
    type: 'abode_security/modes/list',
  });
}

/**
 * Switch the active Abode mode. Backend delegates to the corresponding
 * alarm_control_panel service (alarm_disarm / alarm_arm_home / alarm_arm_away).
 */
export async function setMode(hass: HomeAssistant, modeId: Mode): Promise<void> {
  await hass.callWS({
    type: 'abode_security/modes/set',
    mode_id: modeId,
  });
}

/**
 * Fetch sensors grouped by category.
 */
export async function fetchSensors(hass: HomeAssistant): Promise<SensorsByCategory> {
  const response = await hass.callWS<{ sensors: SensorsByCategory }>({
    type: 'abode_security/entities/sensors',
  });
  return response.sensors;
}

/**
 * Fetch alarm entities.
 */
export async function fetchAlarms(hass: HomeAssistant): Promise<AlarmEntity[]> {
  const response = await hass.callWS<{ alarms: AlarmEntity[] }>({
    type: 'abode_security/entities/alarms',
  });
  return response.alarms;
}

/**
 * Fetch every camera entity in Home Assistant (the integration is
 * camera-source-agnostic — any HA camera is a valid notification
 * deep-link target).
 */
export async function fetchCameras(hass: HomeAssistant): Promise<AbodeCamera[]> {
  const response = await hass.callWS<{ cameras: AbodeCamera[] }>({
    type: 'abode_security/entities/cameras',
  });
  return response.cameras;
}

/**
 * Create a new action.
 */
export async function createAction(
  hass: HomeAssistant,
  data: Partial<AbodeAction>,
): Promise<AbodeAction> {
  return hass.callWS<AbodeAction>({
    type: 'abode_security/actions/create',
    ...data,
  });
}

/**
 * Update an existing action.
 */
export async function updateAction(
  hass: HomeAssistant,
  id: string,
  data: Partial<AbodeAction>,
): Promise<AbodeAction> {
  return hass.callWS<AbodeAction>({
    type: 'abode_security/actions/update',
    action_id: id,
    ...data,
  });
}

/**
 * Delete an action.
 */
export async function deleteAction(hass: HomeAssistant, id: string): Promise<void> {
  await hass.callWS({
    type: 'abode_security/actions/delete',
    action_id: id,
  });
}

/**
 * Test an action (triggers alarms immediately).
 */
export async function testAction(hass: HomeAssistant, id: string): Promise<void> {
  await hass.callWS({
    type: 'abode_security/actions/test',
    action_id: id,
  });
}

/**
 * Fetch the integration's runtime config. Includes `debug_logging` (read-only,
 * mirrored from the config entry options) so the UI can gate power-user
 * affordances like the per-action "copy ID" button.
 */
export interface AbodeIntegrationConfig {
  debounce_seconds: number;
  debug_logging: boolean;
}

export async function fetchIntegrationConfig(hass: HomeAssistant): Promise<AbodeIntegrationConfig> {
  return hass.callWS<AbodeIntegrationConfig>({
    type: 'abode_security/config/get',
  });
}
