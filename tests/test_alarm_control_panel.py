"""Tests for the Abode Security alarm control panel device."""

import os
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.alarm_control_panel import (
    DOMAIN as ALARM_DOMAIN,
)
from homeassistant.components.alarm_control_panel import AlarmControlPanelState
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    ATTR_SUPPORTED_FEATURES,
    CONF_PASSWORD,
    CONF_USERNAME,
    SERVICE_ALARM_ARM_AWAY,
    SERVICE_ALARM_ARM_HOME,
    SERVICE_ALARM_DISARM,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.abode_security import ATTR_DEVICE_ID, DOMAIN
from custom_components.abode_security.const import CONF_POLLING

from .test_constants import ALARM_ENTITY_ID, ALARM_UID

# Use constants from test_constants
DEVICE_ID = ALARM_ENTITY_ID


@pytest.mark.integration
@pytest.mark.enable_socket
async def test_alarm_entity_registry(
    hass: HomeAssistant,
    mock_server_client: dict[str, str],
    entity_registry: er.EntityRegistry,
) -> None:
    """Tests that the alarm is registered in the entity registry."""
    import importlib

    from custom_components.abode_security.abode import event_controller
    from custom_components.abode_security.abode.helpers import urls

    original_url = os.environ.get("ABODE_BASE_URL")
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]
    importlib.reload(urls)
    importlib.reload(event_controller)

    try:
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_USERNAME: mock_server_client["username"],
                CONF_PASSWORD: mock_server_client["password"],
                CONF_POLLING: False,
            },
        )
        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        entry = entity_registry.async_get(ALARM_ENTITY_ID)
        assert entry is not None
        # Abode alarm device unique_id is the MAC address
        assert entry.unique_id == ALARM_UID

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
@pytest.mark.enable_socket
async def test_alarm_attributes(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the alarm control panel attributes are correct."""
    import importlib

    from custom_components.abode_security.abode import event_controller
    from custom_components.abode_security.abode.helpers import urls

    original_url = os.environ.get("ABODE_BASE_URL")
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]
    importlib.reload(urls)
    importlib.reload(event_controller)

    try:
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_USERNAME: mock_server_client["username"],
                CONF_PASSWORD: mock_server_client["password"],
                CONF_POLLING: False,
            },
        )
        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get(ALARM_ENTITY_ID)
        assert state is not None
        assert state.state == AlarmControlPanelState.DISARMED
        assert state.attributes.get(ATTR_DEVICE_ID) == "area_1"
        assert not state.attributes.get("battery_backup")
        assert not state.attributes.get("cellular_backup")
        assert state.attributes.get(ATTR_FRIENDLY_NAME) == "Abode Alarm"
        assert state.attributes.get(ATTR_SUPPORTED_FEATURES) == 3

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
@pytest.mark.enable_socket
async def test_alarm_arm_away(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the alarm control panel can be armed to away mode."""
    import importlib

    from custom_components.abode_security.abode import event_controller
    from custom_components.abode_security.abode.helpers import urls

    original_url = os.environ.get("ABODE_BASE_URL")
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]
    importlib.reload(urls)
    importlib.reload(event_controller)

    try:
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_USERNAME: mock_server_client["username"],
                CONF_PASSWORD: mock_server_client["password"],
                CONF_POLLING: False,
            },
        )
        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        # Verify initial state
        state = hass.states.get(ALARM_ENTITY_ID)
        assert state.state == AlarmControlPanelState.DISARMED

        # Patch the device method and call service
        with patch(
            "custom_components.abode_security.abode.devices.alarm.Alarm.set_away",
            new_callable=AsyncMock,
        ) as mock_set_away:
            await hass.services.async_call(
                ALARM_DOMAIN,
                SERVICE_ALARM_ARM_AWAY,
                {ATTR_ENTITY_ID: ALARM_ENTITY_ID},
                blocking=True,
            )
            await hass.async_block_till_done()
            mock_set_away.assert_called_once()

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
@pytest.mark.enable_socket
async def test_alarm_arm_home(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the alarm control panel can be armed to home mode."""
    import importlib

    from custom_components.abode_security.abode import event_controller
    from custom_components.abode_security.abode.helpers import urls

    original_url = os.environ.get("ABODE_BASE_URL")
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]
    importlib.reload(urls)
    importlib.reload(event_controller)

    try:
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_USERNAME: mock_server_client["username"],
                CONF_PASSWORD: mock_server_client["password"],
                CONF_POLLING: False,
            },
        )
        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        # Verify initial state
        state = hass.states.get(ALARM_ENTITY_ID)
        assert state.state == AlarmControlPanelState.DISARMED

        # Patch the device method and call service
        with patch(
            "custom_components.abode_security.abode.devices.alarm.Alarm.set_home",
            new_callable=AsyncMock,
        ) as mock_set_home:
            await hass.services.async_call(
                ALARM_DOMAIN,
                SERVICE_ALARM_ARM_HOME,
                {ATTR_ENTITY_ID: ALARM_ENTITY_ID},
                blocking=True,
            )
            await hass.async_block_till_done()
            mock_set_home.assert_called_once()

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
@pytest.mark.enable_socket
async def test_alarm_disarm(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the alarm control panel can be disarmed."""
    import importlib

    from custom_components.abode_security.abode import event_controller
    from custom_components.abode_security.abode.helpers import urls

    original_url = os.environ.get("ABODE_BASE_URL")
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]
    importlib.reload(urls)
    importlib.reload(event_controller)

    try:
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_USERNAME: mock_server_client["username"],
                CONF_PASSWORD: mock_server_client["password"],
                CONF_POLLING: False,
            },
        )
        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        # Verify initial state
        state = hass.states.get(ALARM_ENTITY_ID)
        assert state.state == AlarmControlPanelState.DISARMED

        # Patch the device method and call service
        with patch(
            "custom_components.abode_security.abode.devices.alarm.Alarm.set_standby",
            new_callable=AsyncMock,
        ) as mock_set_standby:
            await hass.services.async_call(
                ALARM_DOMAIN,
                SERVICE_ALARM_DISARM,
                {ATTR_ENTITY_ID: ALARM_ENTITY_ID},
                blocking=True,
            )
            await hass.async_block_till_done()
            mock_set_standby.assert_called_once()

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]
