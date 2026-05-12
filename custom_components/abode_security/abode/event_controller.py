"""Abode cloud push events."""

import asyncio
import collections
import concurrent.futures
import contextlib
import logging
import os
import threading

from . import socketio as sio
from ._itertools import always_iterable, opt_single, single
from .devices.alarm import Alarm
from .devices.base import Device
from .exceptions import Exception as AbodeException
from .helpers import errors, timeline, urls

log = logging.getLogger(__name__)


def _get_socketio_url():
    """
    Get Socket.IO URL derived from base URL.

    Production: wss://my.goabode.com/socket.io/
    Development: ws://mock-abode:8000/socket.io/

    Derives from ABODE_BASE_URL environment variable or uses production default.
    """
    base = os.environ.get('ABODE_BASE_URL', 'https://my.goabode.com')

    # Convert http(s) to ws(s)
    if base.startswith('https://'):
        ws_url = base.replace('https://', 'wss://')
    elif base.startswith('http://'):
        ws_url = base.replace('http://', 'ws://')
    else:
        # Assume it's a host without protocol, default to wss
        ws_url = f'wss://{base}'

    return f"{ws_url.rstrip('/')}/socket.io/"


SOCKETIO_URL = _get_socketio_url()


def _cookie_string(cookies):
    """Convert cookies to string format.

    Args:
        cookies: CookieJar or cookie-like object

    Returns:
        str: Cookie string in 'name=value; name=value' format
    """
    if not hasattr(cookies, "__iter__"):
        return ""
    try:
        return "; ".join(f"{cookie.name}={cookie.value}" for cookie in cookies)
    except (AttributeError, TypeError):
        return ""


