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
    # The alarm Mock needs concrete (JSON-serializable) values for every
    # attribute touched during entity setup, otherwise the entity_registry's
    # serialization step fails on Mock objects (TypeError "Type is not JSON
    # serializable: Mock") and tears down the entire test.
    # - `id`/`name`/`type` flow into `device_info` and the device-slug part of
    #   `entity_id` (tests in test_entity_lifecycle.py expect `test_alarm_*`).
    # - `uuid` is `_attr_unique_id` for AbodeDevice.
    # - `battery`/`battery_low`/`is_cellular`/`is_standby`/`is_away`/`is_home`/
    #   `no_response` are accessed by `_sync_attrs` on AbodeAlarm/AbodeDevice.
    mock_alarm = Mock()
    mock_alarm.id = "test_alarm_id"
    mock_alarm.uuid = "test_alarm_uuid"
    mock_alarm.name = "Test Alarm"
    mock_alarm.type = "alarm"
    mock_alarm.battery = "ok"
    mock_alarm.battery_low = False
    mock_alarm.is_cellular = False
    mock_alarm.is_standby = True
    mock_alarm.is_away = False
    mock_alarm.is_home = False
    mock_alarm.no_response = False
    mock_alarm.trigger_manual_alarm = AsyncMock(return_value=None)
    mock_alarm.set_standby = AsyncMock(return_value=None)
    mock_alarm.set_home = AsyncMock(return_value=None)
    mock_alarm.set_away = AsyncMock(return_value=None)
    # `get_alarm` is sync in production (client.py:758) — use Mock, not AsyncMock.
    mock_client.get_alarm = Mock(return_value=mock_alarm)
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


# --- Integration test socket gating -----------------------------------------
#
# pytest-HA-cc's `pytest_runtest_setup` hook (plugins.py:199) unconditionally
# calls both `pytest_socket.socket_allow_hosts(["127.0.0.1"])` and
# `pytest_socket.disable_socket(allow_unix_socket=True)`, which defeats per-test
# `@pytest.mark.enable_socket` decorators and any function-scope autouse fixture
# that requests `socket_enabled` -- session-scope fixtures (e.g. `mock_server`)
# run before function-scope autouse fixtures, so the latter is too late.
#
# Fix: monkey-patch both calls so they're no-ops while an integration test is
# running, and restore `socket.socket.connect` to its real implementation so
# the host-allowlist guard installed by a previous unit test doesn't bleed
# into the integration test. A `tryfirst=True` `pytest_runtest_setup` hook
# flips the flag before HA-cc's same-name hook runs.
#
# This deviates from the original spec ("just request the `socket_enabled`
# fixture") because that approach didn't account for either the session-scope
# `mock_server` fixture or the IPv6 (::1) host gate, both of which trip the
# fixture-order workaround.
import socket as _socket  # noqa: E402

import pytest_socket as _pytest_socket  # noqa: E402

# Module-level mutable state. Safe under pytest's default sequential test
# execution and under `pytest-xdist` (which uses worker *processes*, so each
# worker has its own module state). If thread-based parallelism is ever
# adopted, replace with a `threading.local` or a contextvar.
_in_integration_test = False
_original_disable_socket = _pytest_socket.disable_socket
_original_socket_allow_hosts = _pytest_socket.socket_allow_hosts
# Captured before any guard is installed so we can restore on entry to an
# integration test even if a prior unit test left a host-allowlist guard
# active on `socket.socket.connect`.
_real_socket_connect = _pytest_socket._true_connect


def _conditional_disable_socket(*args, **kwargs):  # type: ignore[no-untyped-def]
    """Skip disabling sockets while an integration test is running."""
    if _in_integration_test:
        return None
    return _original_disable_socket(*args, **kwargs)


def _conditional_socket_allow_hosts(*args, **kwargs):  # type: ignore[no-untyped-def]
    """Skip installing the host-allowlist guard for integration tests."""
    if _in_integration_test:
        # Make sure no prior unit test's connect guard remains active.
        _socket.socket.connect = _real_socket_connect  # type: ignore[method-assign]
        return None
    return _original_socket_allow_hosts(*args, **kwargs)


_pytest_socket.disable_socket = _conditional_disable_socket
_pytest_socket.socket_allow_hosts = _conditional_socket_allow_hosts


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    """Toggle the integration-test flag *before* pytest-HA-cc's setup hook."""
    global _in_integration_test
    _in_integration_test = item.get_closest_marker("integration") is not None
    if _in_integration_test:
        # Lazy import so unit-test runs that never touch pytest-HA-cc's
        # plugin internals stay unaffected.
        from pytest_homeassistant_custom_component.plugins import (
            HASocketBlockedError,
        )

        # `.clear()` rather than `= []` to keep pyright happy about the
        # `list[Self]` annotation on the class attribute.
        HASocketBlockedError.instances.clear()
        # Restore a real `socket.socket` in case an earlier unit test's
        # `disable_socket` call replaced it with `GuardedSocket`.
        _socket.socket = _pytest_socket._true_socket  # type: ignore[assignment]


@pytest.fixture(autouse=True)
def _integration_socket_cleanup(
    request: pytest.FixtureRequest,
) -> Generator[None, None, None]:
    """Clear `HASocketBlockedError.instances` on integration-test teardown.

    The setup-time clear is in `pytest_runtest_setup` above; this fixture
    re-clears after the test body in case an async-teardown socket attempt
    populated the list and would otherwise trip the cleanup assertion at
    `pytest_homeassistant_custom_component/plugins.py:468`.
    """
    yield
    if request.node.get_closest_marker("integration") is None:
        return
    from pytest_homeassistant_custom_component.plugins import (
        HASocketBlockedError,
    )

    HASocketBlockedError.instances.clear()


@pytest.fixture
def expected_lingering_tasks(request: pytest.FixtureRequest) -> bool:
    """Permit lingering tasks for `@pytest.mark.integration` tests.

    The Abode SocketIO connect callback schedules a refresh via
    `asyncio.run_coroutine_threadsafe`; with the mock server's WebSocket
    handshake rejected (Engine.IO version mismatch), that future never
    resolves before the test finishes its assertion phase. Letting
    pytest-HA-cc's `verify_cleanup` (`plugins.py:411-423`) downgrade the
    lingering-task fail to a warning is the framework's blessed escape
    hatch (see the docstring on the upstream fixture default).
    """
    return request.node.get_closest_marker("integration") is not None
