"""Tests for the Abode Security sensor device."""

import os

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_FRIENDLY_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_PASSWORD,
    CONF_USERNAME,
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.abode_security import ATTR_DEVICE_ID
from custom_components.abode_security.const import CONF_POLLING, DOMAIN


@pytest.mark.integration
async def test_sensor_entity_registry(
    hass: HomeAssistant,
    mock_server_client: dict[str, str],
    entity_registry: er.EntityRegistry,
) -> None:
    """Tests that the sensor devices are registered in the entity registry."""
    import importlib

    from custom_components.abode_security.abode.helpers import urls

    original_url = os.environ.get("ABODE_BASE_URL")
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]
    importlib.reload(urls)

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

        entry = entity_registry.async_get("sensor.environment_sensor_humidity")
        assert entry is not None
        assert entry.unique_id == "13545b21f4bdcd33d9abd461f8443e65-humidity"

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_sensor_attributes(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the sensor attributes are correct."""
    import importlib

    from custom_components.abode_security.abode.helpers import urls

    original_url = os.environ.get("ABODE_BASE_URL")
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]
    importlib.reload(urls)

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

        state = hass.states.get("sensor.environment_sensor_humidity")
        assert state is not None
        assert state.state == "32.0"
        assert state.attributes.get(ATTR_DEVICE_ID) == "RF:02148e70"
        assert not state.attributes.get("battery_low")
        assert not state.attributes.get("no_response")
        assert state.attributes.get("device_type") == "LM"
        assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == PERCENTAGE
        assert state.attributes.get(ATTR_FRIENDLY_NAME) == "Environment Sensor Humidity"
        assert state.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.HUMIDITY

        state = hass.states.get("sensor.environment_sensor_illuminance")
        assert state is not None
        assert state.state == "1.0"
        assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "lx"

        state = hass.states.get("sensor.environment_sensor_temperature")
        assert state is not None
        # Abodepy device JSON reports 19.5, but Home Assistant shows 19.4
        assert float(state.state) == pytest.approx(19.44444)
        assert (
            state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfTemperature.CELSIUS
        )

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]
