"""Small SocketIO client via Websockets."""

import asyncio
import collections
import contextlib
import datetime
import inspect
import itertools
import json
import logging
import random
import urllib.parse
from typing import Any

from ._websocket import AbodeWebSocket, AbodeWebSocketError
from .exceptions import SocketIOException
from .helpers import errors as ERRORS
from .helpers._collections import BijectiveMap

log = logging.getLogger(__name__)


class EngineIO:
    codes = BijectiveMap(
        open=0,
        close=1,
        ping=2,
        pong=3,
        message=4,
    )


class BackoffIntervals:
    """
    >>> bi = BackoffIntervals()
    >>> intervals = list(itertools.islice(bi, 10))
    >>> all(
    ...     BackoffIntervals.min_wait <= interval <= BackoffIntervals.max_wait
    ...     for interval in intervals)
    True
    """

    min_wait = 5
    max_wait = 30
    diff = max_wait - min_wait

    def __init__(self):
        self.reset(1)

    def __iter__(self):
        return self

    def __next__(self):
        attempt = next(self.attempts)
        return self.min_wait + random.random() * min(self.diff, 2**attempt)

    def reset(self, *args):
        self.attempts = itertools.count(*args)


def find_json_list(text):
    r"""
    >>> find_json_list('["foo",\n\t"bar"]')
    ['foo', 'bar']
    >>> find_json_list('{"abc": ["123"]}')
    ['123']
    >>> find_json_list('{"abc": null}')
    Traceback (most recent call last):
    ...
    ValueError: ...
    >>> find_json_list('some text string')
    Traceback (most recent call last):
    ...
    ValueError: ...
    """
    l_bracket = text.find("[")
    r_bracket = text.rfind("]")

    if l_bracket == -1 or r_bracket == -1:
        raise ValueError("No list found", text)

    return json.loads(text[l_bracket : r_bracket + 1])


