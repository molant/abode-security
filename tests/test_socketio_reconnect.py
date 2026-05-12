"""SocketIO reconnect behavior: cookie refresh, persistent disconnect surface.

Covers the fixes for issue #2:
1. Cookies are cleared between reconnect iterations so stale cookies aren't reused.
2. After PERSISTENT_DISCONNECT_THRESHOLD consecutive failures, a
   `persistent_disconnect` event is dispatched (once, until next successful connect).
3. The failure counter resets when the websocket reaches `Connected`.
4. EventController seeds cookies from the existing session only on the first
   `started` event; subsequent events skip seeding so the SocketIO wait loop
   actually blocks on a fresh `_async_get_session()`.
"""

import asyncio
import logging
from unittest.mock import AsyncMock, Mock, patch

from custom_components.abode_security.abode import socketio as sio_module
from custom_components.abode_security.abode._websocket import AbodeWebSocket
from custom_components.abode_security.abode.exceptions import SocketIOException
from custom_components.abode_security.abode.helpers import errors as ERRORS
from custom_components.abode_security.abode.socketio import SocketIO


def _stub_intervals(monkeypatch):
    """Make BackoffIntervals.__next__ return 0 so _run doesn't sleep."""
    monkeypatch.setattr(sio_module.BackoffIntervals, "__next__", lambda _self: 0)


class TestPersistentDisconnect:
    """SocketIO surfaces a persistent_disconnect event after N failures."""

    async def test_fires_after_threshold_connect_failures(self, monkeypatch):
        _stub_intervals(monkeypatch)
        s = SocketIO(url="ws://example/socket.io/", cookie="seed")

        fired = []
        s.on("persistent_disconnect", lambda count: fired.append(count))

        threshold = SocketIO.PERSISTENT_DISCONNECT_THRESHOLD
        attempts = {"n": 0}

        async def fake_step(_intervals):
            attempts["n"] += 1
            # Stop a couple iterations past the threshold so we see one fire.
            if attempts["n"] >= threshold + 2:
                s._running = False
            raise SocketIOException(ERRORS.SOCKETIO_ERROR, details="boom")

        s._step = fake_step  # type: ignore[assignment]
        await s._run()

        assert fired == [threshold], (
            "persistent_disconnect must fire exactly once after threshold reached, "
            f"got {fired}"
        )

    async def test_does_not_fire_below_threshold(self, monkeypatch):
        _stub_intervals(monkeypatch)
        s = SocketIO(url="ws://example/socket.io/", cookie="seed")
        fired = []
        s.on("persistent_disconnect", lambda count: fired.append(count))

        attempts = {"n": 0}
        # Stop a few iterations short of the threshold.
        stop_at = SocketIO.PERSISTENT_DISCONNECT_THRESHOLD - 2

        async def fake_step(_intervals):
            attempts["n"] += 1
            if attempts["n"] >= stop_at:
                s._running = False
            raise SocketIOException(ERRORS.SOCKETIO_ERROR, details="boom")

        s._step = fake_step  # type: ignore[assignment]
        await s._run()

        assert fired == []

    async def test_resets_after_successful_connect_then_refires(self, monkeypatch):
        """After a recovery, the threshold counter restarts so a later
        persistent failure can fire again."""
        _stub_intervals(monkeypatch)
        s = SocketIO(url="ws://example/socket.io/", cookie="seed")
        fired = []
        recovered = []
        s.on("persistent_disconnect", lambda count: fired.append(count))
        s.on("connection_recovered", lambda: recovered.append(True))

        threshold = SocketIO.PERSISTENT_DISCONNECT_THRESHOLD
        attempts = {"n": 0}

        async def fake_step(_intervals):
            attempts["n"] += 1
            # Fail enough times to fire persistent_disconnect once.
            if attempts["n"] == threshold + 2:
                # Simulate a successful websocket connect: the handler resets
                # counters and emits connection_recovered.
                await s._on_websocket_connected(Mock())
            # Then fail again until the threshold trips a second time.
            if attempts["n"] >= 2 * threshold + 4:
                s._running = False
            raise SocketIOException(ERRORS.SOCKETIO_ERROR, details="boom")

        s._step = fake_step  # type: ignore[assignment]
        await s._run()

        assert recovered == [True], "connection_recovered should fire after reset"
        assert fired == [threshold, threshold], (
            f"persistent_disconnect should fire twice (once before recovery, "
            f"once after a second run of failures), got {fired}"
        )

    async def test_websocket_connected_resets_counter(self):
        s = SocketIO(url="ws://example/socket.io/", cookie="seed")
        s._connect_failures = 7
        s._persistent_disconnect_fired = False

        await s._on_websocket_connected(Mock())

        assert s._connect_failures == 0


