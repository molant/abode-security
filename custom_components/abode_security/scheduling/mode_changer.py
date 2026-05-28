"""ModeChanger protocol and HAModeChanger implementation."""

from __future__ import annotations

import uuid
from typing import Protocol

from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceNotFound

from ..action_manager import VALID_MODES as _ACTION_VALID_MODES
from ..const import CONTEXT_ID_PREFIX
from ..helpers import find_abode_alarm_panel
from .models import ChangeSource

MODE_TO_SERVICE: dict[str, str] = {
    "standby": "alarm_disarm",
    "home": "alarm_arm_home",
    "away": "alarm_arm_away",
}
VALID_MODES: frozenset[str] = frozenset(MODE_TO_SERVICE)

# Guard against MODE_TO_SERVICE drifting from action_manager.VALID_MODES.
# Both sets must stay identical; if a new mode is added to one, add it to both.
# RuntimeError (not assert) so the guard survives python -O optimized builds.
if frozenset(_ACTION_VALID_MODES) != VALID_MODES:
    raise RuntimeError("mode_changer.VALID_MODES must match action_manager.VALID_MODES")
del _ACTION_VALID_MODES


class ModeChangeFailed(HomeAssistantError):
    """Raised when the underlying alarm_control_panel service call fails."""


class ModeChanger(Protocol):
    """Protocol for mode-change operations."""

    async def async_set_mode(
        self,
        target: str,
        source: ChangeSource,
        *,
        pair_id: str | None = None,
    ) -> None: ...


class HAModeChanger:
    """Production implementation that calls the alarm_control_panel domain."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    def _build_context(
        self, source: ChangeSource, pair_id: str | None
    ) -> Context | None:
        if source in (
            ChangeSource.SCHEDULE_ARM,
            ChangeSource.SCHEDULE_DISARM,
            ChangeSource.RECONCILE_DISARM,
        ):
            if pair_id is None:
                raise ValueError(f"pair_id required for {source}")
            return Context(id=f"{CONTEXT_ID_PREFIX}{pair_id}_{uuid.uuid4().hex[:8]}")
        return None  # USER_WS gets default Context()

    async def async_set_mode(
        self,
        target: str,
        source: ChangeSource,
        *,
        pair_id: str | None = None,
    ) -> None:
        """Set the alarm mode by calling the alarm_control_panel service.

        Raises:
            ValueError: if target is not a valid mode, or pair_id is missing for
                schedule sources.
            ModeChangeFailed: if the panel is unavailable or the service call fails.
        """
        if target not in VALID_MODES:
            raise ValueError(f"Invalid mode: {target!r}")
        panel_state = find_abode_alarm_panel(self._hass)
        if panel_state is None:
            raise ModeChangeFailed("No Abode alarm_control_panel entity registered")
        ctx = self._build_context(source, pair_id)
        try:
            await self._hass.services.async_call(
                "alarm_control_panel",
                MODE_TO_SERVICE[target],
                {"entity_id": panel_state.entity_id},
                blocking=True,
                context=ctx,
            )
        except (HomeAssistantError, ServiceNotFound, ValueError) as err:
            raise ModeChangeFailed(str(err)) from err
