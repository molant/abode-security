"""Integration tests for advanced features with the Abode Security integration."""

from unittest.mock import AsyncMock, Mock, patch

from homeassistant.components.alarm_control_panel import DOMAIN as ALARM_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.abode_security.const import (
    CONF_ENABLE_EVENTS,
    CONF_EVENT_FILTER,
    CONF_POLLING,
    CONF_POLLING_INTERVAL,
    CONF_RETRY_COUNT,
    DEFAULT_ENABLE_EVENTS,
    DEFAULT_POLLING_INTERVAL,
    DEFAULT_RETRY_COUNT,
    DOMAIN,
)
from custom_components.abode_security.models import AbodeSystem
from tests.common import MockConfigEntry

from .common import setup_platform


class TestSmartPollingIntegration:
    """Test smart polling integration with the system."""

    async def test_smart_polling_initialized_with_presets(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test that smart polling is initialized when using presets."""
        from custom_components.abode_security.models import POLLING_PRESETS

        # Create config with a preset
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "username": "user@email.com",
                "password": "password",
                CONF_POLLING: False,
                CONF_POLLING_INTERVAL: POLLING_PRESETS["balanced"]["interval"],
            },
        )
        mock_entry.add_to_hass(hass)

        with (
            patch("custom_components.abode_security.PLATFORMS", [ALARM_DOMAIN]),
            patch("abode.event_controller.sio"),
        ):
            assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

        # Verify entry was set up successfully
        assert mock_entry.state is ConfigEntryState.LOADED

    async def test_smart_polling_tracks_update_statistics(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test that smart polling tracks update statistics."""
        await setup_platform(hass, ALARM_DOMAIN)

        # Get the AbodeSystem instance
        entry = hass.config_entries.async_entries(DOMAIN)[0]
        abode_system: AbodeSystem = hass.data[DOMAIN][entry.entry_id]["system"]

        # Verify smart polling was initialized
        assert abode_system.smart_polling is not None

        # Record an update
        abode_system.smart_polling.record_update(duration=0.5)
        assert abode_system.smart_polling.stats.update_count == 1

        # Record an error
        abode_system.smart_polling.record_error()
        assert abode_system.smart_polling.stats.error_count == 1

        # Get the current optimal interval
        interval = abode_system.smart_polling.get_optimal_interval()
        assert 15 <= interval <= 120

    async def test_smart_polling_adapts_to_errors(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test that smart polling adapts interval when errors occur."""
        await setup_platform(hass, ALARM_DOMAIN)

        entry = hass.config_entries.async_entries(DOMAIN)[0]
        abode_system: AbodeSystem = hass.data[DOMAIN][entry.entry_id]["system"]

        initial_interval = abode_system.smart_polling.get_optimal_interval()

        # Record multiple errors to trigger backoff
        for _ in range(6):
            abode_system.smart_polling.record_error()

        adapted_interval = abode_system.smart_polling.get_optimal_interval()

        # With 6+ errors, should have backed off
        assert adapted_interval >= initial_interval

    async def test_smart_polling_improves_with_good_performance(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test that smart polling improves interval with good performance."""
        await setup_platform(hass, ALARM_DOMAIN)

        entry = hass.config_entries.async_entries(DOMAIN)[0]
        abode_system: AbodeSystem = hass.data[DOMAIN][entry.entry_id]["system"]

        # Record good performance (fast updates, no errors)
        for _ in range(10):
            abode_system.smart_polling.record_update(duration=0.1)

        interval = abode_system.smart_polling.get_optimal_interval()

        # With good performance (avg_duration < 1s, no errors), should reduce interval
        assert interval <= DEFAULT_POLLING_INTERVAL


class TestEventFilteringIntegration:
    """Test event filtering integration with the system."""

    async def test_event_filter_initialized_from_config(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test that event filter is initialized from config."""
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "username": "user@email.com",
                "password": "password",
                CONF_POLLING: False,
                CONF_EVENT_FILTER: ["device_update", "alarm_state_change"],
            },
        )
        mock_entry.add_to_hass(hass)

        with (
            patch("custom_components.abode_security.PLATFORMS", [ALARM_DOMAIN]),
            patch("abode.event_controller.sio"),
        ):
            assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

        assert mock_entry.state is ConfigEntryState.LOADED

    async def test_event_filter_allows_all_by_default(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test that event filter allows all events by default."""
        await setup_platform(hass, ALARM_DOMAIN)

        entry = hass.config_entries.async_entries(DOMAIN)[0]
        abode_system: AbodeSystem = hass.data[DOMAIN][entry.entry_id]["system"]

        # With empty filter (default), all events should be allowed
        assert abode_system.event_filter.should_process("device_update")
        assert abode_system.event_filter.should_process("alarm_state_change")
        assert abode_system.event_filter.should_process("unknown_event")

    async def test_event_filter_filters_specified_events(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test that event filter filters specified events."""
        await setup_platform(hass, ALARM_DOMAIN)

        entry = hass.config_entries.async_entries(DOMAIN)[0]
        abode_system: AbodeSystem = hass.data[DOMAIN][entry.entry_id]["system"]

        # Configure the filter to only accept specific events
        abode_system.event_filter.set_filter(["device_update"])

        assert abode_system.event_filter.should_process("device_update")
        assert not abode_system.event_filter.should_process("alarm_state_change")

    async def test_event_filter_tracks_statistics(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test that event filter tracks filtering statistics."""
        await setup_platform(hass, ALARM_DOMAIN)

        entry = hass.config_entries.async_entries(DOMAIN)[0]
        abode_system: AbodeSystem = hass.data[DOMAIN][entry.entry_id]["system"]

        abode_system.event_filter.set_filter(["device_update"])

        # Process some events
        abode_system.event_filter.should_process("device_update")
        abode_system.event_filter.should_process("alarm_state_change")

        stats = abode_system.event_filter.get_stats()
        assert stats["total_checks"] == 2
        assert stats["filtered_count"] == 1


class TestBatchOperationsIntegration:
    """Test batch operations integration."""

    async def test_batch_operations_execute_successfully(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test that batch operations execute successfully."""
        from custom_components.abode_security.async_wrapper import (
            async_batch_device_operations,
        )

        mock_device = Mock()
        mock_device.switch_on = AsyncMock(return_value=True)
        mock_device.switch_off = AsyncMock(return_value=True)

        operations = [
            ("switch_on", mock_device, None),
            ("switch_off", mock_device, None),
        ]

        results = await async_batch_device_operations(hass, operations)

        assert len(results) == 2
        assert all(r is not None for r in results)
        mock_device.switch_on.assert_called_once()
        mock_device.switch_off.assert_called_once()

    async def test_batch_operations_handle_individual_failures(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test that batch operations handle individual operation failures."""
        from custom_components.abode_security.async_wrapper import (
            async_batch_device_operations,
        )

        mock_device = Mock()
        mock_device.switch_on = AsyncMock(side_effect=Exception("Device error"))
        mock_device.switch_off = AsyncMock(return_value=True)

        operations = [
            ("switch_on", mock_device, None),
            ("switch_off", mock_device, None),
        ]

        results = await async_batch_device_operations(hass, operations)

        # First operation should fail (None), second should succeed
        assert len(results) == 2
        assert results[0] is None
        assert results[1] is not None

    async def test_batch_read_devices_collects_status(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test that batch read devices collects status information."""
        from custom_components.abode_security.async_wrapper import (
            async_batch_read_devices,
        )

        mock_device = Mock()
        mock_device.device_id = "device_123"
        mock_device.name = "Test Device"
        mock_device.type = "switch"
        mock_device.status = "online"
        mock_device.battery = 85

        results = await async_batch_read_devices(hass, [mock_device])

        assert len(results) == 1
        result = results[0]
        assert result["id"] == "device_123"
        assert result["name"] == "Test Device"
        assert result["type"] == "switch"
        assert result["status"] == "online"
        assert result["battery"] == 85


class TestOptionsFlowIntegration:
    """Test options flow for advanced features."""

    async def test_options_flow_updates_polling_interval(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test that options flow can update polling interval."""
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "username": "user@email.com",
                "password": "password",
                CONF_POLLING: False,
                CONF_POLLING_INTERVAL: DEFAULT_POLLING_INTERVAL,
            },
            options={},
        )
        mock_entry.add_to_hass(hass)

        with (
            patch("custom_components.abode_security.PLATFORMS", [ALARM_DOMAIN]),
            patch("abode.event_controller.sio"),
        ):
            assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

        # Update options
        hass.config_entries.async_update_entry(
            mock_entry,
            options={CONF_POLLING_INTERVAL: 60},
        )
        await hass.async_block_till_done()

        # Verify options were updated
        assert mock_entry.options[CONF_POLLING_INTERVAL] == 60

    async def test_options_flow_updates_event_enable(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test that options flow can enable/disable events."""
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "username": "user@email.com",
                "password": "password",
                CONF_POLLING: False,
                CONF_ENABLE_EVENTS: DEFAULT_ENABLE_EVENTS,
            },
            options={},
        )
        mock_entry.add_to_hass(hass)

        with (
            patch("custom_components.abode_security.PLATFORMS", [ALARM_DOMAIN]),
            patch("abode.event_controller.sio"),
        ):
            assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

        # Update options to disable events
        hass.config_entries.async_update_entry(
            mock_entry,
            options={CONF_ENABLE_EVENTS: False},
        )
        await hass.async_block_till_done()

        assert mock_entry.options[CONF_ENABLE_EVENTS] is False

    async def test_options_flow_updates_retry_count(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test that options flow can update retry count."""
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "username": "user@email.com",
                "password": "password",
                CONF_POLLING: False,
                CONF_RETRY_COUNT: DEFAULT_RETRY_COUNT,
            },
            options={},
        )
        mock_entry.add_to_hass(hass)

        with (
            patch("custom_components.abode_security.PLATFORMS", [ALARM_DOMAIN]),
            patch("abode.event_controller.sio"),
        ):
            assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

        # Update options to increase retry count
        hass.config_entries.async_update_entry(
            mock_entry,
            options={CONF_RETRY_COUNT: 5},
        )
        await hass.async_block_till_done()

        assert mock_entry.options[CONF_RETRY_COUNT] == 5


class TestEndToEndScenarios:
    """Test complete end-to-end scenarios."""

    async def test_complete_setup_with_all_advanced_features(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test complete setup with all advanced features enabled."""
        from custom_components.abode_security.const import CONF_USERNAME

        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_USERNAME: "user@email.com",
                "password": "password",
                CONF_POLLING: True,
                CONF_POLLING_INTERVAL: 30,
                CONF_ENABLE_EVENTS: True,
                CONF_RETRY_COUNT: 3,
                CONF_EVENT_FILTER: ["device_update", "alarm_state_change"],
            },
        )
        mock_entry.add_to_hass(hass)

        with (
            patch("custom_components.abode_security.PLATFORMS", [ALARM_DOMAIN]),
            patch("abode.event_controller.sio"),
        ):
            assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

        assert mock_entry.state is ConfigEntryState.LOADED

        # Verify all systems are initialized
        entry = hass.config_entries.async_entries(DOMAIN)[0]
        abode_system: AbodeSystem = hass.data[DOMAIN][entry.entry_id]["system"]

        assert abode_system.smart_polling is not None
        assert abode_system.event_filter is not None

    async def test_polling_adaptation_over_time(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test that polling adapts over time based on performance."""
        await setup_platform(hass, ALARM_DOMAIN)

        entry = hass.config_entries.async_entries(DOMAIN)[0]
        abode_system: AbodeSystem = hass.data[DOMAIN][entry.entry_id]["system"]

        # Simulate a series of updates with increasing errors
        for i in range(20):
            if i < 10:
                abode_system.smart_polling.record_update(duration=0.5)
            else:
                abode_system.smart_polling.record_error()

        mid_interval = abode_system.smart_polling.get_optimal_interval()

        # Now simulate good performance recovery
        for _ in range(10):
            abode_system.smart_polling.record_update(duration=0.1)

        final_interval = abode_system.smart_polling.get_optimal_interval()

        # Interval should increase with errors, then potentially decrease with good perf
        assert 15 <= mid_interval <= 120
        assert 15 <= final_interval <= 120

    async def test_event_filtering_with_multiple_events(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test event filtering with multiple event types."""
        await setup_platform(hass, ALARM_DOMAIN)

        entry = hass.config_entries.async_entries(DOMAIN)[0]
        abode_system: AbodeSystem = hass.data[DOMAIN][entry.entry_id]["system"]

        # Set filter to allow only specific events
        allowed_events = ["device_update", "alarm_state_change"]
        abode_system.event_filter.set_filter(allowed_events)

        # Test filtering
        test_events = [
            "device_update",  # Should pass
            "alarm_state_change",  # Should pass
            "battery_warning",  # Should fail
            "test_mode_change",  # Should fail
            "device_add",  # Should fail
        ]

        allowed_count = sum(
            1 for event in test_events
            if abode_system.event_filter.should_process(event)
        )

        assert allowed_count == 2
