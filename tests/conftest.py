"""Configuration for Abode Security tests."""

import contextlib
import json
import sys
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

# Ensure custom_components directory is in sys.path for Home Assistant to find integrations
_CUSTOM_COMPONENTS_PATH = Path(__file__).resolve().parents[1] / "custom_components"
if (custom_components_path_str := str(_CUSTOM_COMPONENTS_PATH)) not in sys.path:
    sys.path.insert(0, custom_components_path_str)

# Vendored abode library is now in custom_components/abode_security/abode
# and will be imported as abode_security.abode via the sys.path setup above

import pytest  # noqa: E402
from abode_security.abode.helpers import urls as url  # noqa: E402, N812
from aioresponses import aioresponses  # noqa: E402

from tests.common import load_fixture  # noqa: E402

URL = url


def pytest_collection_modifyitems(config, items):  # noqa: E402
    """Skip tests that require full Home Assistant integration setup."""
    del config  # Unused parameter required by pytest hook
    skip_marker = pytest.mark.skip(
        reason="Requires full Home Assistant integration setup"
    )
    # Tests that use the 'hass' fixture need full HA environment
    for item in items:
        if "hass" in item.fixturenames:
            item.add_marker(skip_marker)


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
        m.post(
            f"{URL.BASE}{URL.LOGIN}",
            payload=json.loads(load_fixture("login.json", "abode")),
        )
        # Mocks the logout response for jaraco.abode.
        m.post(
            f"{URL.BASE}{URL.LOGOUT}",
            payload=json.loads(load_fixture("logout.json", "abode")),
        )
        # Mocks the oauth claims response for jaraco.abode.
        m.get(
            f"{URL.BASE}{URL.OAUTH_TOKEN}",
            payload=json.loads(load_fixture("oauth_claims.json", "abode")),
        )
        # Mocks the panel response for jaraco.abode.
        m.get(
            f"{URL.BASE}{URL.PANEL}",
            payload=json.loads(load_fixture("panel.json", "abode")),
        )
        # Mocks the automations response for jaraco.abode.
        m.get(
            f"{URL.BASE}{URL.AUTOMATION}",
            payload=json.loads(load_fixture("automation.json", "abode")),
        )
        # Mocks the devices response for jaraco.abode.
        m.get(
            f"{URL.BASE}{URL.DEVICES}",
            payload=json.loads(load_fixture("devices.json", "abode")),
        )
        # Mocks the security panel response for CMS settings.
        m.get(
            f"{URL.BASE}{URL.SECURITY_PANEL}",
            payload=json.loads(load_fixture("panel.json", "abode")),
        )
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


# Mock server fixtures for integration tests
import os  # noqa: E402
import subprocess  # noqa: E402

import requests  # noqa: E402

# Mock server configuration
MOCK_SERVER_URL = os.environ.get("MOCK_SERVER_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def mock_server_url() -> str:
    """Provide mock server URL for integration tests."""
    return MOCK_SERVER_URL


@pytest.fixture(scope="session")
def mock_server(mock_server_url: str) -> Generator[str, None, None]:
    """
    Start mock server for the test session if not already running.

    Yields the mock server URL.
    """
    # Check if mock server is already running
    try:
        response = requests.get(f"{mock_server_url}/health", timeout=2)
        if response.status_code == 200:
            # Server already running
            yield mock_server_url
            return
    except requests.RequestException:
        pass

    # Start mock server using docker-compose
    print("\n🚀 Starting mock Abode server...")
    subprocess.run(
        ["docker-compose", "up", "-d", "mock-abode"],
        check=True,
        capture_output=True,
    )

    # Wait for server to be ready
    import time

    max_wait = 30
    waited = 0
    while waited < max_wait:
        try:
            response = requests.get(f"{mock_server_url}/health", timeout=2)
            if response.status_code == 200:
                print(f"✅ Mock server ready at {mock_server_url}")
                break
        except requests.RequestException:
            pass
        time.sleep(1)
        waited += 1
    else:
        raise RuntimeError(f"Mock server failed to start after {max_wait} seconds")

    yield mock_server_url

    # Cleanup: Stop mock server
    print("\n🛑 Stopping mock Abode server...")
    subprocess.run(
        ["docker-compose", "down", "mock-abode"],
        check=False,
        capture_output=True,
    )


@pytest.fixture
def reset_mock_server(mock_server: str) -> Generator[None, None, None]:
    """
    Reset mock server state before each test.

    Ensures test isolation by resetting panel mode, devices, timeline, etc.
    Requires mock server to be running.
    """
    try:
        response = requests.post(
            f"{mock_server}/api/test/reset",
            timeout=2,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        pytest.skip(f"Mock server not available at {mock_server}. Error: {e}")

    yield

    # Cleanup after test (optional, since next test will reset anyway)
    with contextlib.suppress(requests.RequestException):
        requests.post(f"{mock_server}/api/test/reset", timeout=2)


@pytest.fixture
def mock_server_client(mock_server: str, reset_mock_server: None) -> dict[str, str]:
    """
    Provide authenticated client configuration for mock server tests.

    Returns a dict with connection info and test credentials.
    """
    del reset_mock_server  # Unused but ensures reset happens
    return {
        "base_url": mock_server,
        "username": "test@example.com",
        "password": "testpassword",
    }


@pytest.fixture
async def abode_with_mock_server(
    mock_server_client: dict[str, str],
) -> Generator[Mock, None, None]:
    """
    Create Abode client connected to mock server.

    Useful for integration tests that need a real client instance.
    """
    from abode_security.abode.client import Client as Abode

    # Set environment variable for this test
    original_url = os.environ.get("ABODE_BASE_URL")
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]

    try:
        abode = Abode(
            username=mock_server_client["username"],
            password=mock_server_client["password"],
            auto_login=True,
        )

        yield abode

        # Cleanup
        await abode.logout()
    finally:
        # Restore environment
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]
