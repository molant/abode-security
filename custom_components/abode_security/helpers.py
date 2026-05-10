"""Shared helpers for the Abode Security integration."""

from __future__ import annotations

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN


def find_abode_alarm_panel(hass: HomeAssistant) -> State | None:
    """Return the State of the Abode alarm_control_panel, or None.

    Resolves via the entity registry first (matches platform=DOMAIN
    + domain="alarm_control_panel"), so a user-renamed entity_id still
    resolves correctly.

    Falls back to a `state.entity_id.startswith("alarm_control_panel.abode")`
    scan for two cases:
      1. Older installs that pre-date config-entry registration with the
         current platform name.
      2. Test scenarios that set states directly via `hass.states.async_set`
         without going through the entity registry.

    Both `websocket_api` (modes/list, modes/set) and `action_trigger` use
    this helper to resolve the panel — keeping the lookup in one place
    eliminates the prefix-match drift that was previously duplicated
    between the two modules (#44).
    """
    registry = er.async_get(hass)
    for entry in registry.entities.values():
        if entry.domain == "alarm_control_panel" and entry.platform == DOMAIN:
            state = hass.states.get(entry.entity_id)
            if state is not None:
                return state

    for state in hass.states.async_all("alarm_control_panel"):
        if state.entity_id.startswith("alarm_control_panel.abode"):
            return state
    return None
