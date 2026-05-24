/**
 * Type definitions for Abode Security frontend.
 */

// Home Assistant types

// Minimal shape of an HA state object. The real HassEntity has many more
// fields (attributes, last_changed, context, …); we only narrow to what the
// panel actually reads. The Lit `@property` reassignment-triggers-update
// mechanic relies on HA replacing `hass` wholesale on state changes, so
// reading `hass.states[id].state` at render time is enough to stay live.
export interface HassEntityState {
  entity_id: string;
  state: string;
  attributes?: Record<string, unknown>;
}

export interface HomeAssistant {
  callWS<T>(params: { type: string; [key: string]: unknown }): Promise<T>;
  states: Record<string, HassEntityState>;
}

/**
 * Read an entity's current state from `hass.states` with a fallback.
 *
 * Used by the action editor (sensor pills) and actions tab (stale-sensor
 * badge) so they react to live state changes without re-fetching: HA
 * reassigns `hass` on every state change, and Lit re-renders on property
 * reassignment, so reading from `hass.states` at render time is enough.
 *
 * The `fallback` covers the brief window before the panel has the entity
 * in `hass.states` (test harnesses, cold-start, or an entity created
 * after the panel loaded) — without it, picking the right pill state
 * would flicker through "unavailable" on first paint.
 */
export function getEntityState(
  hass: HomeAssistant,
  entityId: string,
  fallback = 'unavailable',
): string {
  return hass.states?.[entityId]?.state ?? fallback;
}

/**
 * Predicate: would this state prevent the action_trigger pipeline from
 * firing? The backend filter requires a clean `off → on` transition
 * (see `custom_components/abode_security/action_trigger.py`); both
 * `unavailable` and `unknown` are dead-ends for that. We treat them
 * identically in the UI — pill colour, partition order, header count,
 * and the saved-action warning chip — so the user sees one consistent
 * story whichever surface they're looking at.
 *
 * Centralising this is load-bearing: a previous iteration of this
 * helper split the predicate across four call sites, and reviewers
 * caught that `unknown` rendered as a red "unavailable" pill while
 * still counting as healthy in the header count and warning chip.
 * Anyone adding a fifth surface should reuse this, not redefine it.
 */
export function isUnavailableState(state: string): boolean {
  return state === 'unavailable' || state === 'unknown';
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
  // Enabled actions only — preserves the original semantics so consumers
  // counting "active wiring" don't change behavior.
  action_count: number;
  // Disabled actions for this mode (#123). Optional because older backends
  // predating this field may omit it; render as 0 when missing.
  disabled_action_count?: number;
  active: boolean;
}

export interface SensorEntity {
  entity_id: string;
  name: string;
  state: string;
  // Optional HA area name surfaced next to each sensor in the editor (#120).
  // Falls back to the device's area on the backend; `null` when neither is
  // set. Older backends predating #120 may omit this entirely, hence optional.
  area?: string | null;
}

// Backend keys sensors by Home Assistant `device_class`, which is open-ended
// (garage_door, gas, heat, vibration, …). Use a string-keyed map so unknown
// categories surface in the editor instead of being silently dropped.
export type SensorsByCategory = Partial<Record<string, SensorEntity[]>>;

// Single source of truth for the well-known sensor categories. Backend can
// still return categories outside this set (see SensorsByCategory); these are
// the ones we recognize for typed iterators and label maps.
//
// The semantic camera-detection categories (person, vehicle, smoke_alarm, …)
// are emitted by the backend (#135) when an entity has no `device_class` but
// a recognizable translation_key — they're not HA `device_class` values.
export const SENSOR_CATEGORIES = [
  'door',
  'window',
  'motion',
  'moisture',
  'smoke',
  'connectivity',
  // Camera smart-detect (#135)
  'person',
  'vehicle',
  'animal',
  'object',
  'package',
  'face',
  'visitor',
  'smoke_alarm',
  'co_alarm',
  'speaking',
  'barking',
  'baby_cry',
  'glass_break',
  'siren',
  'other',
] as const;
export type SensorCategory = (typeof SENSOR_CATEGORIES)[number];

export interface AlarmEntity {
  entity_id: string;
  name: string;
  type: string;
}

export interface AbodeCamera {
  entity_id: string;
  name: string;
  area: string | null;
}
