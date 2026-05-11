"""Tests for the Abode Security light device."""

import os
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_MODE,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ATTR_SUPPORTED_COLOR_MODES,
    ColorMode,
)
from homeassistant.components.light import (
    DOMAIN as LIGHT_DOMAIN,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    ATTR_SUPPORTED_FEATURES,
    CONF_PASSWORD,
    CONF_USERNAME,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.abode_security import ATTR_DEVICE_ID
from custom_components.abode_security.const import CONF_POLLING, DOMAIN

DEVICE_ID = "light.living_room_lamp"


@pytest.mark.integration
async def test_light_entity_registry(
    hass: HomeAssistant,
    mock_server_client: dict[str, str],
    entity_registry: er.EntityRegistry,
) -> None:
    """Tests that the light devices are registered in the entity registry."""
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

        entry = entity_registry.async_get(DEVICE_ID)
        assert entry is not None
        assert entry.unique_id == "741385f4388b2637df4c6b398fe50581"

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_light_attributes(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the light attributes are correct."""
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

        state = hass.states.get(DEVICE_ID)
        assert state is not None
        assert state.state == STATE_ON
        assert state.attributes.get(ATTR_BRIGHTNESS) == 204
        assert state.attributes.get(ATTR_RGB_COLOR) == (0, 64, 255)
        assert state.attributes.get(ATTR_COLOR_TEMP_KELVIN) is None
        assert state.attributes.get(ATTR_DEVICE_ID) == "ZB:db5b1a"
        assert not state.attributes.get("battery_low")
        assert not state.attributes.get("no_response")
        assert state.attributes.get("device_type") == "RGB Dimmer"
        assert state.attributes.get(ATTR_FRIENDLY_NAME) == "Living Room Lamp"
        assert state.attributes.get(ATTR_SUPPORTED_FEATURES) == 0
        assert state.attributes.get(ATTR_COLOR_MODE) == ColorMode.HS
        assert state.attributes.get(ATTR_SUPPORTED_COLOR_MODES) == [
            ColorMode.COLOR_TEMP,
            ColorMode.HS,
        ]

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_light_switch_off(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the light can be turned off."""
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

        with patch(
            "custom_components.abode_security.abode.devices.light.Light.switch_off",
            new_callable=AsyncMock,
        ) as mock_switch_off:
            await hass.services.async_call(
                LIGHT_DOMAIN,
                SERVICE_TURN_OFF,
                {ATTR_ENTITY_ID: DEVICE_ID},
                blocking=True,
            )
            await hass.async_block_till_done()
            mock_switch_off.assert_called_once()

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_light_switch_on(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the light can be turned on."""
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

        with patch(
            "custom_components.abode_security.abode.devices.light.Light.switch_on",
            new_callable=AsyncMock,
        ) as mock_switch_on:
            await hass.services.async_call(
                LIGHT_DOMAIN,
                SERVICE_TURN_ON,
                {ATTR_ENTITY_ID: DEVICE_ID},
                blocking=True,
            )
            await hass.async_block_till_done()
            mock_switch_on.assert_called_once()

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_light_set_brightness(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the brightness can be set."""
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

        with patch(
            "custom_components.abode_security.abode.devices.light.Light.set_level",
            new_callable=AsyncMock,
        ) as mock_set_level:
            await hass.services.async_call(
                LIGHT_DOMAIN,
                SERVICE_TURN_ON,
                {ATTR_ENTITY_ID: DEVICE_ID, "brightness": 100},
                blocking=True,
            )
            await hass.async_block_till_done()
            # Brightness is converted in abode.light.AbodeLight.turn_on
            mock_set_level.assert_called_once_with(39)

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_light_set_color(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the color can be set."""
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

        with patch(
            "custom_components.abode_security.abode.devices.light.Light.set_color",
            new_callable=AsyncMock,
        ) as mock_set_color:
            await hass.services.async_call(
                LIGHT_DOMAIN,
                SERVICE_TURN_ON,
                {ATTR_ENTITY_ID: DEVICE_ID, "hs_color": [240, 100]},
                blocking=True,
            )
            await hass.async_block_till_done()
            mock_set_color.assert_called_once_with((240.0, 100.0))

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_light_set_color_temp(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the color temp can be set."""
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

        with patch(
            "custom_components.abode_security.abode.devices.light.Light.set_color_temp",
            new_callable=AsyncMock,
        ) as mock_set_color_temp:
            await hass.services.async_call(
                LIGHT_DOMAIN,
                SERVICE_TURN_ON,
                {ATTR_ENTITY_ID: DEVICE_ID, "color_temp_kelvin": 3236},
                blocking=True,
            )
            await hass.async_block_till_done()
            # HA renamed `color_temp` (mireds) -> `color_temp_kelvin` in the
            # light.turn_on service schema; the underlying Abode set_color_temp
            # still takes kelvin.
            mock_set_color_temp.assert_called_once_with(3236)

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]
