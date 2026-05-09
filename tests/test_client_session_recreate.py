"""Client session recreation and cleanup: drains in-flight requests.

Covers the fixes for issue #3 (recreate path) and issue #14 (cleanup path):

1. ``_recreate_session`` waits for in-flight ``_send_request`` calls to complete
   before closing the old session. Without the drain, the in-flight request
   holds a reference to the closed session and aiohttp raises
   ``ClientConnectionResetError`` (or hangs).
2. Concurrent ``_recreate_session`` callers serialize on a single lock so that
   only one ``login()`` runs per swap, instead of two failure paths racing two
   logins.
3. ``_consecutive_failures`` is reset to zero on a successful recreate so the
   threshold doesn't trip again immediately after recovery.
4. ``cleanup`` reuses the same drain primitives so HA shutdown / config-entry
   reload can't close a session out from under an in-flight request.
"""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.abode_security.abode.client import Client
from custom_components.abode_security.abode.exceptions import (
    Exception as AbodeException,
)


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
def _stub_aiohttp_session_and_connector(monkeypatch):
    """Replace the aiohttp.ClientSession and TCPConnector constructors used
    inside _recreate_session so tests don't allocate (and leak) a real
    session or connector. A real TCPConnector registers with the running
    loop and emits an "Unclosed connector" ResourceWarning at GC under
    stricter warning configurations (e.g. PYTHONDEVMODE=1)."""
    fake_session_factory = MagicMock(
        side_effect=lambda *_a, **_kw: MagicMock(close=AsyncMock())
    )
    monkeypatch.setattr(
        "custom_components.abode_security.abode.client.aiohttp.ClientSession",
        fake_session_factory,
    )
    monkeypatch.setattr(
        "custom_components.abode_security.abode.client.aiohttp.TCPConnector",
        MagicMock(side_effect=lambda *_a, **_kw: MagicMock()),
    )


