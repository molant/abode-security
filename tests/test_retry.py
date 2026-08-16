"""Tests for scheduling/retry.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.abode_security.const import (
    SCHEDULE_CONFIRM_POLL_SECONDS,
    SCHEDULE_CONFIRM_TIMEOUT_SECONDS,
    SCHEDULE_RETRY_TOTAL_ATTEMPTS,
)
from custom_components.abode_security.scheduling.retry import (
    RetryExhausted,
    async_retry,
    async_retry_confirmed,
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


class TestAsyncRetryConfirmed:
    """State-confirmed retry (#192).

    Abode rejects a mode change that is already underway with 2104, so a retry
    window shorter than the panel's ~60 s arming operation reports a successful
    arm as a total failure.  ``async_retry_confirmed`` asks the panel what state
    it is actually in instead of trusting the service call's outcome.
    """

    async def test_confirm_true_upfront_skips_the_call_entirely(self) -> None:
        factory = AsyncMock()
        with patch(
            "custom_components.abode_security.scheduling.retry.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:
            await async_retry_confirmed(factory, lambda: True, delays=(0, 0, 0))
        factory.assert_not_called()
        mock_sleep.assert_not_called()

    async def test_confirm_true_between_retries_stops_retrying(self) -> None:
        """Panel reaches the target mid-retry — remaining attempts are no-ops."""
        armed = False

        def _confirm() -> bool:
            return armed

        async def _fail_then_arm() -> None:
            nonlocal armed
            if factory.call_count >= 2:
                # The panel finished arming while attempt 2 was in flight.
                armed = True
            raise RuntimeError("2104 Operation error!")

        factory = AsyncMock(side_effect=_fail_then_arm)
        with patch(
            "custom_components.abode_security.scheduling.retry.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await async_retry_confirmed(factory, _confirm, delays=(0, 0, 0))
        # Attempts 1 and 2 ran; attempt 3 saw the confirmed state and skipped.
        assert factory.call_count == 2

    async def test_confirm_true_during_post_exhaustion_poll_is_success(self) -> None:
        """Every attempt fails, but the panel reaches the target while polling."""
        factory = AsyncMock(side_effect=RuntimeError("2104 Operation error!"))
        polls = 0

        def _confirm() -> bool:
            nonlocal polls
            if factory.call_count < SCHEDULE_RETRY_TOTAL_ATTEMPTS:
                return False
            polls += 1
            return polls > 2  # panel settles a couple of polls in

        with patch(
            "custom_components.abode_security.scheduling.retry.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await async_retry_confirmed(factory, _confirm, delays=(0, 0, 0))
        assert factory.call_count == SCHEDULE_RETRY_TOTAL_ATTEMPTS

    async def test_confirm_never_true_raises_retry_exhausted(self) -> None:
        final_err = RuntimeError("final")
        factory = AsyncMock(
            side_effect=[
                RuntimeError("1"),
                RuntimeError("2"),
                RuntimeError("3"),
                final_err,
            ]
        )
        with (
            patch(
                "custom_components.abode_security.scheduling.retry.asyncio.sleep",
                new_callable=AsyncMock,
            ),
            pytest.raises(RetryExhausted) as exc_info,
        ):
            await async_retry_confirmed(factory, lambda: False, delays=(0, 0, 0))
        assert factory.call_count == SCHEDULE_RETRY_TOTAL_ATTEMPTS
        assert exc_info.value.attempts == SCHEDULE_RETRY_TOTAL_ATTEMPTS
        assert exc_info.value.last_error is final_err

    async def test_confirmed_at_exhaustion_needs_no_poll(self) -> None:
        """The panel settling during the final attempt is noticed immediately.

        The last `confirm()` runs before the final attempt, and that attempt
        blocks on a real service call, so the panel can reach the target while
        it is in flight.  Sleeping first would delay the good news by a whole
        poll interval — and skip it entirely when the wait is disabled.
        """
        factory = AsyncMock(side_effect=RuntimeError("2104 Operation error!"))

        def _confirm() -> bool:
            # False for every pre-attempt check, True once they are exhausted.
            return bool(factory.call_count >= SCHEDULE_RETRY_TOTAL_ATTEMPTS)

        with patch(
            "custom_components.abode_security.scheduling.retry.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:
            await async_retry_confirmed(factory, _confirm, delays=(0, 0, 0))
        # Every attempt ran — this is the exhaustion path, not an early return.
        assert factory.call_count == SCHEDULE_RETRY_TOTAL_ATTEMPTS
        # Three backoff sleeps, none from the confirmation wait.
        assert mock_sleep.call_count == 3

    async def test_confirmed_at_exhaustion_with_the_wait_disabled(self) -> None:
        """`polls == 0` must still confirm once rather than reporting failure."""
        factory = AsyncMock(side_effect=RuntimeError("boom"))
        with patch(
            "custom_components.abode_security.scheduling.retry.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await async_retry_confirmed(
                factory,
                lambda: bool(factory.call_count >= SCHEDULE_RETRY_TOTAL_ATTEMPTS),
                delays=(0, 0, 0),
                confirm_poll=0,
            )
        # Pins the exhaustion path: without this, a pre-attempt confirm that
        # turned trivially true would return early and still pass green.
        assert factory.call_count == SCHEDULE_RETRY_TOTAL_ATTEMPTS

    async def test_raising_confirm_in_the_poll_still_reports_failure(self) -> None:
        """A broken predicate must not mask RetryExhausted.

        The poll runs inside `except RetryExhausted`, so an exception escaping
        `confirm()` there would replace it — leaving the manager's
        `except RetryExhausted` handler unrun, and a genuinely failed schedule
        with no `schedule_failed` event and no repair issue.
        """
        factory = AsyncMock(side_effect=RuntimeError("boom"))

        def _broken_confirm() -> bool:
            if factory.call_count >= SCHEDULE_RETRY_TOTAL_ATTEMPTS:
                raise LookupError("panel entity vanished")
            return False

        with (
            patch(
                "custom_components.abode_security.scheduling.retry.asyncio.sleep",
                new_callable=AsyncMock,
            ),
            pytest.raises(RetryExhausted),
        ):
            await async_retry_confirmed(factory, _broken_confirm, delays=(0, 0, 0))

    async def test_post_exhaustion_poll_is_bounded(self) -> None:
        """The confirmation wait cannot spin forever, even with confirm_poll=0."""
        factory = AsyncMock(side_effect=RuntimeError("boom"))
        with (
            patch(
                "custom_components.abode_security.scheduling.retry.asyncio.sleep",
                new_callable=AsyncMock,
            ) as mock_sleep,
            pytest.raises(RetryExhausted),
        ):
            await async_retry_confirmed(
                factory, lambda: False, delays=(0, 0, 0), confirm_poll=0
            )
        # 3 backoff sleeps only — a zero poll interval disables the wait rather
        # than looping without end.
        assert mock_sleep.call_count == 3

    async def test_confirmation_window_outlasts_the_retry_window(self) -> None:
        """The whole point of #192: confirmation must cover a ~60 s arm."""
        retry_window = 1 + 4 + 16  # SCHEDULE_RETRY_DELAYS_SECONDS
        assert SCHEDULE_CONFIRM_TIMEOUT_SECONDS >= 60
        assert retry_window < SCHEDULE_CONFIRM_TIMEOUT_SECONDS
        assert 0 < SCHEDULE_CONFIRM_POLL_SECONDS <= SCHEDULE_CONFIRM_TIMEOUT_SECONDS

    async def test_non_caught_exception_propagates_immediately(self) -> None:
        factory = AsyncMock(side_effect=ValueError("not caught"))
        with (
            patch(
                "custom_components.abode_security.scheduling.retry.asyncio.sleep",
                new_callable=AsyncMock,
            ),
            pytest.raises(ValueError, match="not caught"),
        ):
            await async_retry_confirmed(
                factory, lambda: False, delays=(0, 0, 0), catch=RuntimeError
            )
        factory.assert_called_once()