class EventController:
    """Subscribes to events."""

    # Configuration constants for callback execution
    DEFAULT_CALLBACK_TIMEOUT = 10  # seconds for normal callbacks
    LONG_OPERATION_TIMEOUT = 30  # seconds for setup/initialization callbacks

    def __init__(self, client, url=None):
        if url is None:
            url = _get_socketio_url()
        self._client = client
        self._running = False
        self._connected = False

        # Thread synchronization lock for callback collections
        # This ensures thread-safe access from SocketIO thread and main thread
        self._callback_lock = threading.RLock()
        # Thread synchronization lock for connection state
        # Protects _connected flag from race conditions between SocketIO and HA threads
        self._connection_lock = threading.Lock()

        # Setup callback dicts
        self._connection_status_callbacks = collections.defaultdict(list)
        self._device_callbacks = collections.defaultdict(list)
        self._event_callbacks = collections.defaultdict(list)
        self._timeline_callbacks = collections.defaultdict(list)

        # Event loop reference for scheduling callbacks
        self._event_loop = None

        # Tracks whether we've handled the very first `started` event. The
        # synchronous cookie seed is only useful on the first call — on
        # reconnect the in-memory cookie_jar may be stale and we rely on
        # _async_get_session() to refresh it.
        self._initial_seed_done = False

        # In-flight `concurrent.futures.Future` handles returned by
        # `asyncio.run_coroutine_threadsafe()` from SocketIO-thread callbacks.
        # Tracked so `stop()` can cancel them — otherwise the asyncio Task
        # they wrap stays pending past teardown and trips pytest-HA-cc's
        # `verify_cleanup` lingering-task assertion (see #105).
        self._inflight_lock = threading.Lock()
        self._inflight_futures: set[concurrent.futures.Future] = set()

        # Setup SocketIO
        self._socketio = sio.SocketIO(url=url, origin=urls.BASE)

        # Setup SocketIO Callbacks
        self._socketio.on("started", self._on_socket_started)
        self._socketio.on("connected", self._on_socket_connected)
        self._socketio.on("disconnected", self._on_socket_disconnected)
        self._socketio.on("persistent_disconnect", self._on_persistent_disconnect)
        self._socketio.on("connection_recovered", self._on_connection_recovered)
        self._socketio.on("com.goabode.device.update", self._on_device_update)
        self._socketio.on("com.goabode.gateway.mode", self._on_mode_change)
        self._socketio.on("com.goabode.gateway.timeline", self._on_timeline_update)
        self._socketio.on("com.goabode.automation", self._on_automation_update)

    def start(self):
        """Schedule the SocketIO async task for Abode notifications."""
        self._socketio.start()

    async def stop(self) -> None:
        """Stop the SocketIO task and cancel any in-flight coroutines."""
        await self._socketio.stop()
        with self._inflight_lock:
            futures = list(self._inflight_futures)
        for future in futures:
            future.cancel()

    def _track_inflight(self, future):
        """Register a `run_coroutine_threadsafe` future for shutdown tracking."""
        with self._inflight_lock:
            self._inflight_futures.add(future)
        future.add_done_callback(self._discard_inflight)
        return future

    def _discard_inflight(self, future):
        """Remove a completed future from the in-flight set."""
        with self._inflight_lock:
            self._inflight_futures.discard(future)

    def add_connection_status_callback(self, unique_id, callback):
        """Register callback for Abode server connection status."""
        if not unique_id:
            return False

        log.debug("Subscribing to Abode connection updates for: %s", unique_id)

        with self._callback_lock:
            self._connection_status_callbacks[unique_id].append(callback)

        return True

    def remove_connection_status_callback(self, unique_id):
        """Unregister connection status callbacks."""
        if not unique_id:
            return False

        log.debug("Unsubscribing from Abode connection updates for : %s", unique_id)

        with self._callback_lock:
            self._connection_status_callbacks[unique_id].clear()

        return True

    def add_device_callback(self, devices, callback):
        """Register a device callback."""
        if not devices:
            return False

        with self._callback_lock:
            for device in always_iterable(devices):
                # Device may be a device_id
                device_id = device

                # If they gave us an actual device, get that devices ID
                if isinstance(device, Device):
                    device_id = device.id

                # Validate the device is valid
                if not self._client.get_device(device_id):
                    raise AbodeException(errors.EVENT_DEVICE_INVALID)

                log.debug("Subscribing to updates for device_id: %s", device_id)

                self._device_callbacks[device_id].append(callback)

        return True

    def remove_all_device_callbacks(self, devices):
        """Unregister all callbacks for a device."""
        if not devices:
            return False

        with self._callback_lock:
            for device in always_iterable(devices):
                device_id = device

                if isinstance(device, Device):
                    device_id = device.id

                if not self._client.get_device(device_id):
                    raise AbodeException(errors.EVENT_DEVICE_INVALID)

                if device_id not in self._device_callbacks:
                    return False

                log.debug("Unsubscribing from all updates for device_id: %s", device_id)

                self._device_callbacks[device_id].clear()

        return True

    def add_event_callback(self, event_groups, callback):
        """Register callback for a group of timeline events."""
        if not event_groups:
            return False

        with self._callback_lock:
            for event_group in always_iterable(event_groups):
                if event_group not in timeline.Groups.ALL:
                    raise AbodeException(errors.EVENT_GROUP_INVALID)

                log.debug("Subscribing to event group: %s", event_group)

                self._event_callbacks[event_group].append(callback)

        return True

    def remove_event_callback(self, event_groups, callback):
        """Unregister callback for a group of timeline events."""
        if not event_groups:
            return False

        with self._callback_lock:
            for event_group in always_iterable(event_groups):
                if event_group not in timeline.Groups.ALL:
                    raise AbodeException(errors.EVENT_GROUP_INVALID)

                log.debug("Unsubscribing from event group: %s", event_group)

                with contextlib.suppress(ValueError):
                    self._event_callbacks[event_group].remove(callback)

        return True

    def add_timeline_callback(self, timeline_events, callback):
        """Register a callback for a specific timeline event."""
        if not timeline_events:
            return False

        if isinstance(timeline_events, dict):
            timeline_events = [timeline_events]

        with self._callback_lock:
            for timeline_event in always_iterable(timeline_events):
                if not isinstance(timeline_event, dict):
                    raise AbodeException(errors.EVENT_CODE_MISSING)

                event_code = timeline_event.get("event_code")

                if not event_code:
                    raise AbodeException(errors.EVENT_CODE_MISSING)

                log.debug("Subscribing to timeline event: %s", timeline_event)

                self._timeline_callbacks[event_code].append(callback)

        return True

    @property
    def connected(self):
        """Get the Abode connection status."""
        with self._connection_lock:
            return self._connected

    @property
    def socketio(self):
        """Get the SocketIO instance."""
        return self._socketio

    def set_event_loop(self, loop):
        """Set the event loop reference for scheduling callbacks.

        Called by Home Assistant integration to provide the running event loop.
        This allows callbacks to be safely scheduled from the SocketIO thread.
        """
        self._event_loop = loop

    def _on_socket_started(self):
        """Socket IO startup callback."""
        # Validate event loop before attempting to use it
        if not self._event_loop:
            log.error(
                "Event loop not set before SocketIO startup - "
                "callbacks will not work properly. "
                "Call set_event_loop() before starting SocketIO."
            )
            return

        if not self._event_loop.is_running():
            log.error(
                "Event loop not running when SocketIO started - "
                "callbacks may not execute properly"
            )
            return

        # Seed cookies from the current session only on the very first
        # `started` event. On reconnect we must NOT pre-set the cookie:
        # SocketIO clears self._cookie between iterations, and the wait
        # loop in _step relies on that to block until _async_get_session()
        # completes with fresh cookies. Seeding from a possibly-stale
        # cookie_jar would defeat that wait and reconnect with bad auth.
        if not self._initial_seed_done:
            self._initial_seed_done = True
            try:
                session = getattr(self._client, "_session", None)
                if session is None:
                    log.warning(
                        "SocketIO started before HTTP session was initialized; "
                        "proceeding without seed cookies (will fetch via _async_get_session)"
                    )
                else:
                    cookie_str = _cookie_string(session.cookie_jar)
                    if cookie_str:
                        self._socketio.set_cookie(cookie_str)
                        log.debug("Seeded SocketIO cookies from existing session")
            except Exception as exc:
                log.debug("Unable to seed cookies from existing session: %s", exc)
        else:
            log.debug(
                "Skipping cookie seed on reconnect; relying on _async_get_session "
                "to refresh"
            )

        try:
            future = self._track_inflight(
                asyncio.run_coroutine_threadsafe(
                    asyncio.wait_for(
                        self._async_get_session(), timeout=self.LONG_OPERATION_TIMEOUT
                    ),
                    self._event_loop,
                )
            )
            future.add_done_callback(self._on_session_init_done)
        except Exception as exc:
            log.error("Failed to schedule session initialization: %s", exc)

    def _on_session_init_done(self, future):
        """Callback when session initialization completes."""
        try:
            future.result()
            log.debug("Session initialized successfully")
        except TimeoutError:
            log.error("Session initialization timed out")
        except concurrent.futures.CancelledError:
            # Only reachable via stop()'s cancel-on-shutdown path, so this
            # is expected. TimeoutError above is a real 30s expiry and stays
            # at error level.
            log.debug("Session initialization cancelled (shutdown in progress)")
        except Exception as exc:
            log.warning("Session initialization failed: %s", exc)

    async def _async_get_session(self):
        """Get session asynchronously."""
        log.debug("Attempting to fetch session cookies for SocketIO authentication")
        try:
            session = await self._client._get_session()
            # Set cookies from session
            if hasattr(session, "cookie_jar"):
                cookie_str = ""
                try:
                    cookies = session.cookie_jar.filter_cookies(urls.BASE)
                    cookie_str = "; ".join(
                        f"{name}={morsel.value}" for name, morsel in cookies.items()
                    )
                    if cookie_str:
                        log.debug("Session cookies found: %d cookie(s)", len(cookies))
                except Exception as exc:
                    log.debug("Cookie parsing fallback due to: %s", exc)
                    try:
                        cookie_str = "; ".join(
                            f"{getattr(c, 'key', getattr(c, 'name', ''))}={getattr(c, 'value', '')}"
                            for c in session.cookie_jar
                        )
                    except Exception as inner_exc:
                        log.warning("Failed to build cookie string: %s", inner_exc)
                        cookie_str = ""

                if cookie_str:
                    log.debug(
                        "Setting cookie for SocketIO connection (length: %d)",
                        len(cookie_str),
                    )
                    self._socketio.set_cookie(cookie_str)
                else:
                    log.warning(
                        "No cookies found in session, SocketIO connection may fail"
                    )
        except Exception as exc:
            log.warning("Failed to get session: %s", exc)

    def _on_socket_connected(self):
        """Socket IO connected callback."""
        with self._connection_lock:
            self._connected = True
        with contextlib.suppress(Exception):
            self._client._set_connection_status("connected")

        # Schedule async refresh on the event loop
        if self._event_loop and self._event_loop.is_running():
            try:
                future = self._track_inflight(
                    asyncio.run_coroutine_threadsafe(
                        asyncio.wait_for(
                            self._async_refresh(), timeout=self.LONG_OPERATION_TIMEOUT
                        ),
                        self._event_loop,
                    )
                )
                future.add_done_callback(self._on_refresh_done)
            except Exception as exc:
                log.error("Failed to schedule Abode refresh: %s", exc)
        else:
            log.warning("Event loop not running, cannot refresh Abode on connect")

        # Execute connection status callbacks
        # Use thread-safe callback execution
        self._execute_connection_callbacks()

    def _on_refresh_done(self, future):
        """Callback when refresh completes."""
        try:
            future.result()
            log.debug("Abode refresh completed successfully")
        except TimeoutError:
            log.error("Abode refresh timed out")
        except concurrent.futures.CancelledError:
            log.debug("Abode refresh cancelled (shutdown in progress)")
        except Exception as exc:
            log.warning("Abode refresh failed: %s", exc)

    async def _async_refresh(self):
        """Async refresh of devices and automations."""
        try:
            await self._client.refresh()
        except Exception as exc:
            log.warning("Captured exception during Abode refresh: %s", exc)

    def _on_socket_disconnected(self):
        """Socket IO disconnected callback."""
        with self._connection_lock:
            self._connected = False
        with contextlib.suppress(Exception):
            self._client._set_connection_status("disconnected")
        self._execute_connection_callbacks()

    def _on_persistent_disconnect(self, attempts):
        """SocketIO failed to reconnect for an extended period.

        Surface this to the client so diagnostics and the HA UI can show that
        the integration is stuck rather than silently retrying forever.
        """
        log.warning(
            "Abode SocketIO persistently disconnected after %d failed attempts; "
            "integration may be stuck",
            attempts,
        )
        with self._connection_lock:
            self._connected = False
        with contextlib.suppress(Exception):
            self._client._set_connection_status(
                "persistent_disconnect",
                f"SocketIO failed to reconnect after {attempts} attempts",
            )
        self._execute_connection_callbacks()

    def _on_connection_recovered(self):
        """SocketIO reconnected after a previously-emitted persistent disconnect."""
        log.info("Abode SocketIO reconnected after persistent disconnect")
        with self._connection_lock:
            self._connected = True
        with contextlib.suppress(Exception):
            self._client._set_connection_status("connected")
        self._execute_connection_callbacks()

    def _execute_connection_callbacks(self):
        """Execute all connection status callbacks safely with thread protection."""
        with self._callback_lock:
            # Make a defensive copy of callbacks to avoid issues if callbacks
            # are modified during iteration
            callbacks_to_execute = []
            for callbacks in self._connection_status_callbacks.values():
                callbacks_to_execute.extend(callbacks)

        # Execute callbacks outside the lock
        for callback in callbacks_to_execute:
            _execute_callback(callback, self._event_loop)

    def _on_device_update(self, devid):
        """Device callback from Abode SocketIO server."""
        devid = opt_single(devid)

        if devid is None:
            log.warning("Device update with no device id.")
            return

        log.debug("Device update event for device ID: %s", devid)

        # If we have an event loop, refresh device state asynchronously before dispatching
        if self._event_loop and self._event_loop.is_running():
            try:
                future = self._track_inflight(
                    asyncio.run_coroutine_threadsafe(
                        asyncio.wait_for(
                            self._async_refresh_device_and_dispatch(devid),
                            timeout=self.LONG_OPERATION_TIMEOUT,
                        ),
                        self._event_loop,
                    )
                )
                future.add_done_callback(
                    lambda f: self._log_future_result(
                        f, "_async_refresh_device_and_dispatch"
                    )
                )
            except Exception as exc:
                log.error("Failed to schedule device refresh for %s: %s", devid, exc)
            return

        device = self._client.get_device(devid, True)

        if not device:
            log.debug("Got device update for unknown device: %s", devid)
            return

        # Make defensive copy of callbacks under lock
        with self._callback_lock:
            callbacks = list(self._device_callbacks[device.id])

        # Execute callbacks outside lock
        for callback in callbacks:
            _execute_callback(callback, self._event_loop, device)

    async def _async_refresh_device_and_dispatch(self, device_id):
        """Refresh device state from Abode and dispatch callbacks on the HA loop."""
        try:
            await self._client.get_devices(refresh=True)
        except Exception as exc:
            log.warning(
                "Failed to refresh devices after update for %s: %s", device_id, exc
            )

        device = self._client.get_device(device_id, False)

        if not device:
            log.debug(
                "Got device update for unknown device after refresh: %s", device_id
            )
            return

        with self._callback_lock:
            callbacks = list(self._device_callbacks[device.id])

        for callback in callbacks:
            _execute_callback(callback, self._event_loop, device)

    @staticmethod
    def _log_future_result(future, label):
        with contextlib.suppress(Exception):
            future.result()
        if future.cancelled():
            log.warning("%s was cancelled", label)
        elif future.exception():
            log.warning("%s raised: %s", label, future.exception())

    def _on_mode_change(self, mode):
        """Mode change broadcast from Abode SocketIO server."""
        mode = opt_single(mode)

        if mode is None:
            log.warning("Mode change event with no mode.")
            return

        if not mode or mode.lower() not in Alarm.all_modes:
            log.warning("Mode change event with unknown mode: %s", mode)
            return

        log.debug("Alarm mode change event to: %s", mode)

        # We're just going to convert it to an Alarm device
        alarm_device = self._client.get_alarm(refresh=True)

        # At the time of development, refreshing after mode change notification
        # didn't seem to get the latest update immediately. As such, we will
        # force the mode status now to match the notification.
        alarm_device._state["mode"]["area_1"] = mode

        # Make defensive copy of callbacks under lock
        with self._callback_lock:
            callbacks = list(self._device_callbacks[alarm_device.id])

        # Execute callbacks outside lock
        for callback in callbacks:
            _execute_callback(callback, self._event_loop, alarm_device)

    def _on_timeline_update(self, event):
        """Timeline update broadcast from Abode SocketIO server."""
        event = single(event)

        event_type = event.get("event_type")
        event_code = event.get("event_code")

        if not event_type or not event_code:
            log.warning("Invalid timeline update event: %s", event)
            return

        log.debug(
            "Timeline event received: %s - %s (%s)",
            event.get("event_name"),
            event_type,
            event_code,
        )

        # Gather callbacks under lock
        with self._callback_lock:
            # Compress our callbacks into those that match this event_code
            # or ones registered to get callbacks for all events
            codes = (event_code, timeline.ALL["event_code"])
            callbacks_to_execute = []
            for code in codes:
                callbacks_to_execute.extend(self._timeline_callbacks[code])

            # Attempt to map the event code to a group and callback
            event_group = timeline.map_event_code(event_code)
            callbacks_to_execute.extend(self._event_callbacks[event_group])

        # Execute callbacks outside lock
        for callback in callbacks_to_execute:
            _execute_callback(callback, self._event_loop, event)

    def _on_automation_update(self, event):
        """Automation update broadcast from Abode SocketIO server."""
        event_group = timeline.Groups.AUTOMATION_EDIT
        event = single(event)

        # Gather callbacks under lock
        with self._callback_lock:
            callbacks = list(self._event_callbacks[event_group])

        # Execute callbacks outside lock
        for callback in callbacks:
            _execute_callback(callback, self._event_loop, event)


