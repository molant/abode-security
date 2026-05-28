"""Tests for scheduling/retry.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.abode_security.const import SCHEDULE_RETRY_TOTAL_ATTEMPTS
from custom_components.abode_security.scheduling.retry import (
    RetryExhausted,
    async_retry,
)


class TestAsyncRetry:
    async def test_success_on_first_attempt_no_sleeps(self) -> None:
        factory = AsyncMock(return_value=42)
        with patch(
            "custom_components.abode_security.scheduling.retry.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:
            result = await async_retry(factory, delays=(0, 0, 0))
        assert result == 42
        factory.assert_called_once()
        mock_sleep.assert_not_called()

    async def test_success_on_attempt_2_sleeps_once(self) -> None:
        factory = AsyncMock(side_effect=[RuntimeError("fail"), 99])
        with patch(
            "custom_components.abode_security.scheduling.retry.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:
            result = await async_retry(factory, delays=(0, 0, 0))
        assert result == 99
        assert factory.call_count == 2
        assert mock_sleep.call_count == 1

    async def test_success_on_attempt_4_sleeps_three_times(self) -> None:
        factory = AsyncMock(
            side_effect=[RuntimeError("1"), RuntimeError("2"), RuntimeError("3"), "ok"]
        )
        with patch(
            "custom_components.abode_security.scheduling.retry.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:
            result = await async_retry(factory, delays=(0, 0, 0))
        assert result == "ok"
        assert factory.call_count == 4
        assert mock_sleep.call_count == 3

    async def test_exhaustion_raises_retry_exhausted(self) -> None:
        factory = AsyncMock(side_effect=RuntimeError("boom"))
        with (
            patch(
                "custom_components.abode_security.scheduling.retry.asyncio.sleep",
                new_callable=AsyncMock,
            ),
            pytest.raises(RetryExhausted) as exc_info,
        ):
            await async_retry(factory, delays=(0, 0, 0))
        assert exc_info.value.attempts == SCHEDULE_RETRY_TOTAL_ATTEMPTS
        assert factory.call_count == SCHEDULE_RETRY_TOTAL_ATTEMPTS

    async def test_non_caught_exception_propagates_immediately(self) -> None:
        factory = AsyncMock(side_effect=ValueError("not caught"))
        with (
            patch(
                "custom_components.abode_security.scheduling.retry.asyncio.sleep",
                new_callable=AsyncMock,
            ) as mock_sleep,
            pytest.raises(ValueError, match="not caught"),
        ):
            await async_retry(factory, delays=(0, 0, 0), catch=RuntimeError)
        factory.assert_called_once()
        mock_sleep.assert_not_called()

    async def test_default_delays_produce_correct_total_attempts(self) -> None:
        factory = AsyncMock(side_effect=RuntimeError("always fails"))
        with (
            patch(
                "custom_components.abode_security.scheduling.retry.asyncio.sleep",
                new_callable=AsyncMock,
            ),
            pytest.raises(RetryExhausted) as exc_info,
        ):
            await async_retry(factory)
        assert exc_info.value.attempts == SCHEDULE_RETRY_TOTAL_ATTEMPTS
        assert factory.call_count == SCHEDULE_RETRY_TOTAL_ATTEMPTS

    async def test_retry_exhausted_carries_last_error(self) -> None:
        final_err = RuntimeError("final")
        factory = AsyncMock(
            side_effect=[RuntimeError("first"), RuntimeError("second"), final_err]
        )
        with (
            patch(
                "custom_components.abode_security.scheduling.retry.asyncio.sleep",
                new_callable=AsyncMock,
            ),
            pytest.raises(RetryExhausted) as exc_info,
        ):
            await async_retry(factory, delays=(0, 0))
        assert exc_info.value.last_error is final_err
