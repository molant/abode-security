"""Tests for the Abode Security switch device."""

from unittest.mock import AsyncMock, patch

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.abode_security.services import (
    SERVICE_ACKNOWLEDGE_ALARM,
    SERVICE_DISMISS_ALARM,
    SERVICE_TRIGGER_ALARM,
    SERVICE_TRIGGER_AUTOMATION,
)

from .common import setup_platform
from .test_constants import (
    AUTOMATION_ENTITY_ID,
    AUTOMATION_UID,
    DEVICE_ENTITY_ID,
    DEVICE_UID,
    DOMAIN,
    PANIC_ALARM_ENTITY_ID,
    TEST_MODE_ENTITY_ID,
)

# Use new constants from test_constants
AUTOMATION_ID = AUTOMATION_ENTITY_ID
DEVICE_ID = DEVICE_ENTITY_ID
PANIC_ALARM_ID = PANIC_ALARM_ENTITY_ID
TEST_MODE_ID = TEST_MODE_ENTITY_ID


async def test_entity_registry(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """Tests that the devices are registered in the entity registry."""
    await setup_platform(hass, SWITCH_DOMAIN)

    entry = entity_registry.async_get(AUTOMATION_ID)
    assert entry.unique_id == AUTOMATION_UID

    entry = entity_registry.async_get(DEVICE_ID)
    assert entry.unique_id == DEVICE_UID


async def test_attributes(hass: HomeAssistant) -> None:
    """Test the switch attributes are correct."""
    await setup_platform(hass, SWITCH_DOMAIN)

    state = hass.states.get(DEVICE_ID)
    assert state.state == STATE_OFF


async def test_switch_on(hass: HomeAssistant) -> None:
    """Test the switch can be turned on."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch("abode.devices.switch.Switch.switch_on", new_callable=AsyncMock) as mock_switch_on:
        await hass.services.async_call(
            SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: DEVICE_ID}, blocking=True
        )
        await hass.async_block_till_done()

        mock_switch_on.assert_called_once()


async def test_switch_off(hass: HomeAssistant) -> None:
    """Test the switch can be turned off."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch("abode.devices.switch.Switch.switch_off", new_callable=AsyncMock) as mock_switch_off:
        await hass.services.async_call(
            SWITCH_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: DEVICE_ID}, blocking=True
        )
        await hass.async_block_till_done()

        mock_switch_off.assert_called_once()


async def test_automation_attributes(hass: HomeAssistant) -> None:
    """Test the automation attributes are correct."""
    await setup_platform(hass, SWITCH_DOMAIN)

    state = hass.states.get(AUTOMATION_ID)
    # State is set based on "enabled" key in automation JSON.
    assert state.state == STATE_ON


async def test_turn_automation_off(hass: HomeAssistant) -> None:
    """Test the automation can be turned off."""
    with patch("abode.automation.Automation.enable", new_callable=AsyncMock) as mock_trigger:
        await setup_platform(hass, SWITCH_DOMAIN)

        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: AUTOMATION_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        mock_trigger.assert_called_once_with(False)


async def test_turn_automation_on(hass: HomeAssistant) -> None:
    """Test the automation can be turned on."""
    with patch("abode.automation.Automation.enable", new_callable=AsyncMock) as mock_trigger:
        await setup_platform(hass, SWITCH_DOMAIN)

        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: AUTOMATION_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        mock_trigger.assert_called_once_with(True)


async def test_trigger_automation(hass: HomeAssistant) -> None:
    """Test the trigger automation service."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch("abode.automation.Automation.trigger", new_callable=AsyncMock) as mock:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_TRIGGER_AUTOMATION,
            {ATTR_ENTITY_ID: AUTOMATION_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        mock.assert_called_once()


async def test_manual_alarm_switch_attributes(hass: HomeAssistant) -> None:
    """Test the manual alarm switch attributes are correct."""
    await setup_platform(hass, SWITCH_DOMAIN)

    state = hass.states.get(PANIC_ALARM_ID)
    assert state is not None
    assert state.state == STATE_OFF


async def test_manual_alarm_switch_turn_on(hass: HomeAssistant) -> None:
    """Test the manual alarm switch can be turned on."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch("abode.devices.alarm.Alarm.trigger_manual_alarm", new_callable=AsyncMock) as mock:
        mock.return_value = {"event_id": "test_event_123"}
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: PANIC_ALARM_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        mock.assert_called_once_with("PANIC")