def _execute_callback(callback, *args, **kwargs):
    """Execute a callback, handling both sync and async Home Assistant methods.

    Args:
        callback: The callback function to execute
        *args: Arguments to pass to callback (first may be event_loop for HA methods)
        **kwargs: Keyword arguments to pass to callback

    For Home Assistant entity methods like schedule_update_ha_state(), we need to
    ensure they're called on the event loop thread, not from the SocketIO thread.

    This function does NOT block the SocketIO thread. Async callbacks are scheduled
    and the function returns immediately.
    """
    # Check if first positional arg is an event loop
    event_loop = None
    callback_args = args
    if args and isinstance(args[0], asyncio.AbstractEventLoop):
        event_loop = args[0]
        callback_args = args[1:]

    try:
        # If callback is a method from Home Assistant entity, schedule it on event loop
        # This handles methods like schedule_update_ha_state()
        if event_loop and hasattr(callback, "__self__"):
            # This is a bound method - likely from Home Assistant entity
            # Schedule it on the event loop to ensure thread safety
            future = asyncio.run_coroutine_threadsafe(
                _run_callback_async(callback, callback_args, kwargs),
                event_loop,
            )
            future.add_done_callback(lambda f: _log_callback_completion(callback, f))
        else:
            # Regular sync callback - safe to call directly
            callback(*callback_args, **kwargs)
    except Exception as exc:
        log.error("Failed to execute callback: %s: %s", callback, exc)


def _log_callback_completion(callback, future):
    """Log callback completion or errors, called from event loop thread."""
    try:
        future.result()
        log.debug("Callback completed successfully: %s", callback)
    except TimeoutError:
        log.error("Callback execution timed out: %s", callback)
    except Exception as exc:
        log.error("Callback execution failed: %s: %s", callback, exc)


async def _run_callback_async(callback, args, kwargs):
    """Helper to run a callback that might be sync or async.

    Wraps callback execution with a reasonable timeout to prevent hanging.
    """
    # Determine timeout based on callback characteristics
    timeout = EventController.DEFAULT_CALLBACK_TIMEOUT
    if hasattr(callback, "__name__") and "setup" in callback.__name__.lower():
        timeout = EventController.LONG_OPERATION_TIMEOUT

    try:
        async with asyncio.timeout(timeout):
            if asyncio.iscoroutinefunction(callback):
                await callback(*args, **kwargs)
            else:
                callback(*args, **kwargs)
    except TimeoutError:
        log.error(
            "Callback '%s' timed out after %d seconds",
            getattr(callback, "__name__", str(callback)),
            timeout,
        )
        raise
    except Exception as exc:
        log.error("Callback '%s' raised exception: %s", callback, exc)
        raise
