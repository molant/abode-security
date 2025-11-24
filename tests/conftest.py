"""Configuration for Abode Security tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, Mock, patch

import pytest
from abode.helpers import urls as url  # noqa: N812
from requests_mock import Mocker

from tests.common import load_fixture
from tests.components.light.conftest import mock_light_profiles  # noqa: F401

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
    mock_client.get_alarm = Mock(return_value=Mock())
    mock_client.get_devices = Mock(return_value=[])
    mock_client.get_automations = Mock(return_value=[])
    mock_client.get_test_mode = Mock(return_value=False)
    mock_client.events = Mock()
    mock_client.events.add_event_callback = AsyncMock()
    mock_client.events.remove_event_callback = AsyncMock()
    mock_client.logout = Mock()
    mock_client.event_controller = Mock()
    mock_client.event_controller.stop = Mock()

    with patch("custom_components.abode_security.Abode", return_value=mock_client):
        yield mock_client


@pytest.fixture(autouse=True)
def requests_mock_fixture(requests_mock: Mocker) -> None:
    """Fixture to provide a requests mocker."""
    # Mocks the login response for jaraco.abode.
    requests_mock.post(URL.LOGIN, text=load_fixture("login.json", "abode"))
    # Mocks the logout response for jaraco.abode.
    requests_mock.post(URL.LOGOUT, text=load_fixture("logout.json", "abode"))
    # Mocks the oauth claims response for jaraco.abode.
    requests_mock.get(URL.OAUTH_TOKEN, text=load_fixture("oauth_claims.json", "abode"))
    # Mocks the panel response for jaraco.abode.
    requests_mock.get(URL.PANEL, text=load_fixture("panel.json", "abode"))
    # Mocks the automations response for jaraco.abode.
    requests_mock.get(URL.AUTOMATION, text=load_fixture("automation.json", "abode"))
    # Mocks the devices response for jaraco.abode.
    requests_mock.get(URL.DEVICES, text=load_fixture("devices.json", "abode"))
