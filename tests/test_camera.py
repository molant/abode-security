"""Tests for the Abode Security camera device."""

import os
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.camera import DOMAIN as CAMERA_DOMAIN
from homeassistant.components.camera import CameraState
from homeassistant.const import ATTR_ENTITY_ID, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.abode_security import DOMAIN
from custom_components.abode_security.const import CONF_POLLING


@pytest.mark.integration
async def test_camera_entity_registry(
    hass: HomeAssistant,
    mock_server_client: dict[str, str],
    entity_registry: er.EntityRegistry,
) -> None:
    """Tests that the devices are registered in the entity registry."""
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

        entry = entity_registry.async_get("camera.test_cam")
        assert entry is not None
        assert entry.unique_id == "d0a3a1c316891ceb00c20118aae2a133"

        # Cleanup - unload config entry
        await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_camera_attributes(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the camera attributes are correct."""
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

        state = hass.states.get("camera.test_cam")
        assert state is not None
        assert state.state == CameraState.IDLE

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_camera_capture_image(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the camera capture image service."""
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
            "custom_components.abode_security.abode.devices.camera.Camera.capture",
            new_callable=AsyncMock,
        ) as mock_capture:
            await hass.services.async_call(
                DOMAIN,
                "capture_image",
                {ATTR_ENTITY_ID: "camera.test_cam"},
                blocking=True,
            )
            await hass.async_block_till_done()
            mock_capture.assert_called_once()

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_camera_on(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the camera turn on service."""
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
            "custom_components.abode_security.abode.devices.camera.Camera.privacy_mode",
            new_callable=AsyncMock,
        ) as mock_privacy:
            await hass.services.async_call(
                CAMERA_DOMAIN,
                "turn_on",
                {ATTR_ENTITY_ID: "camera.test_cam"},
                blocking=True,
            )
            await hass.async_block_till_done()
            mock_privacy.assert_called_once_with(False)

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_camera_off(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the camera turn off service."""
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
            "custom_components.abode_security.abode.devices.camera.Camera.privacy_mode",
            new_callable=AsyncMock,
        ) as mock_privacy:
            await hass.services.async_call(
                CAMERA_DOMAIN,
                "turn_off",
                {ATTR_ENTITY_ID: "camera.test_cam"},
                blocking=True,
            )
            await hass.async_block_till_done()
            mock_privacy.assert_called_once_with(True)

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]
