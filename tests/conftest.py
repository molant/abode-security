"""Configuration for Abode Security tests."""

import json
import sys
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from abode.helpers import urls as url  # noqa: N812
from aioresponses import aioresponses

from tests.common import load_fixture
from tests.components.light.conftest import mock_light_profiles  # noqa: F401

# Ensure vendored abode library is importable during tests
_VENDOR_PATH = Path(__file__).resolve().parents[1] / "custom_components" / "lib"
if (vendor_path_str := str(_VENDOR_PATH)) not in sys.path:
    sys.path.insert(0, vendor_path_str)

URL = url


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "custom_components.abode_security.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_abode() -> Generator[Mock]:
    """Provide a mock Abode client."""
    mock_client = Mock()
    mock_client.get_alarm = AsyncMock(return_value=Mock())
    mock_client.get_devices = AsyncMock(return_value=[])
    mock_client.get_automations = AsyncMock(return_value=[])
    mock_client.get_test_mode = AsyncMock(return_value=False)

    # CMS settings methods
    cms_settings = {
        "monitoringActive": True,
        "testModeActive": False,
        "sendMedia": True,
        "dispatchWithoutVerification": False,
        "dispatchPolice": True,
        "dispatchFire": True,
        "dispatchMedical": True,
    }
    mock_client.get_cms_settings = AsyncMock(return_value=cms_settings)
    mock_client.set_cms_setting = AsyncMock(return_value=cms_settings)
    mock_client.set_test_mode = AsyncMock(return_value=cms_settings)

    mock_client.events = Mock()
    mock_client.events.add_event_callback = AsyncMock()
    mock_client.events.remove_event_callback = AsyncMock()
    mock_client.logout = AsyncMock()
    mock_client.event_controller = Mock()
    mock_client.event_controller.stop = Mock()

    with patch("custom_components.abode_security.Abode", return_value=mock_client):
        yield mock_client


@pytest.fixture
def aiohttp_mock():
    """Fixture to provide aiohttp mocking."""
    with aioresponses() as m:
        # Mocks the login response for jaraco.abode.
        m.post(f"{URL.BASE}{URL.LOGIN}", payload=json.loads(load_fixture("login.json", "abode")))
        # Mocks the logout response for jaraco.abode.
        m.post(f"{URL.BASE}{URL.LOGOUT}", payload=json.loads(load_fixture("logout.json", "abode")))
        # Mocks the oauth claims response for jaraco.abode.
        m.get(f"{URL.BASE}{URL.OAUTH_TOKEN}", payload=json.loads(load_fixture("oauth_claims.json", "abode")))
        # Mocks the panel response for jaraco.abode.
        m.get(f"{URL.BASE}{URL.PANEL}", payload=json.loads(load_fixture("panel.json", "abode")))
        # Mocks the automations response for jaraco.abode.
        m.get(f"{URL.BASE}{URL.AUTOMATION}", payload=json.loads(load_fixture("automation.json", "abode")))
        # Mocks the devices response for jaraco.abode.
        m.get(f"{URL.BASE}{URL.DEVICES}", payload=json.loads(load_fixture("devices.json", "abode")))
        # Mocks the security panel response for CMS settings.
        m.get(f"{URL.BASE}{URL.SECURITY_PANEL}", payload=json.loads(load_fixture("panel.json", "abode")))
        # Mocks the CMS settings endpoint.
        cms_settings_response = {
            "monitoringActive": True,
            "testModeActive": False,
            "sendMedia": True,
            "dispatchWithoutVerification": False,
            "dispatchPolice": True,
            "dispatchFire": True,
            "dispatchMedical": True,
        }
        m.post(f"{URL.BASE}{URL.CMS_SETTINGS}", payload=cms_settings_response)
        yield m
