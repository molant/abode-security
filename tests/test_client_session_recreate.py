"""Client session recreation: drains in-flight requests, serializes recreates.

Covers the fixes for issue #3:

1. ``_recreate_session`` waits for in-flight ``_send_request`` calls to complete
   before closing the old session. Without the drain, the in-flight request
   holds a reference to the closed session and aiohttp raises
   ``ClientConnectionResetError`` (or hangs).
2. Concurrent ``_recreate_session`` callers serialize on a single lock so that
   only one ``login()`` runs per swap, instead of two failure paths racing two
   logins.
3. ``_consecutive_failures`` is reset to zero on a successful recreate so the
   threshold doesn't trip again immediately after recovery.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.abode_security.abode.client import Client


class _FakeResponse:
    """Minimal aiohttp.ClientResponse stand-in for tests."""

    def __init__(self):
        self.status = 200
        self.headers = {}

    async def json(self):
        return {"ok": True}

    async def text(self):
        return '{"ok": true}'


class _ControllableRequest:
    """Async context manager that pauses inside __aenter__ until released."""

    def __init__(self, started: asyncio.Event, release: asyncio.Event):
        self._started = started
        self._release = release

    async def __aenter__(self):
        self._started.set()
        await self._release.wait()
        return _FakeResponse()

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _build_client() -> Client:
    """Build a Client without triggering network or session monitor task."""
    client = Client(username="user@example.com", password="hunter2")
    client._initialized = True
    client._token = "fake-token"
    client._oauth_token = "fake-oauth"
    return client


@pytest.fixture(autouse=True)
def _stub_sync_socketio_cookies(monkeypatch):
    """Avoid touching the real EventController/SocketIO during these tests."""
    monkeypatch.setattr(Client, "_sync_socketio_cookies", AsyncMock())


@pytest.fixture(autouse=True)
def _stub_aiohttp_client_session(monkeypatch):
    """Replace the aiohttp.ClientSession constructor used inside
    _recreate_session so tests don't allocate (and leak) a real session."""
    fake_session_factory = MagicMock(
        side_effect=lambda *_a, **_kw: MagicMock(close=AsyncMock())
    )
    monkeypatch.setattr(
        "custom_components.abode_security.abode.client.aiohttp.ClientSession",
        fake_session_factory,
    )


class TestSessionRecreateDrainsInFlightRequests:
    """``_recreate_session`` must wait for in-flight requests before closing."""

    async def test_recreate_waits_for_in_flight_request(self):
        client = _build_client()

        request_started = asyncio.Event()
        release_request = asyncio.Event()

        # Old session: ``get`` returns a context manager that blocks until
        # ``release_request`` is set. ``close`` records when it ran.
        old_session = MagicMock()
        old_session.close = AsyncMock()
        old_session.get = MagicMock(
            return_value=_ControllableRequest(request_started, release_request)
        )
        client._session = old_session

        with patch.object(client, "login", new=AsyncMock()):
            request_task = asyncio.create_task(
                client._send_request("get", "/some/path")
            )
            await request_started.wait()
            assert old_session.close.await_count == 0

            recreate_task = asyncio.create_task(client._recreate_session())

            # Yield several times so recreate has every chance to make
            # forward progress. With the fix it must block on the drain.
            for _ in range(10):
                await asyncio.sleep(0)

            assert not recreate_task.done(), (
                "_recreate_session completed before in-flight request drained"
            )
            assert client._session is old_session, (
                "session was swapped while a request was in flight"
            )
            assert old_session.close.await_count == 0, (
                "old session was closed while a request was in flight"
            )

            # Release the in-flight request; recreate should now proceed.
            release_request.set()
            await request_task
            await recreate_task

            assert old_session.close.await_count == 1
            assert client._session is not old_session


class TestConcurrentRecreateSerialized:
    """Concurrent failure paths must not race two logins."""

    async def test_two_concurrent_recreates_run_one_login_at_a_time(self):
        client = _build_client()
        client._consecutive_failures = 5

        client._session = MagicMock()
        client._session.close = AsyncMock()

        login_release = asyncio.Event()
        in_login = 0
        max_in_login = 0
        login_calls = 0

        async def fake_login(*_args, **_kwargs):
            nonlocal in_login, max_in_login, login_calls
            in_login += 1
            max_in_login = max(max_in_login, in_login)
            login_calls += 1
            # Block until the test releases — this forces both recreates to
            # be observed inside login() simultaneously if they raced.
            await login_release.wait()
            in_login -= 1

        with patch.object(client, "login", new=fake_login):
            t1 = asyncio.create_task(client._recreate_session())
            t2 = asyncio.create_task(client._recreate_session())

            # Pump the loop so both tasks have a chance to enter login() if
            # nothing serializes them.
            for _ in range(20):
                await asyncio.sleep(0)

            # Without the lock, both recreates have already entered fake_login
            # and are both blocked on login_release: max_in_login == 2.
            # With the lock, only one can be inside; the other is queued on
            # the swap lock: max_in_login == 1.
            observed_overlap = max_in_login

            # Release everyone and let the tasks drain.
            login_release.set()
            await asyncio.gather(t1, t2)

        assert observed_overlap == 1, (
            f"recreates raced — {observed_overlap} logins observed concurrently"
        )
        assert login_calls == 2, (
            f"expected one login per serialized recreate, got {login_calls}"
        )


class TestRecreateResetsFailureCounter:
    """Successful recreate clears _consecutive_failures."""

    async def test_failure_counter_reset_after_recreate(self):
        client = _build_client()
        client._consecutive_failures = 7

        client._session = MagicMock()
        client._session.close = AsyncMock()

        with patch.object(client, "login", new=AsyncMock()):
            await client._recreate_session()

        assert client._consecutive_failures == 0


class TestZombieDecrementAfterDrainTimeout:
    """A hung request that completes after a drain-timeout reset must not
    decrement an unrelated request's in-flight slot."""

    async def test_hung_request_finally_skipped_after_generation_bump(self):
        client = _build_client()
        # Compress the drain timeout so the test runs quickly.
        client._session_drain_timeout = 0.05

        request_started = asyncio.Event()
        release_request = asyncio.Event()

        old_session = MagicMock()
        old_session.close = AsyncMock()
        old_session.get = MagicMock(
            return_value=_ControllableRequest(request_started, release_request)
        )
        client._session = old_session

        with patch.object(client, "login", new=AsyncMock()):
            # Start a request that will hang past the drain timeout.
            hung_task = asyncio.create_task(client._send_request("get", "/hung"))
            await request_started.wait()
            assert client._inflight_requests == 1

            # Recreate hits the drain timeout (since we never release the
            # request). The generation token must bump and the counter
            # must be cleared.
            await client._recreate_session()
            assert client._session is not old_session
            assert client._inflight_requests == 0
            assert client._session_swap_generation == 1

            # Simulate a fresh in-flight request against the new session
            # (we don't run the body — just register the slot the same way
            # _send_request would, with the post-swap generation).
            client._inflight_requests = 1
            client._inflight_zero_event.clear()

            # Now release the hung request. Its captured generation is 0,
            # current generation is 1, so its finally must NOT decrement.
            release_request.set()
            await hung_task

            assert client._inflight_requests == 1, (
                "hung request decremented an unrelated in-flight slot after"
                " drain-timeout reset"
            )
            assert not client._inflight_zero_event.is_set()
