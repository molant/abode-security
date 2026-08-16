"""Retry policy for schedule arm/disarm operations."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Iterable
from typing import TypeVar

from ..const import (
    SCHEDULE_CONFIRM_POLL_SECONDS,
    SCHEDULE_CONFIRM_TIMEOUT_SECONDS,
    SCHEDULE_RETRY_DELAYS_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

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


async def async_retry_confirmed(
    factory: Callable[[], Awaitable[object]],
    confirm: Callable[[], bool],
    *,
    delays: Iterable[int] = SCHEDULE_RETRY_DELAYS_SECONDS,
    confirm_timeout: int = SCHEDULE_CONFIRM_TIMEOUT_SECONDS,
    confirm_poll: int = SCHEDULE_CONFIRM_POLL_SECONDS,
    catch: type[BaseException] | tuple[type[BaseException], ...] = Exception,
) -> None:
    """Retry ``factory()``, but let ``confirm()`` overrule its errors.

    A mode change's HTTP response is not the outcome that matters — the panel's
    state is.  Abode's arm takes ~60 s and answers any mode change issued while
    one is in progress with `2104 Operation error!`, so a retry window shorter
    than the operation reports a successful arm as a total failure (#192).

    ``confirm()`` reports whether the panel has reached the target mode.  It is
    consulted at three points:

    * before every attempt, so once the panel confirms, the remaining retries
      become no-ops instead of generating more `2104`s;
    * immediately after the attempts are exhausted — the final attempt blocks on
      a real service call, and the panel may have settled while it was in
      flight;
    * then polled for up to ``confirm_timeout``, so a transition that outlasts
      the whole retry window still resolves as success.

    Parameters
    ----------
    factory:
        Zero-argument async callable performing the mode change.
    confirm:
        Zero-argument sync predicate — True once the panel is in the target
        state.  Must be cheap: it reads local state, never the API.  A predicate
        that raises counts as "not confirmed" rather than propagating.
    delays:
        Backoff between attempts; see :func:`async_retry`.
    confirm_timeout:
        Seconds to wait for the panel after the attempts are exhausted.
    confirm_poll:
        Seconds between confirmation polls.  The wait is count-based, so a poll
        interval that does not divide ``confirm_timeout`` truncates it (7 into
        90 gives 12 polls, 84 s).  Zero or negative disables the wait rather
        than looping without end.  Deliberately not deadline-based: tests stub
        ``asyncio.sleep``, and a wall-clock deadline would never elapse.
    catch:
        Exception type(s) to retry on; anything else propagates immediately.

    Raises
    ------
    RetryExhausted
        When every attempt failed and the panel never reached the target state.
    """

    logged_confirm_error = False

    def _confirmed() -> bool:
        """Evaluate ``confirm()``, treating a raising predicate as unconfirmed.

        Every call site needs this, for two different reasons:

        * in ``_attempt``, a raising predicate would otherwise be caught by
          ``async_retry``'s ``catch`` and counted as a failed attempt — so the
          mode change would never be issued at all;
        * in either post-exhaustion check (the immediate one and the poll), it
          would replace ``RetryExhausted`` with itself, leaving the caller's
          ``except RetryExhausted`` handler unrun: no schedule_failed event and
          no repair issue for a schedule that genuinely failed.  Both run inside
          the ``except`` block, so neither may call ``confirm()`` directly.

        Unconfirmed is the safe reading everywhere.
        """
        nonlocal logged_confirm_error
        try:
            return confirm()
        except Exception:  # noqa: BLE001 — deliberate; see the docstring above
            if not logged_confirm_error:
                # Once per call: the poll can run 18 times at the defaults, and
                # 18 identical tracebacks bury the signal.
                logged_confirm_error = True
                _LOGGER.exception(
                    "Schedule state confirmation raised; treating as unconfirmed"
                )
            else:
                _LOGGER.debug("Schedule state confirmation raised again")
            return False

    async def _attempt() -> None:
        if _confirmed():
            return
        await factory()

    try:
        await async_retry(_attempt, delays=delays, catch=catch)
    except RetryExhausted:
        # Check before sleeping.  The last `_confirmed()` ran *before* the final
        # attempt, and that attempt blocks on a real service call — so the panel
        # may well have settled while it was in flight.  Without this the good
        # news waits a whole poll interval, and when `polls` is 0 (a poll
        # interval above the timeout, or the wait disabled outright) it is
        # never noticed at all.
        if _confirmed():
            return
        polls = confirm_timeout // confirm_poll if confirm_poll > 0 else 0
        for _ in range(polls):
            await asyncio.sleep(confirm_poll)
            if _confirmed():
                return
        raise