class TestRecreateSessionStubsTCPConnector:
    """The autouse fixture must stub ``aiohttp.TCPConnector`` alongside
    ``aiohttp.ClientSession`` so ``_recreate_session`` doesn't allocate a
    real connector that registers with the running loop and emits an
    "Unclosed connector" ResourceWarning at GC under stricter warning
    configurations (e.g. ``PYTHONDEVMODE=1``)."""

    async def test_recreate_session_does_not_construct_real_connector(self):
        client = _build_client()
        client._session = MagicMock()
        client._session.close = AsyncMock()

        with patch.object(client, "login", new=AsyncMock()):
            await client._recreate_session()

        from custom_components.abode_security.abode.client import (
            aiohttp as client_aiohttp,
        )

        assert isinstance(client_aiohttp.TCPConnector, MagicMock), (
            "aiohttp.TCPConnector must be patched in this test module so "
            "_recreate_session doesn't leak a real connector at GC"
        )
        assert client_aiohttp.TCPConnector.call_count >= 1, (
            "expected _recreate_session to construct (the patched) "
            "TCPConnector at least once per recreate"
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


class TestCleanupDrainsInFlightRequests:
    """``cleanup()`` must drain in-flight requests before closing (issue #14)."""

    async def test_cleanup_waits_for_in_flight_request(self):
        client = _build_client()

        request_started = asyncio.Event()
        release_request = asyncio.Event()

        old_session = MagicMock()
        old_session.close = AsyncMock()
        old_session.get = MagicMock(
            return_value=_ControllableRequest(request_started, release_request)
        )
        client._session = old_session

        request_task = asyncio.create_task(client._send_request("get", "/some/path"))
        await request_started.wait()
        assert old_session.close.await_count == 0

        cleanup_task = asyncio.create_task(client.cleanup())

        # Give cleanup every chance to make forward progress. With the fix
        # it must block on the drain.
        for _ in range(10):
            await asyncio.sleep(0)

        assert not cleanup_task.done(), (
            "cleanup() completed before in-flight request drained"
        )
        assert client._session is old_session, (
            "session was cleared while a request was in flight"
        )
        assert old_session.close.await_count == 0, (
            "session was closed while a request was in flight"
        )

        release_request.set()
        await request_task
        await cleanup_task

        assert old_session.close.await_count == 1
        assert client._session is None
        assert client._closed is True


class TestCleanupDrainTimeout:
    """``cleanup()`` must not hang forever on a stuck request."""

    async def test_cleanup_drain_timeout_forces_close(self):
        client = _build_client()
        client._session_drain_timeout = 0.05

        request_started = asyncio.Event()
        release_request = asyncio.Event()

        old_session = MagicMock()
        old_session.close = AsyncMock()
        old_session.get = MagicMock(
            return_value=_ControllableRequest(request_started, release_request)
        )
        client._session = old_session

        hung_task = asyncio.create_task(client._send_request("get", "/hung"))
        await request_started.wait()
        assert client._inflight_requests == 1

        await client.cleanup()

        assert client._session is None
        assert old_session.close.await_count == 1
        assert client._closed is True
        assert client._session_swap_generation == 1
        assert client._inflight_requests == 0

        # Let the hung request unwind so we don't leak the task.
        release_request.set()
        await hung_task


class TestSendRequestAfterCleanupRaises:
    """Once ``cleanup()`` has run, new requests must not allocate a fresh
    session — the client is terminal."""

    async def test_send_request_after_cleanup_raises(self):
        client = _build_client()
        client._session = MagicMock()
        client._session.close = AsyncMock()

        await client.cleanup()
        assert client._closed is True
        assert client._session is None

        with pytest.raises(AbodeException):
            await client._send_request("get", "/whatever")

        # Crucially, the cleanup must not be undone by a stray request.
        assert client._session is None
        assert client._closed is True


class TestCleanupIsIdempotent:
    """A second ``cleanup()`` call must be a no-op — both
    ``async_unload_entry`` and the ``EVENT_HOMEASSISTANT_STOP`` listener can
    fire on the same client during shutdown."""

    async def test_cleanup_called_twice_closes_session_only_once(self):
        client = _build_client()
        client._session = MagicMock()
        client._session.close = AsyncMock()
        original_session = client._session

        await client.cleanup()
        await client.cleanup()

        assert original_session.close.await_count == 1
        assert client._session is None
        assert client._closed is True
        # The post-lock idempotent return must not re-clear the gate or
        # stomp the in-flight counter — both should still be in their
        # post-cleanup state.
        assert client._session_ready is not None
        assert client._session_ready.is_set()
        assert client._inflight_requests == 0


class TestConcurrentRecreateAndCleanupSerialized:
    """``cleanup()`` and ``_recreate_session`` share ``_session_swap_lock`` so
    one cannot close a session the other is mid-swap on."""

    async def test_cleanup_waits_for_concurrent_recreate(self):
        client = _build_client()
        client._session = MagicMock()
        client._session.close = AsyncMock()

        login_release = asyncio.Event()
        recreate_login_started = asyncio.Event()
        cleanup_observed_session = []

        async def fake_login(*_args, **_kwargs):
            recreate_login_started.set()
            await login_release.wait()

        with patch.object(client, "login", new=fake_login):
            recreate_task = asyncio.create_task(client._recreate_session())
            await recreate_login_started.wait()

            # Recreate is parked inside login() while holding the swap lock.
            # cleanup() must queue behind it rather than close concurrently.
            cleanup_task = asyncio.create_task(client.cleanup())
            for _ in range(10):
                await asyncio.sleep(0)
                cleanup_observed_session.append(client._session)

            assert not cleanup_task.done(), (
                "cleanup() ran while _recreate_session held the swap lock"
            )

            login_release.set()
            await recreate_task
            await cleanup_task

        assert client._session is None
        assert client._closed is True


class TestParkedRequestWokenByCleanupRaises:
    """A `_send_request` parked on `_session_ready.wait()` must raise (not
    advance against a torn-down session) when cleanup re-sets the gate on
    its way out. Without the post-wait `_closed` recheck, the woken caller
    would proceed to dereference `self._session` which is now `None`."""

    async def test_parked_request_raises_when_cleanup_wakes_it(self):
        client = _build_client()
        client._session = MagicMock()
        client._session.close = AsyncMock()
        # Force-create the swap primitives so we can clear the gate from
        # the test without going through `_recreate_session`.
        client._ensure_session_swap_primitives()
        assert client._session_ready is not None
        client._session_ready.clear()

        request_task = asyncio.create_task(client._send_request("get", "/x"))
        for _ in range(5):
            await asyncio.sleep(0)
        assert not request_task.done(), (
            "request advanced past the closed _session_ready gate"
        )

        # Cleanup acquires the swap lock, marks `_closed`, drains (no
        # in-flight requests), closes the session, then re-sets the gate
        # on its way out — waking the parked request, which must observe
        # `_closed` and raise.
        await client.cleanup()

        with pytest.raises(AbodeException):
            await request_task

        assert client._closed is True
        assert client._session is None
        assert client._inflight_requests == 0


class TestConcurrentCleanupsAwaitCompletion:
    """Two concurrent ``cleanup()`` calls (e.g. ``async_unload_entry`` and
    the ``EVENT_HOMEASSISTANT_STOP`` listener firing on the same client)
    must both await the actual teardown — neither may return early while
    the other is still draining or closing the session."""

    async def test_second_cleanup_does_not_return_until_first_finishes(self):
        client = _build_client()

        request_started = asyncio.Event()
        release_request = asyncio.Event()

        old_session = MagicMock()
        old_session.close = AsyncMock()
        old_session.get = MagicMock(
            return_value=_ControllableRequest(request_started, release_request)
        )
        client._session = old_session

        # Start a request so cleanup actually has to drain.
        request_task = asyncio.create_task(client._send_request("get", "/x"))
        await request_started.wait()

        cleanup_a = asyncio.create_task(client.cleanup())
        # Yield enough to let cleanup_a acquire the swap lock and set
        # `_closed = True` while it parks on the drain event.
        for _ in range(10):
            await asyncio.sleep(0)
        assert client._closed is True
        assert not cleanup_a.done()

        cleanup_b = asyncio.create_task(client.cleanup())
        for _ in range(10):
            await asyncio.sleep(0)
        # cleanup_b must NOT have returned: cleanup_a is still mid-drain
        # holding the swap lock, even though `_closed` is already True.
        assert not cleanup_b.done(), (
            "second cleanup() returned before first finished — concurrent"
            " caller would observe an unfinished teardown"
        )

        release_request.set()
        await request_task
        await cleanup_a
        await cleanup_b

        assert old_session.close.await_count == 1
        assert client._session is None
        assert client._closed is True


class TestCleanupSwallowsCloseErrors:
    """A real exception from ``self._session.close()`` (e.g. an
    ``aiohttp.ClientError`` or ``OSError``) must not propagate out of
    ``cleanup()`` and leave the client half-torn-down. ``Exception`` is
    shadowed in client.py by the abode-namespaced subclass, so the catch
    must use ``builtins.Exception`` to actually fire."""

    async def test_cleanup_logs_and_swallows_aiohttp_close_error(self, caplog):
        client = _build_client()
        client._session = MagicMock()
        client._session.close = AsyncMock(
            side_effect=aiohttp.ClientError("simulated close failure")
        )

        with caplog.at_level(
            logging.WARNING,
            logger="custom_components.abode_security.abode.client",
        ):
            await client.cleanup()

        assert client._session is None
        assert client._closed is True
        assert "Error closing session during cleanup" in caplog.text


class TestRecreateAfterCleanupNoOps:
    """`_recreate_session` must not resurrect a torn-down client.

    A late `_handle_empty_response_and_retry` racing shutdown could
    otherwise allocate a fresh session after `cleanup()` has run, leaking
    it and re-opening the shutdown race.
    """

    async def test_recreate_after_cleanup_does_not_allocate_session(self):
        client = _build_client()
        client._session = MagicMock()
        client._session.close = AsyncMock()

        login_calls = 0

        async def fake_login(*_args, **_kwargs):
            nonlocal login_calls
            login_calls += 1

        with patch.object(client, "login", new=fake_login):
            await client.cleanup()
            assert client._closed is True
            assert client._session is None

            # Late recreate must observe `_closed` and bail without
            # creating a new aiohttp session or running a fresh login.
            await client._recreate_session()

        assert client._session is None
        assert login_calls == 0
        assert client._closed is True
