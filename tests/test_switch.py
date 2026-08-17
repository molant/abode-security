"""Tests for the Abode Security switch device."""

import os
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_PASSWORD,
    CONF_USERNAME,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.abode_security import DOMAIN
from custom_components.abode_security.abode.exceptions import (
    Exception as AbodeException,
)
from custom_components.abode_security.const import CONF_POLLING
from custom_components.abode_security.services import (
    SERVICE_ACKNOWLEDGE_ALARM,
    SERVICE_DISMISS_ALARM,
    SERVICE_TRIGGER_ALARM,
    SERVICE_TRIGGER_AUTOMATION,
)
from tests.test_constants import (
    AUTOMATION_ENTITY_ID,
    AUTOMATION_UID,
    DEVICE_ENTITY_ID,
    DEVICE_UID,
    PANIC_ALARM_ENTITY_ID,
    TEST_MODE_ENTITY_ID,
)

# Use constants from test_constants
AUTOMATION_ID = AUTOMATION_ENTITY_ID
DEVICE_ID = DEVICE_ENTITY_ID
PANIC_ALARM_ID = PANIC_ALARM_ENTITY_ID
TEST_MODE_ID = TEST_MODE_ENTITY_ID


@pytest.mark.integration
async def test_switch_entity_registry(
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

        # Check automation switch
        entry = entity_registry.async_get(AUTOMATION_ID)
        assert entry is not None
        assert entry.unique_id == AUTOMATION_UID

        # Check device switch
        entry = entity_registry.async_get(DEVICE_ID)
        assert entry is not None
        assert entry.unique_id == DEVICE_UID

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_switch_attributes(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the switch attributes are correct."""
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
        assert state.state == STATE_OFF

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_switch_on(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the switch can be turned on."""
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
            "custom_components.abode_security.abode.devices.switch.Switch.switch_on",
            new_callable=AsyncMock,
        ) as mock_switch_on:
            await hass.services.async_call(
                SWITCH_DOMAIN,
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
async def test_switch_off(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the switch can be turned off."""
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
            "custom_components.abode_security.abode.devices.switch.Switch.switch_off",
            new_callable=AsyncMock,
        ) as mock_switch_off:
            await hass.services.async_call(
                SWITCH_DOMAIN,
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
async def test_automation_attributes(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the automation attributes are correct."""
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

        state = hass.states.get(AUTOMATION_ID)
        assert state is not None
        # State is set based on "enabled" key in automation JSON
        assert state.state == STATE_ON

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_turn_automation_off(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the automation can be turned off."""
    import importlib

    from custom_components.abode_security.abode.helpers import urls

    original_url = os.environ.get("ABODE_BASE_URL")
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]
    importlib.reload(urls)

    try:
        with patch(
            "custom_components.abode_security.abode.automation.Automation.enable",
            new_callable=AsyncMock,
        ) as mock_enable:
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

            await hass.services.async_call(
                SWITCH_DOMAIN,
                SERVICE_TURN_OFF,
                {ATTR_ENTITY_ID: AUTOMATION_ID},
                blocking=True,
            )
            await hass.async_block_till_done()
            mock_enable.assert_called_once_with(False)

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_turn_automation_on(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the automation can be turned on."""
    import importlib

    from custom_components.abode_security.abode.helpers import urls

    original_url = os.environ.get("ABODE_BASE_URL")
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]
    importlib.reload(urls)

    try:
        with patch(
            "custom_components.abode_security.abode.automation.Automation.enable",
            new_callable=AsyncMock,
        ) as mock_enable:
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

            await hass.services.async_call(
                SWITCH_DOMAIN,
                SERVICE_TURN_ON,
                {ATTR_ENTITY_ID: AUTOMATION_ID},
                blocking=True,
            )
            await hass.async_block_till_done()
            mock_enable.assert_called_once_with(True)

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_trigger_automation(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the trigger automation service."""
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
            "custom_components.abode_security.abode.automation.Automation.trigger",
            new_callable=AsyncMock,
        ) as mock_trigger:
            await hass.services.async_call(
                DOMAIN,
                SERVICE_TRIGGER_AUTOMATION,
                {ATTR_ENTITY_ID: AUTOMATION_ID},
                blocking=True,
            )
            await hass.async_block_till_done()
            mock_trigger.assert_called_once()

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_manual_alarm_switch_attributes(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the manual alarm switch attributes are correct."""
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

        state = hass.states.get(PANIC_ALARM_ID)
        assert state is not None
        assert state.state == STATE_OFF

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_manual_alarm_switch_turn_on(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the manual alarm switch can be turned on."""
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

        # `find_alarm_event_id` is stubbed too: the switch now resolves the
        # timeline event id in a background task, and the real lookup would
        # poll the mock server for ~67s after the service call has returned.
        with (
            patch(
                "custom_components.abode_security.abode.devices.alarm.Alarm.trigger_manual_alarm",
                new_callable=AsyncMock,
            ) as mock_trigger,
            patch(
                "custom_components.abode_security.abode.devices.alarm.Alarm.find_alarm_event_id",
                new_callable=AsyncMock,
                return_value="test_event_123",
            ),
        ):
            mock_trigger.return_value = {"code": 200}
            await hass.services.async_call(
                SWITCH_DOMAIN,
                SERVICE_TURN_ON,
                {ATTR_ENTITY_ID: PANIC_ALARM_ID},
                blocking=True,
            )
            await hass.async_block_till_done()
            mock_trigger.assert_called_once_with("PANIC")

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_test_mode_switch_attributes(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the test mode switch attributes are correct."""
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

        state = hass.states.get(TEST_MODE_ID)
        assert state is not None

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_test_mode_switch_initial_status_on(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test that test mode switch pulls initial status when test mode is enabled."""
    import importlib

    from custom_components.abode_security.abode.helpers import urls

    original_url = os.environ.get("ABODE_BASE_URL")
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]
    importlib.reload(urls)

    try:
        with patch(
            "custom_components.abode_security.abode.client.Client.get_test_mode"
        ) as mock_get:
            mock_get.return_value = True
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

            state = hass.states.get(TEST_MODE_ID)
            assert state is not None
            assert state.state == STATE_ON

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_test_mode_switch_initial_status_off(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test that test mode switch pulls initial status when test mode is disabled."""
    import importlib

    from custom_components.abode_security.abode.helpers import urls

    original_url = os.environ.get("ABODE_BASE_URL")
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]
    importlib.reload(urls)

    try:
        with patch(
            "custom_components.abode_security.abode.client.Client.get_test_mode"
        ) as mock_get:
            mock_get.return_value = False
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

            state = hass.states.get(TEST_MODE_ID)
            assert state is not None
            assert state.state == STATE_OFF

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_test_mode_switch_turn_on(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the test mode switch can be turned on."""
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
            "custom_components.abode_security.abode.client.Client.set_test_mode",
            new_callable=AsyncMock,
        ) as mock_set:
            await hass.services.async_call(
                SWITCH_DOMAIN,
                SERVICE_TURN_ON,
                {ATTR_ENTITY_ID: TEST_MODE_ID},
                blocking=True,
            )
            await hass.async_block_till_done()
            mock_set.assert_called_once_with(True)

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_test_mode_switch_turn_off(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the test mode switch can be turned off."""
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
            "custom_components.abode_security.abode.client.Client.set_test_mode",
            new_callable=AsyncMock,
        ) as mock_set:
            await hass.services.async_call(
                SWITCH_DOMAIN,
                SERVICE_TURN_OFF,
                {ATTR_ENTITY_ID: TEST_MODE_ID},
                blocking=True,
            )
            await hass.async_block_till_done()
            mock_set.assert_called_once_with(False)

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_trigger_alarm_service(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the trigger alarm service."""
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
            "custom_components.abode_security.abode.devices.alarm.Alarm.trigger_manual_alarm",
            new_callable=AsyncMock,
        ) as mock_trigger:
            await hass.services.async_call(
                DOMAIN,
                SERVICE_TRIGGER_ALARM,
                {"alarm_type": "PANIC"},
                blocking=True,
            )
            await hass.async_block_till_done()
            mock_trigger.assert_called_once_with("PANIC")

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_acknowledge_alarm_service(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the acknowledge alarm service."""
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
            "custom_components.abode_security.abode.client.Client.acknowledge_timeline_event"
        ) as mock_ack:
            await hass.services.async_call(
                DOMAIN,
                SERVICE_ACKNOWLEDGE_ALARM,
                {"timeline_id": "12345"},
                blocking=True,
            )
            await hass.async_block_till_done()
            mock_ack.assert_called_once_with("12345")

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_dismiss_alarm_service(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the dismiss alarm service."""
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
            "custom_components.abode_security.abode.client.Client.dismiss_timeline_event"
        ) as mock_dismiss:
            await hass.services.async_call(
                DOMAIN,
                SERVICE_DISMISS_ALARM,
                {"timeline_id": "12345"},
                blocking=True,
            )
            await hass.async_block_till_done()
            mock_dismiss.assert_called_once_with("12345")

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_abode_switch_error_handling(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """A failed switch_on surfaces to the caller instead of looking like success.

    `handle_abode_errors` logs and re-raises as `HomeAssistantError`; it does
    not swallow. The entity must survive the failure.
    """
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
            "custom_components.abode_security.abode.devices.switch.Switch.switch_on",
            new_callable=AsyncMock,
        ) as mock_switch_on:
            mock_switch_on.side_effect = AbodeException((500, "API Error"))
            with pytest.raises(HomeAssistantError, match="turn on switch device"):
                await hass.services.async_call(
                    SWITCH_DOMAIN,
                    SERVICE_TURN_ON,
                    {ATTR_ENTITY_ID: DEVICE_ID},
                    blocking=True,
                )
            await hass.async_block_till_done()

            # Entity should still exist despite error
            state = hass.states.get(DEVICE_ID)
            assert state is not None

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_automation_switch_error_handling(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """A failed automation enable surfaces to the caller rather than being swallowed."""
    import importlib

    from custom_components.abode_security.abode.helpers import urls

    original_url = os.environ.get("ABODE_BASE_URL")
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]
    importlib.reload(urls)

    try:
        with patch(
            "custom_components.abode_security.abode.automation.Automation.enable",
            new_callable=AsyncMock,
        ) as mock_enable:
            mock_enable.side_effect = AbodeException((500, "API Error"))
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

            with pytest.raises(HomeAssistantError, match="enable automation"):
                await hass.services.async_call(
                    SWITCH_DOMAIN,
                    SERVICE_TURN_ON,
                    {ATTR_ENTITY_ID: AUTOMATION_ID},
                    blocking=True,
                )
            await hass.async_block_till_done()

            # Entity should still exist despite error
            state = hass.states.get(AUTOMATION_ID)
            assert state is not None

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_automation_trigger_error_handling(
    hass: HomeAssistant,
    mock_server_client: dict[str, str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A failed automation trigger is named in the log rather than dropped.

    Unlike the two tests above, this is not a direct entity service call:
    `_trigger_automation` fans out over `async_dispatcher_send` and
    `_trigger_wrapper` schedules the coroutine with `hass.add_job`, so the
    failure has no caller to reach. `_trigger_and_log` catches and logs it;
    without that it would escape as an unretrieved task exception and fail
    this test at teardown.
    """
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
            "custom_components.abode_security.abode.automation.Automation.trigger",
            new_callable=AsyncMock,
        ) as mock_trigger:
            mock_trigger.side_effect = AbodeException((500, "API Error"))
            await hass.services.async_call(
                DOMAIN,
                SERVICE_TRIGGER_AUTOMATION,
                {ATTR_ENTITY_ID: AUTOMATION_ID},
                blocking=True,
            )
            await hass.async_block_till_done()

            # The dispatch really did reach the entity...
            mock_trigger.assert_called_once()
            # ...the fan-out service call itself cannot report per-entity
            # failure, so it still returns cleanly...
            # ...but the failure is logged against the specific automation
            # rather than surfacing as an anonymous asyncio traceback. Only
            # `_trigger_and_log` can produce this text: the decorator's own
            # log line (decorators.py) never names the entity.
            assert f"Automation {AUTOMATION_ID} failed to trigger" in caplog.text

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]
