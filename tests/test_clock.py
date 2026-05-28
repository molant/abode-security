"""Tests for scheduling/clock.py."""

from __future__ import annotations

import zoneinfo
from datetime import UTC, datetime

import pytest

from custom_components.abode_security.scheduling.clock import HAClock


@pytest.fixture
def clock(hass):
    return HAClock(hass)


async def test_haclock_now_returns_aware_datetime_in_ha_timezone(hass, clock):
    """now() returns a tz-aware datetime in HA's configured time zone."""
    result = clock.now()
    assert isinstance(result, datetime)
    assert result.tzinfo is not None
    expected_tz = zoneinfo.ZoneInfo(hass.config.time_zone)
    # Compare via utcoffset to be DST-safe
    assert result.utcoffset() == result.replace(tzinfo=expected_tz).utcoffset()


async def test_haclock_utcnow_returns_aware_utc_datetime(clock):
    """utcnow() returns a tz-aware datetime in UTC."""
    result = clock.utcnow()
    assert isinstance(result, datetime)
    assert result.tzinfo is not None
    offset = result.utcoffset()
    assert offset is not None
    assert offset.total_seconds() == 0


async def test_haclock_now_and_utcnow_are_within_one_second(clock):
    """now() and utcnow() represent the same instant (within 1 s)."""
    t_now = clock.now()
    t_utcnow = clock.utcnow()
    t_now_utc = t_now.astimezone(UTC)
    t_utcnow_utc = t_utcnow.astimezone(UTC)
    delta = abs((t_now_utc - t_utcnow_utc).total_seconds())
    assert delta < 1.0
