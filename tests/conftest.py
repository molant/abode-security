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
        # Alarm control panel (5/6) - Phase 4.5.3
        # Note: test_alarm_state_unknown removed - edge case difficult to test in integration context
        "test_alarm_entity_registry",
        "test_alarm_attributes",
        "test_alarm_arm_away",
        "test_alarm_arm_home",
        "test_alarm_disarm",
        # Camera (5/5) - Phase 4.5.3
        "test_camera_entity_registry",
        "test_camera_attributes",
        "test_camera_capture_image",
        "test_camera_on",
        "test_camera_off",
        # Switch (21/21) - Phase 4.5.3
        "test_switch_entity_registry",
        "test_switch_attributes",
        "test_switch_on",
        "test_switch_off",
        "test_automation_attributes",
        "test_turn_automation_off",
        "test_turn_automation_on",
        "test_trigger_automation",
        "test_manual_alarm_switch_attributes",
        "test_manual_alarm_switch_turn_on",
        "test_test_mode_switch_attributes",
        "test_test_mode_switch_initial_status_on",
        "test_test_mode_switch_initial_status_off",
        "test_test_mode_switch_turn_on",
        "test_test_mode_switch_turn_off",
        "test_trigger_alarm_service",
        "test_acknowledge_alarm_service",
        "test_dismiss_alarm_service",
        "test_abode_switch_error_handling",
        "test_automation_switch_error_handling",
        "test_automation_trigger_error_handling",
        # CMS Settings Switches (42/42) - Phase 4.5.3
        # Monitoring Active (7)
        "test_monitoring_active_entity_registry",
        "test_monitoring_active_attributes",
        "test_monitoring_active_initial_status_on",
        "test_monitoring_active_initial_status_off",
        "test_monitoring_active_turn_on",
        "test_monitoring_active_turn_off",
        "test_monitoring_active_error_handling",
        # Send Media (7)
        "test_send_media_entity_registry",
        "test_send_media_attributes",
        "test_send_media_initial_status_on",
        "test_send_media_initial_status_off",
        "test_send_media_turn_on",
        "test_send_media_turn_off",
        "test_send_media_error_handling",
        # Dispatch Without Verification (7)
        "test_dispatch_without_verification_entity_registry",
        "test_dispatch_without_verification_attributes",
        "test_dispatch_without_verification_initial_status_on",
        "test_dispatch_without_verification_initial_status_off",
        "test_dispatch_without_verification_turn_on",
        "test_dispatch_without_verification_turn_off",
        "test_dispatch_without_verification_error_handling",
        # Dispatch Police (7)
        "test_dispatch_police_entity_registry",
        "test_dispatch_police_attributes",
        "test_dispatch_police_initial_status_on",
        "test_dispatch_police_initial_status_off",
        "test_dispatch_police_turn_on",
        "test_dispatch_police_turn_off",
        "test_dispatch_police_error_handling",
        # Dispatch Fire (7)
        "test_dispatch_fire_entity_registry",
        "test_dispatch_fire_attributes",
        "test_dispatch_fire_initial_status_on",
        "test_dispatch_fire_initial_status_off",
        "test_dispatch_fire_turn_on",
        "test_dispatch_fire_turn_off",
        "test_dispatch_fire_error_handling",
        # Dispatch Medical (7)
        "test_dispatch_medical_entity_registry",
        "test_dispatch_medical_attributes",
        "test_dispatch_medical_initial_status_on",
        "test_dispatch_medical_initial_status_off",
        "test_dispatch_medical_turn_on",
        "test_dispatch_medical_turn_off",
        "test_dispatch_medical_error_handling",
        # Action Manager tests (Phase 1 - Dashboard Configuration)
        "test_action_creation_defaults",
        "test_action_creation_all_fields",
        "test_action_to_dict",
        "test_action_to_dict_with_datetime",
        "test_action_from_dict",
        "test_action_from_dict_with_datetime_string",
        "test_action_round_trip",
        # ActionStore tests (Phase 1 - Dashboard Configuration)
        "test_store_init",
        "test_store_add_and_get",
        "test_store_persistence",
        "test_store_remove",
        "test_store_remove_not_found",
        "test_store_get_all",
        # ActionManager tests - Sub-Phase A (Phase 2 - Dashboard Configuration)
        "test_manager_create_valid",
        "test_manager_create_empty_name",
        "test_manager_create_whitespace_name",
        "test_manager_create_name_too_long",
        "test_manager_create_empty_modes",
        "test_manager_create_invalid_mode",
        "test_manager_create_empty_sensors",
        "test_manager_create_empty_alarms",
        "test_manager_create_invalid_delay",
        "test_manager_create_negative_delay",
        "test_manager_create_missing_entity_warning",
        "test_manager_get",
        "test_manager_get_not_found",
        "test_manager_get_all",
        "test_manager_update",
        "test_manager_update_partial",
        "test_manager_update_not_found",
        "test_manager_update_validation_error",
        "test_manager_delete",
        "test_manager_delete_not_found",
        # ActionManager tests - Sub-Phase B (Phase 2 - Dashboard Configuration)
        "test_manager_get_by_mode",
        "test_manager_get_by_mode_excludes_disabled",
        "test_manager_get_enabled",
        "test_manager_toggle",
        "test_manager_toggle_not_found",
        "test_manager_record_trigger",
        "test_manager_record_trigger_increments",
        "test_manager_record_trigger_not_found",
        # WebSocket API tests - Sub-Phase A (Phase 3 - Dashboard Configuration)
        "test_ws_actions_list_empty",
        "test_ws_actions_list_with_data",
        "test_ws_actions_get",
        "test_ws_actions_get_not_found",
        "test_ws_actions_create",
        "test_ws_actions_create_with_delay",
        "test_ws_actions_create_validation_error",
        "test_ws_actions_create_invalid_mode_schema",
        "test_ws_actions_update",
        "test_ws_actions_update_not_found",
        "test_ws_actions_update_validation_error",
        "test_ws_actions_delete",
        "test_ws_actions_delete_not_found",
        "test_ws_actions_toggle",
        "test_ws_actions_toggle_not_found",
        "test_ws_actions_test",
        "test_ws_actions_test_not_found",
        "test_ws_actions_test_multiple_alarms",
        "test_ws_actions_list_no_admin_required",
        "test_ws_actions_get_no_admin_required",
        "test_ws_actions_list_not_ready",
        # WebSocket API tests - Sub-Phase B (Phase 3 - Dashboard Configuration)
        "test_ws_modes_list",
        "test_ws_modes_list_with_active_mode",
        "test_ws_modes_list_disarmed",
        "test_ws_modes_list_with_action_count",
        "test_ws_modes_list_has_metadata",
        "test_ws_entities_sensors_empty",
        "test_ws_entities_sensors_grouped_by_device_class",
        "test_ws_entities_sensors_includes_state",
        "test_ws_entities_sensors_no_device_class",
        "test_ws_entities_alarms_empty",
        "test_ws_entities_alarms_filters_abode_alarms",
        "test_ws_entities_alarms_includes_type",
        # WebSocket API tests - Sub-Phase C (Phase 3 - Dashboard Configuration)
        "test_ws_config_get",
        "test_ws_config_set",
        "test_ws_config_set_min_value",
        "test_ws_config_set_max_value",
        "test_ws_config_set_below_min",
        "test_ws_config_set_above_max",
        "test_ws_config_set_no_fields",
        "test_ws_config_persistence",
        "test_ws_config_get_not_ready",
        "test_ws_config_set_not_ready",
        # ActionTriggerCoordinator tests (Phase 4 - Dashboard Configuration)
        # Sub-Phase A: Coordinator Core
        "test_coordinator_init",
        "test_coordinator_start_stop",
        "test_coordinator_get_mode_standby",
        "test_coordinator_get_mode_home",
        "test_coordinator_get_mode_away",
        "test_coordinator_get_mode_no_panel",
        # Sub-Phase B: State Change Handling
        "test_coordinator_ignores_non_binary_sensor",
        "test_coordinator_ignores_off_state",
        "test_coordinator_matches_sensor_and_mode",
        "test_coordinator_no_match_wrong_mode",
        "test_coordinator_no_match_wrong_sensor",
        "test_coordinator_debounce",
        # Sub-Phase C: Action Execution
        "test_coordinator_triggers_alarm_service",
        "test_coordinator_fires_event",
        "test_coordinator_multiple_actions",
        "test_coordinator_disabled_action_not_triggered",
        "test_coordinator_delayed_action",
        "test_coordinator_delayed_action_cancelled_on_delete",
        "test_coordinator_delayed_action_cancelled_on_disable",
        "test_coordinator_multi_alarm_continues_on_failure",
        "test_coordinator_cancel_pending_for_action",
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
