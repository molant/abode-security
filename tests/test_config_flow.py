"""Tests for the Abode Security config flow."""

from http import HTTPStatus
from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from requests.exceptions import ConnectTimeout

from custom_components.abode_security.abode.exceptions import (
    AuthenticationException as AbodeAuthenticationException,
)
from custom_components.abode_security.abode.helpers.errors import MFA_CODE_REQUIRED
from custom_components.abode_security.const import CONF_POLLING, DOMAIN
from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_one_config_allowed(hass: HomeAssistant) -> None:
    """Test that only one Abode Security configuration is allowed.

    The framework must abort before any login attempt — otherwise the
    hass.data[DOMAIN][...] writes in async_setup_entry would clobber the
    existing entry's ActionManager / ConfigStore / coordinator (issue #5).
    """
    MockConfigEntry(
        domain=DOMAIN,
        data={CONF_USERNAME: "user@email.com", CONF_PASSWORD: "password"},
    ).add_to_hass(hass)

    with patch("custom_components.abode_security.abode.client.Client") as mock_client:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
    # No login should be attempted — manifest's single_config_entry contract.
    mock_client.assert_not_called()


async def test_user_flow(hass: HomeAssistant) -> None:
    """Test user flow, with various errors."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    # Test that invalid credentials throws an error.
    with patch(
        "custom_components.abode_security.abode.client.Client",
        side_effect=AbodeAuthenticationException(
            (HTTPStatus.BAD_REQUEST, "auth error")
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "user@email.com", CONF_PASSWORD: "password"},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_auth"}

    # Test other than invalid credentials throws an error.
    with patch(
        "custom_components.abode_security.abode.client.Client",
        side_effect=AbodeAuthenticationException(
            (HTTPStatus.INTERNAL_SERVER_ERROR, "connection error")
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "user@email.com", CONF_PASSWORD: "password"},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}

    # Test login throws an error if connection times out.
    with patch(
        "custom_components.abode_security.abode.client.Client",
        side_effect=ConnectTimeout,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "user@email.com", CONF_PASSWORD: "password"},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}

    # Test success
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch("custom_components.abode_security.abode.client.Client"):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "user@email.com", CONF_PASSWORD: "password"},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "user@email.com"
    assert result["data"] == {
        CONF_USERNAME: "user@email.com",
        CONF_PASSWORD: "password",
        CONF_POLLING: False,
    }


async def test_step_mfa(hass: HomeAssistant) -> None:
    """Test that the MFA step works."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "custom_components.abode_security.abode.client.Client",
        side_effect=AbodeAuthenticationException(MFA_CODE_REQUIRED),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "user@email.com", CONF_PASSWORD: "password"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "mfa"

    with patch(
        "custom_components.abode_security.abode.client.Client",
        side_effect=AbodeAuthenticationException(
            (HTTPStatus.BAD_REQUEST, "invalid mfa")
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"mfa_code": "123456"}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "mfa"
    assert result["errors"] == {"base": "invalid_mfa_code"}

    with patch("custom_components.abode_security.abode.client.Client"):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"mfa_code": "123456"}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "user@email.com"
    assert result["data"] == {
        CONF_USERNAME: "user@email.com",
        CONF_PASSWORD: "password",
        CONF_POLLING: False,
    }


async def test_step_reauth(hass: HomeAssistant) -> None:
    """Test the reauth flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="user@email.com",
        data={CONF_USERNAME: "user@email.com", CONF_PASSWORD: "password"},
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with (
        patch("custom_components.abode_security.abode.client.Client"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "user@email.com",
                CONF_PASSWORD: "new_password",
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"

    assert len(hass.config_entries.async_entries()) == 1
    assert entry.data[CONF_PASSWORD] == "new_password"


async def test_step_reauth_username_change_aborts(hass: HomeAssistant) -> None:
    """Reauth with a different username must abort, not create a duplicate entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="alice@example.com",
        data={CONF_USERNAME: "alice@example.com", CONF_PASSWORD: "password"},
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with patch("custom_components.abode_security.abode.client.Client"):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "bob@example.com",
                CONF_PASSWORD: "new_password",
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_wrong_account"

    # Original entry untouched, no duplicate created.
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].unique_id == "alice@example.com"
    assert entries[0].data[CONF_USERNAME] == "alice@example.com"
    assert entries[0].data[CONF_PASSWORD] == "password"


async def test_step_reauth_preserves_polling(hass: HomeAssistant) -> None:
    """Reauth must merge into existing data so CONF_POLLING is not dropped."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="user@email.com",
        data={
            CONF_USERNAME: "user@email.com",
            CONF_PASSWORD: "password",
            CONF_POLLING: True,
        },
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)

    with patch("custom_components.abode_security.abode.client.Client"):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "user@email.com",
                CONF_PASSWORD: "new_password",
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] == "new_password"
    # CONF_POLLING must survive reauth — the bug overwrote entry.data wholesale.
    assert entry.data[CONF_POLLING] is True
