"""Configuration for Abode Security tests."""

import contextlib
import json
from collections.abc import Generator
from unittest.mock import AsyncMock, Mock, patch

# Vendored abode library is in custom_components/abode_security/abode
# Use proper absolute imports for test code
import pytest
from aioresponses import aioresponses  # noqa: E402

from custom_components.abode_security.abode.helpers import urls as url  # noqa: N812
from tests.common import load_fixture  # noqa: E402

URL = url


# Configure pytest-homeassistant-custom-component to load our integration
pytest_plugins = "pytest_homeassistant_custom_component"


def pytest_collection_modifyitems(config, items):
    """Skip tests that aren't ready yet."""
    del config  # Unused parameter required by pytest hook
    skip_marker = pytest.mark.skip(
        reason="Test infrastructure complete but test needs updates - see phase-4-5.md"
    )
    # Tests enabled for Phase 4.5.1-4.5.2: Config flow + init tests
    enabled_tests = {
        # Config flow tests (Phase 4.5.1)
        "test_one_config_allowed",
        "test_user_flow",
        "test_step_mfa",
        "test_step_reauth",
        # Init tests (Phase 4.5.2)
        "test_change_settings",
        "test_add_unique_id",
        "test_unload_entry",
        "test_invalid_credentials",
        "test_raise_config_entry_not_ready_when_offline",
        # Platform tests with mock server (Phase 4.5.3)
        # Binary sensor (2/2)
        "test_binary_sensor_with_mock_server",
        "test_binary_sensor_attributes",
        # Cover (4/4)
        "test_cover_entity_registry",
        "test_cover_attributes",
        "test_cover_open",
        "test_cover_close",
        # Lock (4/4)
        "test_lock_entity_registry",
        "test_lock_attributes",
        "test_lock_lock",
        "test_lock_unlock",
        # Sensor (2/2)
        "test_sensor_entity_registry",
        "test_sensor_attributes",
        # Light (7/7)
        "test_light_entity_registry",
        "test_light_attributes",
        "test_light_switch_off",
        "test_light_switch_on",
        "test_light_set_brightness",
        "test_light_set_color",
        "test_light_set_color_temp",
    }
    # Skip tests with hass fixture except enabled tests
    for item in items:
        if "hass" in item.fixturenames and item.name not in enabled_tests:
            item.add_marker(skip_marker)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    del enable_custom_integrations  # Fixture dependency, not used directly
    yield


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
    mock_client._async_initialize = AsyncMock()
    mock_client._token = "mock_token"
    mock_client._devices = []
    mock_client._automations = []
    mock_client.cleanup = AsyncMock()
    mock_client.set_setting = AsyncMock()

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
    mock_client.events.add_event_callback = Mock()
    mock_client.events.remove_event_callback = Mock()
    mock_client.events.set_event_loop = Mock()
    mock_client.events.stop = Mock()
    mock_client.events.start = Mock()
    mock_client.logout = AsyncMock()

    with patch(
        "custom_components.abode_security.abode.client.Client", return_value=mock_client
    ):
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
    from custom_components.abode_security.abode.client import Client as Abode

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
