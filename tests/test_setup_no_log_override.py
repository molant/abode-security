"""Regression test: setup must not pin logger levels.

Previously ``async_setup_entry`` called ``setLevel(logging.DEBUG)`` on the
integration loggers when the ``debug_logging`` option was enabled. That pinned
``custom_components.abode_security`` and ``…abode`` (and therefore the noisy
``…abode.client`` / ``…abode.socketio`` children) to DEBUG, which made HA's
``logger.set_level`` service ineffective and survived restarts. Log verbosity
must be controlled entirely by Home Assistant — setup must never touch a
logger's level.
"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.alarm_control_panel import DOMAIN as ALARM_DOMAIN
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.abode_security import DOMAIN
from custom_components.abode_security.const import CONF_DEBUG_LOGGING, CONF_POLLING

# The loggers the old code used to pin to DEBUG.
_PINNED_LOGGER_NAMES = (
    "custom_components.abode_security",
    "custom_components.abode_security.abode",
)


async def test_setup_does_not_override_logger_level(
    hass: HomeAssistant, mock_abode: object
) -> None:
    """Enabling debug_logging must not call setLevel on any pinned logger.

    Spying on ``setLevel`` (rather than only checking the final level) enforces
    the full invariant: setup must never *touch* a pinned logger's level, even
    transiently. A check of just the end state would still pass if setup set
    DEBUG and later reset to NOTSET.
    """
    del mock_abode  # Fixture patches the Abode client; not used directly.

    # Baseline: force the loggers back to NOTSET so the end-state assertion is
    # meaningful regardless of state left by other tests.
    for name in _PINNED_LOGGER_NAMES:
        logging.getLogger(name).setLevel(logging.NOTSET)

    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "user@email.com",
            CONF_PASSWORD: "password",
            CONF_POLLING: False,
        },
        options={CONF_DEBUG_LOGGING: True},
    )
    mock_entry.add_to_hass(hass)

    mock_sio = MagicMock()
    mock_sio.SocketIO.return_value.stop = AsyncMock()

    # Record every logger name setLevel is called on during setup, delegating
    # to the real implementation so HA's own logging keeps working.
    real_set_level = logging.Logger.setLevel
    set_level_calls: list[str] = []

    def _spy_set_level(self: logging.Logger, level: int | str) -> None:
        set_level_calls.append(self.name)
        real_set_level(self, level)

    with (
        patch("custom_components.abode_security.PLATFORMS", [ALARM_DOMAIN]),
        patch("custom_components.abode_security.abode.event_controller.sio", mock_sio),
        patch.object(logging.Logger, "setLevel", _spy_set_level),
    ):
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

    # Setup must never have called setLevel on a pinned logger...
    pinned_calls = sorted(
        {name for name in set_level_calls if name in _PINNED_LOGGER_NAMES}
    )
    assert not pinned_calls, (
        f"setup called setLevel on {pinned_calls}; the integration must leave "
        "logger levels entirely to Home Assistant"
    )

    # ...so they stay at NOTSET and HA's logger config / logger.set_level
    # service remains fully in control.
    for name in _PINNED_LOGGER_NAMES:
        assert logging.getLogger(name).level == logging.NOTSET