class TestCookieClearingBetweenIterations:
    """Stale cookies are not reused across reconnect attempts."""

    async def test_cookie_cleared_before_subsequent_iterations(self, monkeypatch):
        _stub_intervals(monkeypatch)
        s = SocketIO(url="ws://example/socket.io/", cookie="initial-cookie")

        seen_cookies = []
        attempts = {"n": 0}

        async def fake_step(_intervals):
            seen_cookies.append(s._cookie)
            attempts["n"] += 1
            if attempts["n"] >= 3:
                s._running = False
            raise SocketIOException(ERRORS.SOCKETIO_ERROR, details="boom")

        s._step = fake_step  # type: ignore[assignment]
        await s._run()

        assert seen_cookies[0] == "initial-cookie", "first iteration uses seeded cookie"
        assert seen_cookies[1:] == [None, None], (
            "later iterations must clear cookie so the wait loop blocks for fresh ones, "
            f"got {seen_cookies}"
        )


class TestSocketIOShutdown:
    """Shutdown contract for the async task."""

    async def test_stop_returns_when_task_exits_cleanly(self):
        """stop() returns normally when the task exits after _exit_event.set()."""
        s = SocketIO(url="ws://example/socket.io/")

        async def cooperative_run():
            await s._exit_event.wait()

        task = asyncio.create_task(cooperative_run())
        s._task = task
        s._running = True

        await s.stop()

        assert s._task is None
        assert task.done() and not task.cancelled()

    async def test_stop_closes_websocket_when_connected(self):
        """stop() proactively closes the websocket only after _on_websocket_connected fired."""
        s = SocketIO(url="ws://example/socket.io/")
        ws = Mock(spec=AbodeWebSocket)
        ws.close = AsyncMock(return_value=None)
        s._websocket = ws  # type: ignore[assignment]
        s._websocket_connected = True  # simulate post-connect (receive phase)

        async def cooperative_run():
            await s._exit_event.wait()

        s._task = asyncio.create_task(cooperative_run())
        s._running = True

        await s.stop()

        ws.close.assert_awaited_once()
        assert s._task is None

    async def test_stop_does_not_close_websocket_during_connect(self):
        """During connect() the gate must skip ws.close() so aiohttp's resolve_host
        shield isn't cancelled — that path raises CancelledError that escapes
        connect()'s aiohttp.ClientError handler and surfaces as a teardown error."""
        s = SocketIO(url="ws://example/socket.io/")
        ws = Mock(spec=AbodeWebSocket)
        ws.close = AsyncMock(return_value=None)
        s._websocket = ws  # type: ignore[assignment]
        s._websocket_connected = False  # simulate mid-connect

        async def cooperative_run():
            await s._exit_event.wait()

        s._task = asyncio.create_task(cooperative_run())
        s._running = True

        await s.stop()

        ws.close.assert_not_awaited()
        assert s._task is None

    async def test_stop_called_from_within_own_task_skips_self_await(self):
        """A callback dispatched from inside the SocketIO task may trigger
        stop() (e.g. via an HA reload cascade). Awaiting self._task from
        within itself raises RuntimeError — the guard must short-circuit
        and let the task exit naturally on its next iteration."""
        s = SocketIO(url="ws://example/socket.io/")
        s._websocket_connected = False  # don't try to close a non-existent ws

        async def run_that_calls_stop():
            # Simulates a callback inside the task triggering stop().
            await s.stop()

        task = asyncio.create_task(run_that_calls_stop())
        s._task = task
        s._running = True

        # If the guard is missing, the task body raises RuntimeError.
        await task

        assert not task.cancelled()
        assert task.exception() is None, (
            f"stop() from within own task must not raise; got {task.exception()!r}"
        )
        # The stop flags must have been set so _run's loop will observe them
        # on its next iteration.
        assert s._running is False
        assert s._exit_event.is_set()
        # _task intentionally NOT cleared on the self-await path: an outside
        # stop() may still want to await it.
        assert s._task is task

    async def test_start_after_stop_clears_exit_event(self, monkeypatch):
        """A restart (e.g. config-entry reload) must clear _exit_event so the
        next _step()'s cookie-wait doesn't bail immediately."""
        _stub_intervals(monkeypatch)
        s = SocketIO(url="ws://example/socket.io/", cookie="seed")
        # Simulate the state after a completed stop(): exit event set, task cleared.
        s._exit_event.set()
        s._task = None

        # Track how _step() sees the exit event when the restarted task enters it.
        seen_set_at_step_start: list[bool] = []

        async def fake_step(_intervals):
            seen_set_at_step_start.append(s._exit_event.is_set())
            s._running = False  # exit the _run loop after one iteration

        s._step = fake_step  # type: ignore[assignment]
        s.start()
        task: asyncio.Task[None] | None = s._task
        assert task is not None
        await task

        assert seen_set_at_step_start == [False], (
            "start() must clear the exit event set by stop() so the next "
            f"_step() doesn't bail immediately; saw {seen_set_at_step_start}"
        )

    async def test_stop_cancels_stuck_task_with_warning(self, caplog):
        """A stuck task that ignores the exit event is force-cancelled with a warning."""
        s = SocketIO(url="ws://example/socket.io/")

        never_resolves: asyncio.Future[None] = (
            asyncio.get_running_loop().create_future()
        )

        async def stuck_run():
            await never_resolves

        task = asyncio.create_task(stuck_run())
        s._task = task
        s._running = True

        # Patch wait_for: first call (10s grace) raises TimeoutError immediately;
        # second call (1s cancel drain) uses the real wait_for so the task is
        # properly reaped after cancel().
        original_wait_for = asyncio.wait_for
        first_call = {"done": False}

        async def patched_wait_for(coro_or_fut, **kwargs):
            if not first_call["done"]:
                first_call["done"] = True
                raise TimeoutError()
            return await original_wait_for(coro_or_fut, **kwargs)

        with (
            patch(
                "custom_components.abode_security.abode.socketio.asyncio.wait_for",
                patched_wait_for,
            ),
            caplog.at_level(
                logging.WARNING,
                logger="custom_components.abode_security.abode.socketio",
            ),
        ):
            await s.stop()

        never_resolves.cancel()  # clean up the future so no lingering tasks remain
        assert s._task is None
        assert "did not exit within 10s" in caplog.text
        assert task.cancelled()


