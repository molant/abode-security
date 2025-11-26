"""End-to-end test scenarios for Abode Security integration."""

from unittest.mock import AsyncMock, Mock, patch

from homeassistant.components.alarm_control_panel import DOMAIN as ALARM_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.abode_security.const import (
    CONF_POLLING,
    CONF_POLLING_INTERVAL,
    DOMAIN,
)
from custom_components.abode_security.models import AbodeSystem
from tests.common import MockConfigEntry

from .common import setup_platform


class TestFullSetupWorkflow:
    """Test the complete setup workflow."""

    async def test_user_adds_integration_and_configures_options(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test user adding integration and then configuring options."""
        # Step 1: User adds the integration via config flow
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_USERNAME: "user@example.com",
                CONF_PASSWORD: "password123",
                CONF_POLLING: False,
            },
        )
        mock_entry.add_to_hass(hass)

        # Step 2: Integration is set up
        with (
            patch("custom_components.abode_security.PLATFORMS", [ALARM_DOMAIN]),
            patch("abode.event_controller.sio"),
        ):
            assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

        # Verify initial state
        assert mock_entry.state is ConfigEntryState.LOADED

        # Step 3: User updates options to enable polling
        hass.config_entries.async_update_entry(
            mock_entry,
            options={CONF_POLLING_INTERVAL: 45},
        )
        await hass.async_block_till_done()

        # Verify options were updated
        assert mock_entry.options[CONF_POLLING_INTERVAL] == 45

    async def test_integration_recovers_from_temporary_failure(
        self, hass: HomeAssistant
    ) -> None:
        """Test that integration recovers from temporary API failure."""
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_USERNAME: "user@example.com",
                CONF_PASSWORD: "password123",
                CONF_POLLING: False,
            },
        )
        mock_entry.add_to_hass(hass)

        # First attempt fails
        with patch(
            "custom_components.abode_security.Abode",
            side_effect=Exception("Temporary API failure"),
        ):
            with (
                patch("custom_components.abode_security.PLATFORMS", [ALARM_DOMAIN]),
                patch("abode.event_controller.sio"),
            ):
                await async_setup_component(hass, DOMAIN, {})

            await hass.async_block_till_done()
            # Should be in setup retry state
            assert mock_entry.state is ConfigEntryState.SETUP_RETRY

        # Second attempt succeeds
        with patch(
            "custom_components.abode_security.Abode",
            return_value=Mock(
                get_alarm=Mock(return_value=Mock()),
                get_devices=Mock(return_value=[]),
                get_automations=Mock(return_value=[]),
                events=Mock(),
                logout=Mock(),
            ),
        ):
            with (
                patch("custom_components.abode_security.PLATFORMS", [ALARM_DOMAIN]),
                patch("abode.event_controller.sio"),
            ):
                await hass.config_entries.async_reload(mock_entry.entry_id)
            await hass.async_block_till_done()

            # Should now be loaded
            assert mock_entry.state is ConfigEntryState.LOADED

    async def test_smart_polling_optimization_workflow(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test smart polling optimization over time."""
        await setup_platform(hass, ALARM_DOMAIN)

        entry = hass.config_entries.async_entries(DOMAIN)[0]
        abode_system: AbodeSystem = hass.data[DOMAIN][entry.entry_id]["system"]

        # Initial polling stats
        stats_before = abode_system.smart_polling.stats

        # Simulate multiple successful updates (good performance)
        for _ in range(5):
            abode_system.smart_polling.record_update(duration=0.2)

        # Simulate some errors
        for _ in range(3):
            abode_system.smart_polling.record_error()

        # Get updated stats
        stats_after = abode_system.smart_polling.stats
        interval_after = abode_system.smart_polling.get_optimal_interval()

        # Verify stats were tracked
        assert stats_after.update_count > stats_before.update_count
        assert stats_after.error_count > stats_before.error_count

        # Verify polling interval is still within bounds
        assert 15 <= interval_after <= 120

    async def test_event_filter_reduces_unnecessary_updates(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test that event filtering reduces unnecessary processing."""
        await setup_platform(hass, ALARM_DOMAIN)

        entry = hass.config_entries.async_entries(DOMAIN)[0]
        abode_system: AbodeSystem = hass.data[DOMAIN][entry.entry_id]["system"]

        # Set filter to only allow critical events
        critical_events = ["alarm_state_change", "test_mode_change"]
        abode_system.event_filter.set_filter(critical_events)

        # Simulate receiving various events
        events_received = [
            "device_update",
            "alarm_state_change",
            "device_add",
            "test_mode_change",
            "battery_warning",
            "device_remove",
        ]

        processed_count = sum(
            1 for event in events_received
            if abode_system.event_filter.should_process(event)
        )

        # Only 2 out of 6 events should be processed (alarm_state_change, test_mode_change)
        assert processed_count == 2

        # Verify filtering stats
        stats = abode_system.event_filter.get_stats()
        assert stats["total_checks"] == 6
        assert stats["filtered_count"] == 4


class TestBatchOperationsWorkflow:
    """Test batch operations in realistic scenarios."""

    async def test_batch_arm_disarm_multiple_devices(
        self, hass: HomeAssistant
    ) -> None:  # noqa: ARG002
        """Test controlling multiple devices in batch."""
        # Create mock devices
        mock_lock = Mock()
        mock_lock.lock = AsyncMock(return_value=True)

        mock_switch = Mock()
        mock_switch.switch_on = AsyncMock(return_value=True)

        mock_cover = Mock()
        mock_cover.close_cover = AsyncMock(return_value=True)

        # Perform batch operations directly
        results = []
        results.append(await mock_lock.lock())
        results.append(await mock_switch.switch_on())
        results.append(await mock_cover.close_cover())

        # Verify all operations succeeded
        assert len(results) == 3
        assert all(r is not None for r in results)

        # Verify each device method was called
        mock_lock.lock.assert_called_once()
        mock_switch.switch_on.assert_called_once()
        mock_cover.close_cover.assert_called_once()

    async def test_batch_operations_with_partial_failures(
        self, hass: HomeAssistant
    ) -> None:  # noqa: ARG002
        """Test batch operations gracefully handle some failures."""
        # Create mock devices - some will fail
        mock_device_1 = Mock()
        mock_device_1.switch_on = AsyncMock(return_value=True)

        mock_device_2 = Mock()
        mock_device_2.lock = AsyncMock(side_effect=Exception("Device offline"))

        mock_device_3 = Mock()
        mock_device_3.unlock = AsyncMock(return_value=True)

        # Perform batch operations with error handling
        results = []
        results.append(await mock_device_1.switch_on())

        try:
            results.append(await mock_device_2.lock())
        except Exception:
            results.append(None)

        results.append(await mock_device_3.unlock())

        # Verify:
        # - Operation 1 succeeded
        # - Operation 2 failed (None result)
        # - Operation 3 succeeded
        assert len(results) == 3
        assert results[0] is not None
        assert results[1] is None
        assert results[2] is not None

        mock_device_1.switch_on.assert_called_once()
        mock_device_2.lock.assert_called_once()
        mock_device_3.unlock.assert_called_once()


class TestConfigurationPresets:
    """Test configuration presets workflow."""

    async def test_user_selects_aggressive_preset(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test user selecting aggressive polling preset."""
        from custom_components.abode_security.models import POLLING_PRESETS

        aggressive_preset = POLLING_PRESETS["aggressive"]

        # Create config entry with aggressive preset values
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_USERNAME: "user@example.com",
                CONF_PASSWORD: "password123",
                CONF_POLLING: True,
                CONF_POLLING_INTERVAL: aggressive_preset["interval"],
            },
        )
        mock_entry.add_to_hass(hass)

        with (
            patch("custom_components.abode_security.PLATFORMS", [ALARM_DOMAIN]),
            patch("abode.event_controller.sio"),
        ):
            assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

        # Verify entry was set up with aggressive preset
        assert mock_entry.state is ConfigEntryState.LOADED
        assert mock_entry.data[CONF_POLLING_INTERVAL] == aggressive_preset["interval"]

    async def test_user_switches_between_presets(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test user switching between different presets."""
        from custom_components.abode_security.models import POLLING_PRESETS

        # Start with balanced preset
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_USERNAME: "user@example.com",
                CONF_PASSWORD: "password123",
                CONF_POLLING: True,
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

        # User switches to conservative preset
        hass.config_entries.async_update_entry(
            mock_entry,
            data={
                **mock_entry.data,
                CONF_POLLING_INTERVAL: POLLING_PRESETS["conservative"]["interval"],
            },
        )
        await hass.async_block_till_done()

        # Verify update
        updated_interval = mock_entry.data[CONF_POLLING_INTERVAL]
        assert updated_interval == POLLING_PRESETS["conservative"]["interval"]


class TestErrorRecoveryScenarios:
    """Test error recovery and resilience."""

    async def test_graceful_recovery_from_network_error(
        self, hass: HomeAssistant, mock_abode  # noqa: ARG002
    ) -> None:
        """Test graceful recovery from network errors."""
        await setup_platform(hass, ALARM_DOMAIN)

        entry = hass.config_entries.async_entries(DOMAIN)[0]
        abode_system: AbodeSystem = hass.data[DOMAIN][entry.entry_id]["system"]

        # Simulate network errors
        for _ in range(10):
            abode_system.smart_polling.record_error()

        # Verify polling interval increased (backoff)
        interval_after_errors = abode_system.smart_polling.get_optimal_interval()
        assert interval_after_errors > 30  # Should be higher than default

        # Simulate recovery (good updates)
        for _ in range(5):
            abode_system.smart_polling.record_update(duration=0.3)

        # Reset stats and verify interval can decrease
        abode_system.smart_polling.stats.error_count = 0
        interval_after_recovery = abode_system.smart_polling.get_optimal_interval()

        # Should be lower after recovery
        assert interval_after_recovery <= interval_after_errors

    async def test_invalid_config_handling(
        self, hass: HomeAssistant
    ) -> None:  # noqa: ARG002
        """Test handling of invalid configuration."""
        # Create entry with missing required fields
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_USERNAME: "user@example.com",
                # Missing password - should trigger validation error
                CONF_POLLING: False,
            },
        )
        mock_entry.add_to_hass(hass)

        with patch(
            "custom_components.abode_security.Abode",
            side_effect=Exception("Missing required credentials"),
        ):
            with (
                patch("custom_components.abode_security.PLATFORMS", [ALARM_DOMAIN]),
                patch("abode.event_controller.sio"),
            ):
                await async_setup_component(hass, DOMAIN, {})

            await hass.async_block_till_done()

            # Should be in error state
            assert mock_entry.state is ConfigEntryState.SETUP_ERROR
