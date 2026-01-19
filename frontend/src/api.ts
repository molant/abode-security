/**
 * WebSocket API helpers for Abode Security frontend.
 */

import type {
  HomeAssistant,
  AbodeAction,
  AbodeMode,
  SensorsByCategory,
  AlarmEntity,
  AbodeConfig,
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
 * Fetch all modes with their action counts.
 */
export async function fetchModes(hass: HomeAssistant): Promise<AbodeMode[]> {
  const response = await hass.callWS<{ modes: AbodeMode[] }>({
    type: 'abode_security/modes/list',
  });
  return response.modes;
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
 * Fetch configuration.
 */
export async function fetchConfig(hass: HomeAssistant): Promise<AbodeConfig> {
  const response = await hass.callWS<{ config: AbodeConfig }>({
    type: 'abode_security/config/get',
  });
  return response.config;
}

/**
 * Create a new action.
 */
export async function createAction(
  hass: HomeAssistant,
  data: Partial<AbodeAction>
): Promise<AbodeAction> {
  const response = await hass.callWS<{ action: AbodeAction }>({
    type: 'abode_security/actions/create',
    ...data,
  });
  return response.action;
}

/**
 * Update an existing action.
 */
export async function updateAction(
  hass: HomeAssistant,
  id: string,
  data: Partial<AbodeAction>
): Promise<AbodeAction> {
  const response = await hass.callWS<{ action: AbodeAction }>({
    type: 'abode_security/actions/update',
    action_id: id,
    ...data,
  });
  return response.action;
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