class SocketIO:
    """Class for using websockets to talk to a SocketIO server."""

    codes = BijectiveMap(
        connect=0,
        disconnect=1,
        event=2,
        error=4,
    )

    # After this many consecutive failed connect cycles, dispatch a
    # `persistent_disconnect` event so the outer integration can surface a
    # warning. With max backoff 30s and min 5s, 20 attempts is ~3.3 to
    # ~10 minutes of attempts depending on jitter.
    PERSISTENT_DISCONNECT_THRESHOLD = 20

    def __init__(self, url, cookie=None, origin=None):
        params = dict(EIO=3, transport="websocket")
        self._url = url + "?" + urllib.parse.urlencode(params)

        self._cookie = cookie
        self._origin = origin

        self._task: asyncio.Task | None = None
        self._websocket: AbodeWebSocket | None = None
        # Create the exit event up front so stop() can signal the task even
        # during the early cookie-wait phase (before the websocket is built).
        # asyncio.Event() is loop-agnostic since Python 3.10; construction
        # outside a running loop is safe — the event is used only when _run()
        # is awaited inside a task on a real event loop.
        self._exit_event = asyncio.Event()
        self._running = False

        self._websocket_connected = False
        self._engineio_connected = False
        self._socketio_connected = False

        self._last_ping_time = datetime.datetime.min.replace(tzinfo=datetime.UTC)
        self._last_packet_time = datetime.datetime.min.replace(tzinfo=datetime.UTC)
        # Defensive defaults; overwritten by the EngineIO `open` packet.
        self._ping_interval = datetime.timedelta(seconds=25)
        self._ping_timeout = datetime.timedelta(seconds=60)

        # Reconnect health tracking. _connect_failures increments per
        # failed iteration of _run and resets to 0 on successful websocket
        # connect. _persistent_disconnect_fired guards against re-emitting
        # the same disconnect signal repeatedly while still down.
        self._connect_failures = 0
        self._persistent_disconnect_fired = False

        self._callbacks = collections.defaultdict(list)

    @property
    def consecutive_connect_failures(self) -> int:
        return self._connect_failures

    @property
    def last_packet_age_seconds(self) -> float | None:
        if self._last_packet_time == datetime.datetime.min.replace(tzinfo=datetime.UTC):
            return None
        return (
            datetime.datetime.now(tz=datetime.UTC) - self._last_packet_time
        ).total_seconds()

    def set_origin(self, origin=None):
        """Set the Origin header."""
        self._origin = origin

    def set_cookie(self, cookie=None):
        """Set the Cookie header."""
        self._cookie = cookie

    def on(self, event_name, callback):
        """Register callback for a SocketIO event."""
        log.debug("Adding callback for event name: %s", event_name)
        self._callbacks[event_name].append(callback)

    def start(self):
        """Schedule the SocketIO async task on the running event loop."""
        if self._task is not None and not self._task.done():
            return

        log.info("Starting SocketIO task...")
        # asyncio.create_task requires a running event loop. Let RuntimeError
        # propagate if called outside of one — a silent no-op on a missing loop
        # is the bug that breaks cold-start.
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Stop the SocketIO async task. Bounded by 10s timeout."""
        if self._task is None:
            return

        log.info("Stopping SocketIO task...")
        self._running = False
        self._exit_event.set()

        try:
            await asyncio.wait_for(self._task, timeout=10.0)
        except TimeoutError:
            log.warning("SocketIO task did not exit within 10s; cancelling")
            self._task.cancel()
            # Best-effort drain of the cancel; if it takes longer, give up.
            with contextlib.suppress(TimeoutError, asyncio.CancelledError):
                await asyncio.wait_for(self._task, timeout=1.0)
        finally:
            self._task = None

    async def _run(self) -> None:
        self._running = True

        intervals = BackoffIntervals()
        first_iteration = True

        while self._running:
            log.info("Attempting to connect to SocketIO server...")

            # On reconnect, drop any cookie left over from the previous cycle.
            # The wait-for-cookie poll inside _step then blocks until
            # _async_get_session() supplies a fresh one — without this the
            # SocketIO task would happily reconnect with stale cookies that
            # Abode invalidated during the disconnect window.
            if not first_iteration:
                self._cookie = None
            first_iteration = False

            try:
                await self._step(intervals)
            except SocketIOException as exc:
                log.warning("SocketIO Error: %s", exc.details)
            except AbodeWebSocketError as exc:
                log.warning("Websocket Error: %s", exc)

            if not self._running:
                break

            self._connect_failures += 1
            if (
                self._connect_failures >= self.PERSISTENT_DISCONNECT_THRESHOLD
                and not self._persistent_disconnect_fired
            ):
                log.warning(
                    "SocketIO failed to connect %d times consecutively; "
                    "signaling persistent disconnect",
                    self._connect_failures,
                )
                self._persistent_disconnect_fired = True
                await self._handle_event(
                    "persistent_disconnect", self._connect_failures
                )

            interval = next(intervals)
            log.info("Waiting %f seconds before reconnecting...", interval)
            # threading.Event.wait(timeout) returned True when set (stop) and
            # False on timeout (continue). asyncio signals timeout via exception.
            try:
                await asyncio.wait_for(self._exit_event.wait(), timeout=interval)
                # .set() was called — caller wants to stop.
                break
            except TimeoutError:
                # Interval elapsed normally; continue the outer loop.
                pass

        await self._handle_event("stopped", None)

    async def _step(self, intervals: BackoffIntervals) -> None:
        await self._handle_event("started")

        # Wait for cookies to be set by async callback; abort connect if none
        # available. Use the exit event so stop() interrupts the wait instead
        # of blocking HA shutdown for up to 15s.
        poll_interval = 0.05
        max_attempts = 300  # 15s total at 50ms polls
        attempt = 0
        while not self._cookie:
            if not self._running or self._exit_event.is_set():
                raise SocketIOException(
                    ERRORS.SOCKETIO_ERROR,
                    details="SocketIO stopped while waiting for cookies",
                )
            await asyncio.sleep(poll_interval)
            attempt += 1
            if attempt >= max_attempts:
                raise SocketIOException(
                    ERRORS.SOCKETIO_ERROR,
                    details="Timeout waiting for authentication cookies before SocketIO connect (15s)",
                )
            if attempt == 100:
                log.warning(
                    "Still waiting for authentication cookies (5s elapsed, continuing...)"
                )
            elif attempt == 200:
                log.warning(
                    "Still waiting for authentication cookies (10s elapsed, continuing...)"
                )
        log.debug(
            "Cookies obtained after %d polls, proceeding with WebSocket connection",
            attempt,
        )

        # Reset for this connection cycle and re-check _running to close the
        # window where stop() raced with the clear() and had its signal wiped.
        self._exit_event.clear()
        if not self._running:
            raise SocketIOException(
                ERRORS.SOCKETIO_ERROR,
                details="SocketIO stopped before WebSocket connect",
            )

        self._websocket = AbodeWebSocket(
            self._url, cookie=self._cookie, origin=self._origin
        )
        try:
            await self._websocket.connect()
        except AbodeWebSocketError as exc:
            raise SocketIOException(ERRORS.SOCKETIO_ERROR, details=str(exc)) from exc

        # Reset backoff here (matches today's `if isinstance(event,
        # events.Connected): intervals.reset()` inside the persist loop).
        intervals.reset()

        # Drive the full _on_websocket_connected handler — it owns the connect
        # bookkeeping (counter reset, persistent-disconnect/recovery transitions,
        # `connected` event). Do not inline a partial version.
        await self._on_websocket_connected(None)

        poll_task = asyncio.create_task(self._poll_loop())
        try:
            # _exit_event is consumed by the cookie-wait phase and cleared
            # before we reach this point.  Once inside receive(), cooperative
            # exit is no longer available; shutdown is driven by task
            # cancellation (stop() cancels after a 10s grace period) or by the
            # server closing the WebSocket.
            async for _msg_type, text in self._websocket.receive():
                await self._on_websocket_text(text)
        except AbodeWebSocketError:
            raise
        finally:
            poll_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await poll_task
            await self._websocket.close()
            await self._on_websocket_disconnected(None)

    async def _poll_loop(self) -> None:
        """Runs alongside receive() to emit poll events on a 5s cadence."""
        while True:
            await asyncio.sleep(5.0)
            await self._on_websocket_poll(None)

    async def _on_websocket_connected(self, _event: Any) -> None:
        self._websocket_connected = True
        log.info("Websocket Connected")
        # A successful connect clears the persistent-disconnect bookkeeping.
        # If we'd previously emitted persistent_disconnect, also fire a
        # recovery event so listeners can clear their warning state.
        self._connect_failures = 0
        if self._persistent_disconnect_fired:
            self._persistent_disconnect_fired = False
            await self._handle_event("connection_recovered")
        await self._handle_event("connected")

    async def _on_websocket_disconnected(self, _event: Any) -> None:
        self._websocket_connected = False
        self._engineio_connected = False
        self._socketio_connected = False

        log.info("Websocket Disconnected")
        await self._handle_event("disconnected")

    async def _on_websocket_poll(self, _event: Any) -> None:
        ws = self._websocket
        if ws is None:
            return
        last_packet_delta = (
            datetime.datetime.now(tz=datetime.UTC) - self._last_packet_time
        )

        if self._engineio_connected and last_packet_delta > self._ping_timeout:
            log.warning("SocketIO Server Ping Timeout")
            await ws.close()
            return

        last_ping_delta = datetime.datetime.now(tz=datetime.UTC) - self._last_ping_time

        if self._engineio_connected and last_ping_delta >= self._ping_interval:
            await ws.send_text(str(EngineIO.codes["ping"]))
            self._last_ping_time = datetime.datetime.now(tz=datetime.UTC)
            log.debug("Client Ping")
            await self._handle_event("ping")

        await self._handle_event("poll")

    async def _on_websocket_text(self, text: str) -> None:
        if not text:
            return
        self._last_packet_time = datetime.datetime.now(tz=datetime.UTC)

        log.debug("Received: %s", text)

        try:
            code = int(text[:1])
        except ValueError:
            log.debug("Ignoring malformed EngineIO packet: %s", text[:20])
            return
        message = text[1:]

        try:
            name = EngineIO.codes[code]
            handler = getattr(self, f"_on_engineio_{name}")
            await handler(message)
        except KeyError:
            log.debug("Ignoring unrecognized EngineIO packet")

    async def _on_engineio_open(self, message: str) -> None:
        packet = json.loads(message)

        self._ping_interval = datetime.timedelta(milliseconds=packet["pingInterval"])
        log.debug("Set ping interval to %s", self._ping_interval)

        self._ping_timeout = datetime.timedelta(milliseconds=packet["pingTimeout"])
        log.debug("Set ping timeout to %s", self._ping_timeout)

        self._engineio_connected = True
        log.debug("EngineIO Connected")

    async def _on_engineio_close(self, _message: str) -> None:
        self._engineio_connected = False
        log.debug("EngineIO Disconnected")
        if self._websocket is not None:
            await self._websocket.close()

    async def _on_engineio_pong(self, _message: str) -> None:
        log.debug("Server Pong")
        await self._handle_event("pong")

    async def _on_engineio_message(self, message: str) -> None:
        try:
            code = int(message[:1])
        except ValueError:
            log.debug("Ignoring malformed SocketIO message: %s", message[:20])
            return
        data = message[1:]

        try:
            name = SocketIO.codes[code]
            handler = getattr(self, f"_on_socketio_{name}")
            await handler(data)
        except KeyError:
            log.debug("Ignoring SocketIO message: %s", message)

    async def _on_socketio_connected(self, _data: str = "") -> None:
        self._socketio_connected = True
        log.debug("SocketIO Connected")

    async def _on_socketio_disconnected(self, _data: str = "") -> None:
        self._socketio_connected = False
        log.debug("SocketIO Disconnected")
        if self._websocket is not None:
            await self._websocket.close()

    async def _on_socketio_error(self, _message_data: str) -> None:
        await self._handle_event("error", _message_data)
        raise SocketIOException(ERRORS.SOCKETIO_ERROR, details=_message_data)

    async def _on_socketio_event(self, _message_data: str) -> None:
        try:
            json_data = find_json_list(_message_data)
        except ValueError:
            log.warning("Unable to find event [data]: %s", _message_data)
            return
        await self._handle_event("event", _message_data)
        await self._handle_event(json_data[0], json_data[1:])

    async def _handle_event(self, event_name: str, *args: Any) -> None:
        for callback in self._callbacks[event_name]:
            try:
                if inspect.iscoroutinefunction(callback):
                    await callback(*args)
                else:
                    callback(*args)
            except Exception as exc:
                log.exception(
                    "Captured exception during SocketIO event callback: %s", exc
                )
