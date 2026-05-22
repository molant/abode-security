"""Config flow for the Abode Security System component."""

from __future__ import annotations

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any, cast

import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import selector
from requests.exceptions import (
    ConnectTimeout,
    HTTPError,
)

# Import using relative imports (proper pattern for production code)
from .abode.exceptions import (
    AuthenticationException as AbodeAuthenticationException,
)
from .abode.helpers.errors import MFA_CODE_REQUIRED
from .const import (
    CONF_DEBUG_LOGGING,
    CONF_ENABLE_EVENTS,
    CONF_POLLING,
    CONF_POLLING_INTERVAL,
    CONF_RETRY_COUNT,
    CONF_SNAPSHOT_RETENTION_DAYS,
    DEFAULT_ENABLE_EVENTS,
    DEFAULT_POLLING_INTERVAL,
    DEFAULT_RETRY_COUNT,
    DEFAULT_SNAPSHOT_RETENTION_DAYS,
    DOMAIN,
    LOGGER,
)

CONF_MFA = "mfa_code"


class AbodeFlowHandler(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Config flow for Abode."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self.data_schema = {
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        }
        self.mfa_data_schema = {
            vol.Required(CONF_MFA): str,
        }

        self._mfa_code: str | None = None
        self._password: str | None = None
        self._polling: bool = False
        self._username: str | None = None

    async def _async_abode_login(self, step_id: str) -> ConfigFlowResult:
        """Handle login with Abode."""
        # Import Client inside function so test mocks can intercept it
        from .abode.client import Client as Abode

        errors: dict[str, str] = {}
        abode = None

        try:
            abode = Abode(self._username, self._password, False, False, False)
            # Initialize and login - handle both real client and mocked client
            result = abode._async_initialize()
            if hasattr(result, "__await__"):
                await result
            result = abode.login()
            if hasattr(result, "__await__"):
                await result
            result = abode.get_devices()
            if hasattr(result, "__await__"):
                await result
            result = abode.get_automations()
            if hasattr(result, "__await__"):
                await result

        except AbodeAuthenticationException as ex:
            if ex.errcode == MFA_CODE_REQUIRED[0]:
                # finally below cleans up this client; MFA step opens a new one.
                return await self.async_step_mfa()

            LOGGER.error("Unable to connect to Abode: %s", ex)

            if ex.errcode == HTTPStatus.BAD_REQUEST:
                errors = {"base": "invalid_auth"}

            else:
                errors = {"base": "cannot_connect"}

        except (ConnectTimeout, HTTPError):
            errors = {"base": "cannot_connect"}

        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Unexpected exception during Abode login")
            errors = {"base": "unknown"}

        finally:
            # Always close the aiohttp session opened by the client (issue #6).
            # async_setup_entry creates a fresh client on entry creation.
            if abode is not None:
                result = abode.cleanup()
                if hasattr(result, "__await__"):
                    await result

        if errors:
            return self.async_show_form(
                step_id=step_id, data_schema=vol.Schema(self.data_schema), errors=errors
            )

        return await self._async_create_entry()

    async def _async_abode_mfa_login(self) -> ConfigFlowResult:
        """Handle multi-factor authentication (MFA) login with Abode."""
        # Import Client inside function so test mocks can intercept it
        from .abode.client import Client as Abode

        abode = None
        try:
            # Create instance to access login method for passing MFA code
            abode = Abode(self._username, self._password, False, False, False)
            # Handle both real client and mocked client
            result = abode._async_initialize()
            if hasattr(result, "__await__"):
                await result
            result = abode.login(self._username, self._password, self._mfa_code)
            if hasattr(result, "__await__"):
                await result

        except AbodeAuthenticationException:
            return self.async_show_form(
                step_id="mfa",
                data_schema=vol.Schema(self.mfa_data_schema),
                errors={"base": "invalid_mfa_code"},
            )

        finally:
            # Always close the aiohttp session opened by the client (issue #6).
            if abode is not None:
                result = abode.cleanup()
                if hasattr(result, "__await__"):
                    await result

        return await self._async_create_entry()

    async def _async_create_entry(self) -> ConfigFlowResult:
        """Create the config entry."""
        await self.async_set_unique_id(self._username)

        if self.source == SOURCE_REAUTH:
            # Force username stability on reauth: a different login means a
            # different account, which would orphan the existing entry.
            self._abort_if_unique_id_mismatch(reason="reauth_wrong_account")
            # Use data_updates so existing keys (e.g. CONF_POLLING) survive.
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(),
                data_updates={CONF_PASSWORD: cast(str, self._password)},
            )

        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=cast(str, self._username),
            data={
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_POLLING: self._polling,
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=vol.Schema(self.data_schema)
            )

        self._username = user_input[CONF_USERNAME]
        self._password = user_input[CONF_PASSWORD]

        return await self._async_abode_login(step_id="user")

    async def async_step_mfa(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a multi-factor authentication (MFA) flow."""
        if user_input is None:
            return self.async_show_form(
                step_id="mfa", data_schema=vol.Schema(self.mfa_data_schema)
            )

        self._mfa_code = user_input[CONF_MFA]

        return await self._async_abode_mfa_login()

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauthorization request from Abode."""
        self._username = entry_data[CONF_USERNAME]

        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauthorization flow."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_USERNAME, default=self._username): str,
                        vol.Required(CONF_PASSWORD): str,
                    }
                ),
            )

        self._username = user_input[CONF_USERNAME]
        self._password = user_input[CONF_PASSWORD]

        return await self._async_abode_login(step_id="reauth_confirm")

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,  # noqa: ARG004
    ) -> AbodeOptionsFlowHandler:
        """Get the options flow."""
        return AbodeOptionsFlowHandler()


class AbodeOptionsFlowHandler(OptionsFlow):
    """Handle Abode options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle basic options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current config values
        polling_interval = self.config_entry.options.get(
            CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
        )
        enable_events = self.config_entry.options.get(
            CONF_ENABLE_EVENTS, DEFAULT_ENABLE_EVENTS
        )
        retry_count = self.config_entry.options.get(
            CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT
        )
        snapshot_retention_days = self.config_entry.options.get(
            CONF_SNAPSHOT_RETENTION_DAYS, DEFAULT_SNAPSHOT_RETENTION_DAYS
        )
        debug_logging = self.config_entry.options.get(CONF_DEBUG_LOGGING, False)

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_POLLING_INTERVAL, default=polling_interval
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=15, max=120, mode=selector.NumberSelectorMode.BOX
                    ),
                ),
                vol.Optional(
                    CONF_ENABLE_EVENTS, default=enable_events
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_RETRY_COUNT, default=retry_count
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=5, mode=selector.NumberSelectorMode.BOX
                    ),
                ),
                vol.Optional(
                    CONF_SNAPSHOT_RETENTION_DAYS, default=snapshot_retention_days
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=365, step=1, mode=selector.NumberSelectorMode.BOX
                    ),
                ),
                vol.Optional(
                    CONF_DEBUG_LOGGING, default=debug_logging
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )
