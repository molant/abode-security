"""Retry policy for schedule arm/disarm operations."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from typing import TypeVar

from ..const import SCHEDULE_RETRY_DELAYS_SECONDS

T = TypeVar("T")


class RetryExhausted(Exception):
    """Raised when all retry attempts have failed."""

    def __init__(self, last_error: BaseException, attempts: int) -> None:
        super().__init__(f"Exhausted after {attempts} attempts: {last_error}")
        self.last_error = last_error
        self.attempts = attempts


async def async_retry(  # noqa: UP047
    factory: Callable[[], Awaitable[T]],
    *,
    delays: Iterable[int] = SCHEDULE_RETRY_DELAYS_SECONDS,
    catch: type[BaseException] | tuple[type[BaseException], ...] = Exception,
) -> T:
    """Run ``factory()`` with exponential backoff retry.

    Parameters
    ----------
    factory:
        Zero-argument async callable to retry.
    delays:
        Sequence of sleep durations (seconds) between attempts.  Length
        determines the number of retries: len(delays) retries after the
        initial attempt.  Pass ``(0, 0, 0)`` in tests to avoid real waits.
    catch:
        Exception type(s) to catch and retry on.  Any other exception
        propagates immediately without retry.

    Raises
    ------
    RetryExhausted
        After all attempts (1 initial + len(delays) retries) have failed.
    """
    delays_list = list(delays)
    last_error: BaseException | None = None
    total_attempts = len(delays_list) + 1
    for attempt in range(total_attempts):
        try:
            return await factory()
        except catch as err:
            last_error = err
            if attempt < total_attempts - 1:
                await asyncio.sleep(delays_list[attempt])
    assert last_error is not None
    raise RetryExhausted(last_error, total_attempts)
