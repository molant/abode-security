"""Tests for the Abode Security binary sensor device."""

import os

import pytest
from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
)
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
)
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    ATTR_DEVICE_CLASS,
    ATTR_FRIENDLY_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
    STATE_OFF,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.abode_security import ATTR_DEVICE_ID
from custom_components.abode_security.const import ATTRIBUTION, CONF_POLLING, DOMAIN

from .common import setup_platform


async def test_entity_registry(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """Tests that the devices are registered in the entity registry."""
    await setup_platform(hass, BINARY_SENSOR_DOMAIN)

    entry = entity_registry.async_get("binary_sensor.front_door")
    assert entry.unique_id == "2834013428b6035fba7d4054aa7b25a3"


@pytest.mark.integration
@pytest.mark.enable_socket
async def test_binary_sensor_attributes(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the binary sensor attributes are correct."""
    # Set environment variable to point to mock server
    import importlib

    from custom_components.abode_security.abode.helpers import urls

    original_url = os.environ.get("ABODE_BASE_URL")
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]

    # Reload urls module to pick up the new environment variable
    importlib.reload(urls)

    try:
        # Create config entry with mock server credentials
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_USERNAME: mock_server_client["username"],
                CONF_PASSWORD: mock_server_client["password"],
                CONF_POLLING: False,
            },
        )
        config_entry.add_to_hass(hass)

        # Set up the integration - this will make real HTTP calls to mock server
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        # Verify entity attributes
        state = hass.states.get("binary_sensor.front_door")
        assert state is not None
        assert state.state == STATE_OFF
        assert state.attributes.get(ATTR_ATTRIBUTION) == ATTRIBUTION
        assert state.attributes.get(ATTR_DEVICE_ID) == "RF:01430030"
        assert not state.attributes.get("battery_low")
        assert not state.attributes.get("no_response")
        assert state.attributes.get("device_type") == "Door Contact"
        assert state.attributes.get(ATTR_FRIENDLY_NAME) == "Front Door"
        assert state.attributes.get(ATTR_DEVICE_CLASS) == BinarySensorDeviceClass.WINDOW

    finally:
        # Restore original environment
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
@pytest.mark.enable_socket
async def test_binary_sensor_with_mock_server(
    hass: HomeAssistant,
    mock_server_client: dict[str, str],
    entity_registry: er.EntityRegistry,
) -> None:
    """Test binary sensor entity creation using mock server."""
    # Set environment variable to point to mock server
    import importlib

    from custom_components.abode_security.abode.helpers import urls

    original_url = os.environ.get("ABODE_BASE_URL")
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]

    # Reload urls module to pick up the new environment variable
    importlib.reload(urls)

    try:
        # Create config entry with mock server credentials
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_USERNAME: mock_server_client["username"],
                CONF_PASSWORD: mock_server_client["password"],
                CONF_POLLING: False,
            },
        )
        config_entry.add_to_hass(hass)

        # Set up the integration - this will make real HTTP calls to mock server
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        # Verify entity was created in registry
        entry = entity_registry.async_get("binary_sensor.front_door")
        assert entry is not None
        assert entry.unique_id == "2834013428b6035fba7d4054aa7b25a3"

        # Verify entity state and attributes
        state = hass.states.get("binary_sensor.front_door")
        assert state is not None
        assert state.state == STATE_OFF
        assert state.attributes.get(ATTR_ATTRIBUTION) == ATTRIBUTION
        assert state.attributes.get(ATTR_DEVICE_ID) == "RF:01430030"
        assert state.attributes.get("device_type") == "Door Contact"
        assert state.attributes.get(ATTR_FRIENDLY_NAME) == "Front Door"
        assert state.attributes.get(ATTR_DEVICE_CLASS) == BinarySensorDeviceClass.WINDOW

    finally:
        # Restore original environment
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]
