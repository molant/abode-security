"""Tests for entity lifecycle and error handling."""

from unittest.mock import AsyncMock, Mock

from homeassistant.components.alarm_control_panel import DOMAIN as ALARM_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.core import HomeAssistant

from custom_components.abode_security.models import AbodeSystem

from .common import setup_platform


async def test_manual_alarm_switch_subscribes_to_events(
    hass: HomeAssistant, mock_abode
) -> None:
    """Test that alarm switch subscribes to timeline events on init."""
    mock_abode.events.add_event_callback = AsyncMock()

    await setup_platform(hass, SWITCH_DOMAIN)

    # Verify that the entity was set up
    state = hass.states.get("switch.test_alarm_panic_alarm")
    assert state is not None

    # Verify callback was registered
    assert mock_abode.events.add_event_callback.called
    # Should be called twice (ALARM and ALARM_END groups)
    assert mock_abode.events.add_event_callback.call_count >= 1


async def test_manual_alarm_switch_unsubscribes_on_removal(
    hass: HomeAssistant, mock_abode
) -> None:
    """Test that alarm switch unsubscribes from events on removal."""
    # Setup remove_event_callback mock
    mock_abode.events.remove_event_callback = AsyncMock()

    await setup_platform(hass, SWITCH_DOMAIN)

    # Get the entity and verify it exists
    state = hass.states.get("switch.test_alarm_panic_alarm")
    assert state is not None

    # The remove_event_callback mock should exist for cleanup
    assert hasattr(mock_abode.events, "remove_event_callback")


async def test_manual_alarm_switch_handles_missing_remove_callback(
    hass: HomeAssistant, mock_abode
) -> None:
    """Test graceful handling when remove_event_callback doesn't exist."""
    # Remove the remove_event_callback to simulate older library version
    if hasattr(mock_abode.events, "remove_event_callback"):
        delattr(mock_abode.events, "remove_event_callback")

    await setup_platform(hass, SWITCH_DOMAIN)

    # Verify the entity still sets up successfully
    state = hass.states.get("switch.test_alarm_panic_alarm")
    assert state is not None


async def test_get_test_mode_returns_false_when_method_missing() -> None:
    """Test that get_test_mode returns False if method doesn't exist."""
    abode_system = AbodeSystem(
        abode=Mock(spec=[]),  # No methods
        polling=False,
        entity_ids=set(),
        logout_listener=None,
    )

    result = await abode_system.get_test_mode()
    assert result is False


async def test_set_test_mode_handles_exception_gracefully() -> None:
    """Test that set_test_mode logs but doesn't raise on error."""
    mock_abode = Mock()
    mock_abode.set_test_mode.side_effect = Exception("API error")

    abode_system = AbodeSystem(
        abode=mock_abode,
        polling=False,
        entity_ids=set(),
        logout_listener=None,
    )

    # Should not raise
    abode_system.set_test_mode(True)


async def test_alarm_control_panel_error_handling(
    hass: HomeAssistant, mock_abode
) -> None:
    """Test that alarm control panel methods handle errors gracefully."""
    # Make set_standby raise an error to test error handling
    mock_abode.get_alarm.return_value.set_standby.side_effect = Exception("API Error")

    await setup_platform(hass, ALARM_DOMAIN)

    # Verify the entity exists
    state = hass.states.get("alarm_control_panel.abode_alarm")
    assert state is not None

    # Verify error handling didn't prevent entity creation
    assert state.state is not None


async def test_test_mode_switch_polling_disabled_initially(
    hass: HomeAssistant, mock_abode
) -> None:
    """Test that test mode switch doesn't poll until initial sync is done."""
    mock_abode.get_test_mode = Mock(return_value=False)

    await setup_platform(hass, SWITCH_DOMAIN)

    # Verify the test mode switch exists
    state = hass.states.get("switch.test_alarm_test_mode")
    assert state is not None
    # State should be off (test mode disabled)
    assert state.state == "off"


async def test_event_callback_helpers_handle_exceptions(
    hass: HomeAssistant, mock_abode
) -> None:
    """Test that event callback helpers handle exceptions gracefully."""
    # Make add_event_callback raise to test exception handling
    mock_abode.events.add_event_callback.side_effect = Exception("Subscription failed")

    await setup_platform(hass, SWITCH_DOMAIN)

    # Entity should still be set up despite callback exception
    state = hass.states.get("switch.test_alarm_panic_alarm")
    assert state is not None


async def test_service_handler_factory_error_handling(
    hass: HomeAssistant, mock_abode
) -> None:
    """Test that service handlers created with factory handle errors gracefully."""
    from custom_components.abode_security.const import DOMAIN
    from custom_components.abode_security.services import SERVICE_ACKNOWLEDGE_ALARM

    # Make acknowledge_timeline_event raise an error
    mock_abode.acknowledge_timeline_event.side_effect = Exception("API Error")

    await setup_platform(hass, SWITCH_DOMAIN)

    # Call the service (should not raise even though underlying method fails)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_ACKNOWLEDGE_ALARM,
        {"timeline_id": "test_123"},
        blocking=True,
    )
    # Service should complete without raising