class TestEventControllerStartedSeeding:
    """EventController only seeds cookies on the first `started` event.

    On reconnect the in-memory session.cookie_jar may be stale; the SocketIO
    wait loop must block until _async_get_session() refreshes them.
    """

    def _make_controller(self):
        from custom_components.abode_security.abode import event_controller as ec_module

        client = Mock()
        # Build the controller without touching real network endpoints.
        # Patch SocketIO so __init__ doesn't try to start anything.
        with patch.object(ec_module.sio, "SocketIO") as mock_socketio_cls:
            mock_socketio_cls.return_value = Mock()
            ec = ec_module.EventController(client=client, url="ws://example/")
        return ec

    async def test_seeds_only_on_first_started(self, monkeypatch):
        ec = self._make_controller()

        fake_session = Mock()
        # Concrete value isn't used; _cookie_string is monkeypatched below.
        fake_session.cookie_jar = []
        from custom_components.abode_security.abode import event_controller as ec_module

        monkeypatch.setattr(ec_module, "_cookie_string", lambda _jar: "seed=value")
        ec._client._session = fake_session
        # Stub out _async_get_session so it doesn't hit the real client.
        ec._async_get_session = AsyncMock()

        await ec._on_socket_started()
        await ec._on_socket_started()
        await ec._on_socket_started()

        set_cookie_calls = ec._socketio.set_cookie.call_args_list
        # Only the first started call should have seeded the cookie.
        assert len(set_cookie_calls) == 1, (
            f"set_cookie should be called once (first started only), "
            f"got {len(set_cookie_calls)} calls: {set_cookie_calls}"
        )
        assert set_cookie_calls[0][0] == ("seed=value",)

    def test_persistent_disconnect_handler_updates_client_status(self):
        ec = self._make_controller()
        # Make _set_connection_status track invocations.
        ec._client._set_connection_status = Mock()

        ec._on_persistent_disconnect(20)

        ec._client._set_connection_status.assert_called_once()
        args = ec._client._set_connection_status.call_args
        assert args[0][0] == "persistent_disconnect"
        assert "20" in (args[0][1] or "")

    def test_connection_recovered_handler_updates_client_status(self):
        ec = self._make_controller()
        ec._client._set_connection_status = Mock()

        ec._on_connection_recovered()

        ec._client._set_connection_status.assert_called_once()
        args = ec._client._set_connection_status.call_args
        assert args[0][0] == "connected"


class TestExecuteCallbackAsync:
    """_execute_callback fire-and-forget: task completes and is logged."""

    async def test_async_callback_runs_as_task(self):
        from custom_components.abode_security.abode.event_controller import (
            _execute_callback,
        )

        completed: list[str] = []

        async def my_callback(value):
            completed.append(value)

        _execute_callback(my_callback, "hello")
        # Two iterations: first runs the task, second lets the done-callback fire.
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        assert completed == ["hello"]

    async def test_async_callback_failure_consumed_by_done_callback(self, caplog):
        """Task failures do not surface as unhandled-task warnings; they're logged."""
        from custom_components.abode_security.abode.event_controller import (
            _execute_callback,
        )

        async def failing_callback():
            raise ValueError("intentional failure")

        with caplog.at_level(
            logging.ERROR,
            logger="custom_components.abode_security.abode.event_controller",
        ):
            _execute_callback(failing_callback)
            # Two iterations: first runs the task, second lets the done-callback fire.
            await asyncio.sleep(0)
            await asyncio.sleep(0)

        assert "Callback execution failed" in caplog.text
        assert "intentional failure" in caplog.text