async def test_test_mode_switch_attributes(hass: HomeAssistant) -> None:
    """Test the test mode switch attributes are correct."""
    await setup_platform(hass, SWITCH_DOMAIN)

    state = hass.states.get(TEST_MODE_ID)
    assert state is not None


async def test_test_mode_switch_initial_status_on(hass: HomeAssistant) -> None:
    """Test that test mode switch pulls initial status when test mode is enabled."""
    with patch("abode.Abode.get_test_mode") as mock_get:
        mock_get.return_value = True
        await setup_platform(hass, SWITCH_DOMAIN)
        await hass.async_block_till_done()

        state = hass.states.get(TEST_MODE_ID)
        assert state is not None
        assert state.state == STATE_ON


async def test_test_mode_switch_initial_status_off(hass: HomeAssistant) -> None:
    """Test that test mode switch pulls initial status when test mode is disabled."""
    with patch("abode.Abode.get_test_mode") as mock_get:
        mock_get.return_value = False
        await setup_platform(hass, SWITCH_DOMAIN)
        await hass.async_block_till_done()

        state = hass.states.get(TEST_MODE_ID)
        assert state is not None
        assert state.state == STATE_OFF


async def test_test_mode_switch_turn_on(hass: HomeAssistant) -> None:
    """Test the test mode switch can be turned on."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch("abode.Abode.set_test_mode", new_callable=AsyncMock) as mock:
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: TEST_MODE_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        mock.assert_called_once_with(True)


async def test_test_mode_switch_turn_off(hass: HomeAssistant) -> None:
    """Test the test mode switch can be turned off."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch("abode.Abode.set_test_mode", new_callable=AsyncMock) as mock:
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: TEST_MODE_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        mock.assert_called_once_with(False)


async def test_trigger_alarm_service(hass: HomeAssistant) -> None:
    """Test the trigger alarm service."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch("abode.devices.alarm.Alarm.trigger_manual_alarm", new_callable=AsyncMock) as mock:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_TRIGGER_ALARM,
            {"alarm_type": "PANIC"},
            blocking=True,
        )
        await hass.async_block_till_done()

        mock.assert_called_once_with("PANIC")


async def test_acknowledge_alarm_service(hass: HomeAssistant) -> None:
    """Test the acknowledge alarm service."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch("abode.Abode.acknowledge_timeline_event") as mock:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_ACKNOWLEDGE_ALARM,
            {"timeline_id": "12345"},
            blocking=True,
        )
        await hass.async_block_till_done()

        mock.assert_called_once_with("12345")


async def test_dismiss_alarm_service(hass: HomeAssistant) -> None:
    """Test the dismiss alarm service."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch("abode.Abode.dismiss_timeline_event") as mock:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_DISMISS_ALARM,
            {"timeline_id": "12345"},
            blocking=True,
        )
        await hass.async_block_till_done()

        mock.assert_called_once_with("12345")


async def test_abode_switch_error_handling(hass: HomeAssistant) -> None:
    """Test that AbodeSwitch handles errors gracefully."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch("abode.devices.switch.Switch.switch_on") as mock_switch_on:
        mock_switch_on.side_effect = Exception("API Error")
        await hass.services.async_call(
            SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: DEVICE_ID}, blocking=True
        )
        await hass.async_block_till_done()

        # Entity should still exist despite error
        state = hass.states.get(DEVICE_ID)
        assert state is not None


async def test_automation_switch_error_handling(hass: HomeAssistant) -> None:
    """Test that AbodeAutomationSwitch turn_on handles errors gracefully."""
    with patch("abode.automation.Automation.enable") as mock_enable:
        mock_enable.side_effect = Exception("API Error")
        await setup_platform(hass, SWITCH_DOMAIN)

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


async def test_automation_trigger_error_handling(hass: HomeAssistant) -> None:
    """Test that automation trigger handles errors gracefully."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch("abode.automation.Automation.trigger") as mock_trigger:
        mock_trigger.side_effect = Exception("API Error")
        await hass.services.async_call(
            DOMAIN,
            SERVICE_TRIGGER_AUTOMATION,
            {ATTR_ENTITY_ID: AUTOMATION_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        # Service call should complete without raising
        # (error handling in decorator will catch and log)
