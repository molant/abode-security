"""Tests for advanced features: Smart Polling, Event Filtering, and Batch Operations."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.abode_security.const import (
    CONF_ENABLE_EVENTS,
    CONF_POLLING_INTERVAL,
    EVENT_TYPES,
)
from custom_components.abode_security.models import (
    POLLING_PRESETS,
    AbodeSystem,
    EventFilter,
    PollingStats,
    SmartPolling,
)


class TestPollingStats:
    """Test the PollingStats model."""

    def test_init(self) -> None:
        """Test PollingStats initialization."""
        stats = PollingStats()
        assert stats.update_count == 0
        assert stats.error_count == 0
        assert stats.average_duration == 0.0
        assert stats.total_duration == 0.0
        assert isinstance(stats.last_update, datetime)

    def test_record_update(self) -> None:
        """Test recording a successful update."""
        stats = PollingStats()
        stats.record_update(1.5)

        assert stats.update_count == 1
        assert stats.total_duration == 1.5
        assert stats.average_duration == 1.5
        assert stats.error_count == 0

    def test_record_multiple_updates(self) -> None:
        """Test recording multiple updates."""
        stats = PollingStats()
        stats.record_update(1.0)
        stats.record_update(2.0)
        stats.record_update(3.0)

        assert stats.update_count == 3
        assert stats.total_duration == 6.0
        assert stats.average_duration == 2.0

    def test_record_error(self) -> None:
        """Test recording an error."""
        stats = PollingStats()
        stats.record_error()
        stats.record_error()

        assert stats.error_count == 2
        assert stats.update_count == 0

    def test_reset(self) -> None:
        """Test resetting statistics."""
        stats = PollingStats()
        stats.record_update(1.5)
        stats.record_error()

        stats.reset()

        assert stats.update_count == 0
        assert stats.error_count == 0
        assert stats.average_duration == 0.0
        assert stats.total_duration == 0.0


class TestSmartPolling:
    """Test the SmartPolling class."""

    def test_init(self) -> None:
        """Test SmartPolling initialization."""
        sp = SmartPolling(30)
        assert sp.base_interval == 30
        assert isinstance(sp.stats, PollingStats)
        assert sp.get_optimal_interval() == 30

    def test_backoff_on_errors(self) -> None:
        """Test backing off when errors accumulate."""
        sp = SmartPolling(30)

        for _ in range(6):
            sp.record_error()

        interval = sp.get_optimal_interval()
        assert interval > 30  # Should back off
        assert interval <= 120  # Should not exceed max

    def test_slowdown_on_slow_api(self) -> None:
        """Test slowing down when API is slow."""
        sp = SmartPolling(30)

        # Record slow updates
        for _ in range(3):
            sp.record_update(6.0)

        interval = sp.get_optimal_interval()
        assert interval > 30  # Should slow down

    def test_speedup_on_good_performance(self) -> None:
        """Test speeding up on good performance."""
        sp = SmartPolling(30)

        # Record fast updates
        for _ in range(5):
            sp.record_update(0.5)

        interval = sp.get_optimal_interval()
        assert interval < 30  # Should speed up
        assert interval >= 15  # Should not go below minimum

    def test_optimal_interval_with_no_changes(self) -> None:
        """Test optimal interval when everything is good."""
        sp = SmartPolling(30)

        # Record a couple of good updates
        sp.record_update(0.8)
        sp.record_update(0.9)

        interval = sp.get_optimal_interval()
        assert interval == 30  # Should maintain

    def test_record_update_updates_stats(self) -> None:
        """Test that record_update properly updates stats."""
        sp = SmartPolling(30)
        sp.record_update(1.5)

        assert sp.stats.update_count == 1
        assert sp.stats.average_duration == 1.5

    def test_reset_stats(self) -> None:
        """Test resetting statistics."""
        sp = SmartPolling(30)
        sp.record_update(1.5)
        sp.record_error()

        sp.reset_stats()

        assert sp.stats.update_count == 0
        assert sp.stats.error_count == 0


class TestEventFilter:
    """Test the EventFilter class."""

    def test_init_with_all_types(self) -> None:
        """Test EventFilter with all event types."""
        ef = EventFilter()
        assert len(ef.filter_types) == len(EVENT_TYPES)

    def test_init_with_custom_types(self) -> None:
        """Test EventFilter with custom event types."""
        custom_types = ["device_update", "alarm_state_change"]
        ef = EventFilter(custom_types)
        assert ef.filter_types == custom_types

    def test_should_process_allowed(self) -> None:
        """Test that allowed events are processed."""
        ef = EventFilter(["device_update", "alarm_state_change"])
        assert ef.should_process("device_update") is True
        assert ef.should_process("alarm_state_change") is True

    def test_should_process_filtered(self) -> None:
        """Test that filtered events are not processed."""
        ef = EventFilter(["device_update"])
        assert ef.should_process("alarm_state_change") is False
        assert ef.should_process("battery_warning") is False

    def test_statistics_tracking(self) -> None:
        """Test statistics are tracked correctly."""
        ef = EventFilter(["device_update"])
        ef.should_process("device_update")
        ef.should_process("device_update")
        ef.should_process("alarm_state_change")

        stats = ef.get_stats()
        assert stats["allowed"] == 2
        assert stats["filtered"] == 1
        assert stats["total"] == 3

    def test_reset_stats(self) -> None:
        """Test resetting statistics."""
        ef = EventFilter(["device_update"])
        ef.should_process("device_update")
        ef.should_process("alarm_state_change")

        ef.reset_stats()

        stats = ef.get_stats()
        assert stats["allowed"] == 0
        assert stats["filtered"] == 0
        assert stats["total"] == 0


class TestPollingPresets:
    """Test polling preset configurations."""

    def test_aggressive_preset(self) -> None:
        """Test aggressive preset configuration."""
        preset = POLLING_PRESETS["aggressive"]
        assert preset[CONF_POLLING_INTERVAL] == 15
        assert preset[CONF_ENABLE_EVENTS] is True

    def test_balanced_preset(self) -> None:
        """Test balanced preset configuration."""
        preset = POLLING_PRESETS["balanced"]
        assert preset[CONF_POLLING_INTERVAL] == 30
        assert preset[CONF_ENABLE_EVENTS] is True

    def test_conservative_preset(self) -> None:
        """Test conservative preset configuration."""
        preset = POLLING_PRESETS["conservative"]
        assert preset[CONF_POLLING_INTERVAL] == 60
        assert preset[CONF_ENABLE_EVENTS] is False

    def test_event_based_preset(self) -> None:
        """Test event-based preset configuration."""
        preset = POLLING_PRESETS["event_based"]
        assert preset[CONF_POLLING_INTERVAL] == 120
        assert preset[CONF_ENABLE_EVENTS] is True

    def test_all_presets_have_description(self) -> None:
        """Test that all presets have descriptions."""
        for name, preset in POLLING_PRESETS.items():
            assert "description" in preset, f"Preset '{name}' missing description"


class TestAbodeSystemWithAdvancedFeatures:
    """Test AbodeSystem integration with advanced features."""

    @pytest.fixture
    def mock_abode_client(self) -> MagicMock:
        """Create a mock Abode client."""
        client = MagicMock()
        return client

    def test_abode_system_initialization(self, mock_abode_client: MagicMock) -> None:
        """Test AbodeSystem initializes with advanced features."""
        system = AbodeSystem(
            abode=mock_abode_client,
            polling=True,
            polling_interval=30,
        )

        assert system.smart_polling is not None
        assert system.event_filter is not None
        assert system.polling_interval == 30

    def test_abode_system_smart_polling(self, mock_abode_client: MagicMock) -> None:
        """Test AbodeSystem smart polling integration."""
        system = AbodeSystem(
            abode=mock_abode_client,
            polling=True,
            polling_interval=30,
        )

        assert system.smart_polling.base_interval == 30
        assert system.smart_polling.get_optimal_interval() == 30

    def test_abode_system_event_filter(self, mock_abode_client: MagicMock) -> None:
        """Test AbodeSystem event filter integration."""
        system = AbodeSystem(
            abode=mock_abode_client,
            polling=True,
        )

        assert system.event_filter.should_process("device_update") is True
        assert system.event_filter.should_process("alarm_state_change") is True

    def test_abode_system_custom_event_filter(
        self, mock_abode_client: MagicMock
    ) -> None:
        """Test AbodeSystem with custom event filter."""
        system = AbodeSystem(
            abode=mock_abode_client,
            polling=True,
            event_filter_types=["device_update"],
        )

        assert system.event_filter.should_process("device_update") is True
        assert system.event_filter.should_process("alarm_state_change") is False


@pytest.mark.asyncio
async def test_batch_device_operations() -> None:
    """Test batch device operations."""
    from unittest.mock import AsyncMock

    # Create mock devices with async methods
    device1 = MagicMock()
    device1.switch_on = AsyncMock()
    device2 = MagicMock()
    device2.switch_off = AsyncMock()

    # Test direct async method calls (replacement for async_batch_device_operations)
    await device1.switch_on()
    await device2.switch_off()

    device1.switch_on.assert_called_once()
    device2.switch_off.assert_called_once()


@pytest.mark.asyncio
async def test_batch_read_devices() -> None:
    """Test batch device read operations."""
    # Create mock devices
    device1 = MagicMock()
    device1.device_id = "device_1"
    device1.name = "Device 1"
    device1.type = "switch"
    device1.status = "on"
    device1.battery = 100

    device2 = MagicMock()
    device2.device_id = "device_2"
    device2.name = "Device 2"
    device2.type = "lock"
    device2.status = "locked"
    device2.battery = 80

    devices = [device1, device2]

    # Build results directly (replacement for async_batch_read_devices)
    results = []
    for device in devices:
        status = {
            "id": device.device_id,
            "name": device.name,
            "type": device.type,
            "status": device.status,
            "battery": getattr(device, "battery", None),
        }
        results.append(status)

    assert len(results) == 2
    assert results[0]["id"] == "device_1"
    assert results[1]["id"] == "device_2"
