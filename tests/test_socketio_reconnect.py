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

from unittest.mock import Mock, patch

from custom_components.abode_security.abode import socketio as sio_module
from custom_components.abode_security.abode.exceptions import SocketIOException
from custom_components.abode_security.abode.helpers import errors as ERRORS
from custom_components.abode_security.abode.socketio import SocketIO


def _stub_intervals(monkeypatch):
    """Make BackoffIntervals.__next__ return 0 so _run doesn't sleep."""
    monkeypatch.setattr(sio_module.BackoffIntervals, "__next__", lambda _self: 0)


class TestPersistentDisconnect:
    """SocketIO surfaces a persistent_disconnect event after N failures."""

    def test_fires_after_threshold_connect_failures(self, monkeypatch):
        _stub_intervals(monkeypatch)
        s = SocketIO(url="ws://example/socket.io/", cookie="seed")

        fired = []
        s.on("persistent_disconnect", lambda count: fired.append(count))

        threshold = SocketIO.PERSISTENT_DISCONNECT_THRESHOLD
        attempts = {"n": 0}

        def fake_step(_intervals):
            attempts["n"] += 1
            # Stop a couple iterations past the threshold so we see one fire.
            if attempts["n"] >= threshold + 2:
                s._running = False
            raise SocketIOException(ERRORS.SOCKETIO_ERROR, details="boom")

        s._step = fake_step  # type: ignore[assignment]
        s._run()

        assert fired == [threshold], (
            "persistent_disconnect must fire exactly once after threshold reached, "
            f"got {fired}"
        )

    def test_does_not_fire_below_threshold(self, monkeypatch):
        _stub_intervals(monkeypatch)
        s = SocketIO(url="ws://example/socket.io/", cookie="seed")
        fired = []
        s.on("persistent_disconnect", lambda count: fired.append(count))

        attempts = {"n": 0}
        # Stop a few iterations short of the threshold.
        stop_at = SocketIO.PERSISTENT_DISCONNECT_THRESHOLD - 2

        def fake_step(_intervals):
            attempts["n"] += 1
            if attempts["n"] >= stop_at:
                s._running = False
            raise SocketIOException(ERRORS.SOCKETIO_ERROR, details="boom")

        s._step = fake_step  # type: ignore[assignment]
        s._run()

        assert fired == []

    def test_resets_after_successful_connect_then_refires(self, monkeypatch):
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

        def fake_step(_intervals):
            attempts["n"] += 1
            # Fail enough times to fire persistent_disconnect once.
            if attempts["n"] == threshold + 2:
                # Simulate a successful websocket connect: the handler resets
                # counters and emits connection_recovered.
                s._on_websocket_connected(Mock())
            # Then fail again until the threshold trips a second time.
            if attempts["n"] >= 2 * threshold + 4:
                s._running = False
            raise SocketIOException(ERRORS.SOCKETIO_ERROR, details="boom")

        s._step = fake_step  # type: ignore[assignment]
        s._run()

        assert recovered == [True], "connection_recovered should fire after reset"
        assert fired == [threshold, threshold], (
            f"persistent_disconnect should fire twice (once before recovery, "
            f"once after a second run of failures), got {fired}"
        )

    def test_websocket_connected_resets_counter(self):
        s = SocketIO(url="ws://example/socket.io/", cookie="seed")
        s._connect_failures = 7
        s._persistent_disconnect_fired = False

        s._on_websocket_connected(Mock())

        assert s._connect_failures == 0


class TestCookieClearingBetweenIterations:
    """Stale cookies are not reused across reconnect attempts."""

    def test_cookie_cleared_before_subsequent_iterations(self, monkeypatch):
        _stub_intervals(monkeypatch)
        s = SocketIO(url="ws://example/socket.io/", cookie="initial-cookie")

        seen_cookies = []
        attempts = {"n": 0}

        def fake_step(_intervals):
            seen_cookies.append(s._cookie)
            attempts["n"] += 1
            if attempts["n"] >= 3:
                s._running = False
            raise SocketIOException(ERRORS.SOCKETIO_ERROR, details="boom")

        s._step = fake_step  # type: ignore[assignment]
        s._run()

        assert seen_cookies[0] == "initial-cookie", "first iteration uses seeded cookie"
        assert seen_cookies[1:] == [None, None], (
            "later iterations must clear cookie so the wait loop blocks for fresh ones, "
            f"got {seen_cookies}"
        )


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
        # A running event loop substitute - just enough to satisfy the guard.
        loop = Mock()
        loop.is_running = Mock(return_value=True)
        ec._event_loop = loop
        return ec

    def test_seeds_only_on_first_started(self, monkeypatch):
        ec = self._make_controller()

        fake_session = Mock()
        # Concrete value isn't used; _cookie_string is monkeypatched below.
        fake_session.cookie_jar = []
        from custom_components.abode_security.abode import event_controller as ec_module

        monkeypatch.setattr(ec_module, "_cookie_string", lambda _jar: "seed=value")
        ec._client._session = fake_session

        # Don't actually schedule anything on the event loop.
        with patch(
            "custom_components.abode_security.abode.event_controller.asyncio.run_coroutine_threadsafe"
        ) as mock_schedule:
            mock_schedule.return_value = Mock()

            ec._on_socket_started()
            ec._on_socket_started()
            ec._on_socket_started()

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
