"""
An Abode alarm Python library.
"""

import asyncio
import json as json_module
import logging
import uuid
from datetime import datetime, timedelta

import aiohttp

from . import settings
from ._itertools import always_iterable
from .automation import Automation
from .devices import alarm as alarm
from .devices.base import Device, Unknown
from .event_controller import EventController
from .exceptions import AuthenticationException, Exception, RateLimitException
from .helpers import errors, urls

log = logging.getLogger(__name__)


class Everything:
    """A set that contains everything for membership testing."""

    def __contains__(self, item):
        return True


class ResponseWrapper:
    """Wrapper to provide response-like interface with cached body."""

    def __init__(self, response_data, status, headers_dict):
        """Initialize wrapper with response data extracted from context manager.

        Args:
            response_data: Cached response body (dict, str, or bytes)
            status: HTTP status code
            headers_dict: Response headers as dict
        """
        self._body = response_data
        self._status = status
        self._headers = headers_dict

    @property
    def status(self):
        """Get response status code."""
        return self._status

    @property
    def headers(self):
        """Get response headers."""
        return self._headers

    async def json(self):
        """Return cached JSON body."""
        if isinstance(self._body, dict):
            return self._body
        if isinstance(self._body, str):
            return json_module.loads(self._body)
        # If body is already parsed, return as-is
        return self._body

    async def text(self):
        """Return cached text body."""
        if isinstance(self._body, str):
            return self._body
        if isinstance(self._body, dict):
            return json_module.dumps(self._body)
        return str(self._body)


class Client:
    """Client to an Abode system."""

    def __init__(
        self,
        username=None,
        password=None,
        auto_login=False,
        get_devices=False,
        get_automations=False,
    ):
        self._session = None
        self._token = None
        self._oauth_token = None
        self._panel = None
        self._user = None
        self._username = username
        self._password = password

        self._event_controller = EventController(self)

        self._default_alarm_mode = "away"

        self._devices = None
        self._automations = None

        self._cookies = {}

        # Connection diagnostics
        self._connection_status = "disconnected"
        self._last_error = None
        self._test_mode_supported = True
        self._cms_cache: dict[str, bool] | None = None
        self._cms_cache_time: datetime | None = None
        self._cms_lock: asyncio.Lock | None = None

        # Auth and session health tracking
        self._auth_count = 0  # Total authentications
        self._last_auth_time: datetime | None = None  # Last successful auth
        self._last_successful_request: datetime | None = (
            None  # Last successful API call
        )
        self._consecutive_failures = 0  # Track failures for session health
        self._session_recreate_count = 0  # Track session recreations
        self._session_created_time: datetime | None = None  # When session was created
        self._session_max_age_seconds = 1800  # Recreate session every 30 minutes (well before 1h 30s server timeout)

        # Background task for proactive session monitoring
        self._session_monitor_task: asyncio.Task | None = None
        self._session_monitor_running = False

        # These will be initialized during async initialization
        self._initialized = False
        self._auto_login = auto_login
        self._get_devices = get_devices
        self._get_automations = get_automations

    async def _async_initialize(self):
        """Initialize async session and perform initial login/device fetch."""
        if self._initialized:
            return

        # Create aiohttp session with cookies and timeout configuration
        timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=10)
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        self._session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        self._session_created_time = datetime.now()
        self._initialized = True

        # Start background session monitor task
        self._start_session_monitor()

        if self._auto_login:
            await self.login()

        if self._get_devices:
            await self.get_devices()

        if self._get_automations:
            await self.get_automations()

    async def __aenter__(self):
        """Async context manager entry."""
        await self._async_initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()

    async def cleanup(self):
        """Clean up async resources."""
        # Stop background session monitor
        self._stop_session_monitor()

        if self._session:
            await self._session.close()
            self._session = None
        self._initialized = False

    async def login(self, username=None, password=None, mfa_code=None):
        """Explicit Abode login."""
        await self._async_initialize()

        self._token = None

        username = username or self._username
        password = password or self._password

        if not isinstance(username, str):
            raise AuthenticationException(errors.USERNAME)

        if not isinstance(password, str):
            raise AuthenticationException(errors.PASSWORD)

        login_data = {
            "id": username,
            "password": password,
            "uuid": self._cookies.get("uuid") or str(uuid.uuid1()),
        }

        if mfa_code is not None:
            login_data["mfa_code"] = mfa_code
            login_data["remember_me"] = 1

        async with self._session.post(
            f"{urls.BASE}{urls.LOGIN}", json=login_data
        ) as response:
            await AuthenticationException.raise_for(response)
            response_object = await response.json()

        # Check for multi-factor authentication
        if "mfa_type" in response_object:
            if response_object["mfa_type"] == "google_authenticator":
                raise AuthenticationException(errors.MFA_CODE_REQUIRED)

            raise AuthenticationException(errors.UNKNOWN_MFA_TYPE)

        async with self._session.get(
            f"{urls.BASE}{urls.OAUTH_TOKEN}"
        ) as oauth_response:
            await AuthenticationException.raise_for(oauth_response)
            oauth_response_object = await oauth_response.json()

        log.debug("Login URL: %s", urls.LOGIN)
        log.debug("Login Response: %s", response_object)

        self._token = response_object["token"]
        self._panel = response_object["panel"]
        self._user = response_object["user"]
        self._oauth_token = oauth_response_object["access_token"]

        # Update cookies
        if "uuid" in login_data:
            self._cookies["uuid"] = login_data["uuid"]

        # Track authentication
        self._auth_count += 1
        self._last_auth_time = datetime.now()
        self._consecutive_failures = 0

        log.info("Login successful (auth count: %d)", self._auth_count)
        self._set_connection_status("connected")

        # Sync cookies to SocketIO after successful login
        try:
            await self._sync_socketio_cookies()
        except Exception as exc:
            log.warning("Failed to sync cookies after login: %s", exc)

    async def logout(self):
        """Explicit Abode logout."""
        if not self._token:
            return

        header_data = {"ABODE-API-KEY": self._token}

        self._token = None
        self._oauth_token = None
        self._panel = None
        self._user = None
        self._devices = None
        self._automations = None

        try:
            async with self._session.post(
                f"{urls.BASE}{urls.LOGOUT}", headers=header_data
            ) as response:
                await AuthenticationException.raise_for(response)
                log.debug("Logout URL: %s", urls.LOGOUT)
                log.debug("Logout Response: %s", await response.text())
        except (aiohttp.ClientError, OSError) as exc:
            log.warning("Caught exception during logout: %s", exc)
            return

        log.info("Logout successful")
        self._set_connection_status("disconnected")

    async def _recreate_session(self):
        """Recreate aiohttp session to clear stale connections."""
        log.info("Recreating aiohttp session due to connection issues")
        self._session_recreate_count += 1

        if self._session:
            try:
                await self._session.close()
            except Exception as exc:
                log.warning("Error closing old session: %s", exc)

        # Create fresh session
        timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=10)
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        self._session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        self._session_created_time = datetime.now()

        # Clear token to force fresh auth
        self._token = None
        self._oauth_token = None

        # Clear CMS cache to force fresh fetch after session recreation
        self._cms_cache = None
        self._cms_cache_time = None

        await self.login()

        # Sync cookies to SocketIO if available
        try:
            await self._sync_socketio_cookies()
        except Exception as exc:
            log.warning("Failed to sync cookies after session recreation: %s", exc)

    def _start_session_monitor(self):
        """Start background task to monitor session age and recreate proactively."""
        if self._session_monitor_running:
            return

        self._session_monitor_running = True
        try:
            # Get current event loop - if this fails, we can't start the monitor
            loop = asyncio.get_event_loop()
            self._session_monitor_task = loop.create_task(self._session_monitor_loop())
            log.debug("Session monitor background task started")
        except RuntimeError as exc:
            log.warning("Could not start session monitor: %s", exc)
            self._session_monitor_running = False

    async def _handle_empty_response_and_retry(
        self,
        url: str,
        context: str,
    ) -> dict | None:
        """Handle empty response by recreating session and retrying.

        When an endpoint returns an empty response, it indicates the session
        is stale. Recreate the session and retry the request with fresh auth.

        Args:
            url: The endpoint URL to retry
            context: Context string for logging (e.g., "security panel", "CMS")

        Returns:
            Parsed JSON response dict, or None if retry failed
        """
        log.warning(
            "Empty %s response detected - session likely stale, recreating session",
            context,
        )
        try:
            await self._recreate_session()
            retry_response = await self.send_request("get", url, raise_on_error=False)
            if retry_response:
                try:
                    return await retry_response.json()
                except Exception:
                    pass
        except Exception as exc:
            log.error(
                "Session recreation or %s fetch retry failed: %s", context, exc
            )
        return None

    def _stop_session_monitor(self):
        """Stop background session monitor task."""
        if not self._session_monitor_running:
            return

        self._session_monitor_running = False
        if self._session_monitor_task:
            self._session_monitor_task.cancel()
            log.debug("Session monitor background task stopped")

    async def _session_monitor_loop(self):
        """Background task that proactively recreates sessions before server timeout.

        This runs independently of API requests, so it works even when using SocketIO
        events without polling. The Abode server closes idle connections after 3630 seconds,
        so we proactively recreate the session every 1800 seconds (30 minutes).
        """
        monitor_interval = 60  # Check session age every 60 seconds

        try:
            while self._session_monitor_running:
                try:
                    await asyncio.sleep(monitor_interval)

                    if not self._session_monitor_running:
                        break

                    # Check if session is getting too old
                    if self._session_created_time:
                        session_age = (
                            datetime.now() - self._session_created_time
                        ).total_seconds()

                        if session_age > self._session_max_age_seconds:
                            log.warning(
                                "Background monitor: Session age (%d seconds) exceeds max age (%d seconds) - recreating",
                                int(session_age),
                                self._session_max_age_seconds,
                            )
                            await self._recreate_session()
                        else:
                            log.debug(
                                "Background monitor: Session age %d seconds (max %d)",
                                int(session_age),
                                self._session_max_age_seconds,
                            )

                except asyncio.CancelledError:
                    log.debug("Session monitor loop cancelled")
                    break
                except Exception as exc:
                    log.warning("Error in session monitor loop: %s", exc)
                    # Continue monitoring even if there's an error
                    await asyncio.sleep(monitor_interval)

        finally:
            log.debug("Session monitor loop exited")
            self._session_monitor_running = False

    async def refresh(self):
        """Do a full refresh of all devices and automations."""
        await self.get_devices(refresh=True)
        await self.get_automations(refresh=True)

    async def get_devices(self, refresh=False, generic_type=None):
        """Get all devices from Abode."""
        if refresh or self._devices is None:
            await self._load_devices()

        spec_types = (
            Everything() if generic_type is None else set(always_iterable(generic_type))
        )

        return [
            device
            for device in self._devices.values()
            if device.generic_type in spec_types
        ]

    async def _load_devices(self):
        if self._devices is None:
            self._devices = {}

        log.info("Updating all devices...")
        response = await self.send_request("get", urls.DEVICES)
        devices_data = await response.json()
        devices = always_iterable(devices_data)

        log.debug("Get Devices URL (get): %s", urls.DEVICES)
        log.debug("Get Devices Response: %s", devices_data)

        for device_doc in devices:
            await self._load_device(device_doc)

        # We will be treating the Abode panel itself as an armable device.
        panel_response = await self.send_request("get", urls.PANEL)
        panel_data = await panel_response.json()

        self._panel.update(panel_data)

        log.debug("Get Mode Panel URL (get): %s", urls.PANEL)
        log.debug("Get Mode Panel Response: %s", panel_data)

        alarm_device = self._devices.get(alarm.id(1))

        if alarm_device:
            alarm_device.update(self._panel)
        else:
            alarm_device = alarm.create_alarm(self._panel, self)
            self._devices[alarm_device.id] = alarm_device

    async def _load_device(self, doc):
        self._reuse_device(doc) or self._create_new_device(doc)

    def _reuse_device(self, doc):
        device = self._devices.get(doc["id"])

        if not device:
            return

        device.update(doc)
        return device

    def _create_new_device(self, doc):
        device = Device.new(doc, self)

        if isinstance(device, Unknown):
            log.debug("Skipping unknown device: %s", doc)
            return

        self._devices[device.id] = device

    def get_device(self, device_id, refresh=False):
        """Get a single device.

        Note: Devices must be loaded via await get_devices() before calling this method.
        """
        assert self._devices is not None, (
            "Devices not loaded. Call await get_devices() or await get_automations() first"
        )

        device = self._devices.get(device_id)

        if device and refresh:
            # Note: refresh would need to be async
            pass

        return device

    async def get_automations(self, refresh=False):
        """Get all automations."""
        if refresh or self._automations is None:
            await self._update_all()

        return list(self._automations.values())

    async def _update_all(self):
        if self._automations is None:
            # Set up the device libraries
            self._automations = {}

        log.info("Updating all automations...")
        resp = await self.send_request("get", urls.AUTOMATION, raise_on_error=False)
        if resp is None or resp.status == 404:
            log.info(
                "Automations endpoint unavailable (status=%s); treating as zero automations",
                getattr(resp, "status", "unknown"),
            )
            resp_data = []
        else:
            resp_data = await resp.json()
        log.debug("Get Automations URL (get): %s", urls.AUTOMATION)
        log.debug("Get Automations Response: %s", resp_data)

        for state in always_iterable(resp_data):
            # Attempt to reuse an existing automation object
            automation = self._automations.get(str(state["id"]))

            # No existing automation, create a new one
            if automation:
                automation.update(state)
            else:
                automation = Automation(state, self)
                self._automations[automation.id] = automation

    def get_automation(self, automation_id):
        """Get a single automation."""
        if self._automations is None:
            # Note: Must be loaded async first
            return None

        automation = self._automations.get(str(automation_id))

        return automation

    def get_alarm(self, area="1", refresh=False):
        """Shortcut method to get the alarm device."""
        return self.get_device(alarm.id(area), refresh)

    def set_default_mode(self, default_mode):
        """Set the default mode when alarms are turned 'on'."""
        if default_mode.lower() not in ("away", "home"):
            raise Exception(errors.INVALID_DEFAULT_ALARM_MODE)

        self._default_alarm_mode = default_mode.lower()

    async def set_setting(self, name, value, area="1"):
        """Set an abode system setting to a given value."""
        setting = settings.Setting.load(name.lower(), value, area)
        return await self.send_request(
            method="put", path=setting.path, data=setting.data
        )

    async def acknowledge_timeline_event(self, timeline_id):
        """Acknowledge/verify a timeline alarm event."""
        return await self._process_timeline_event(
            timeline_id,
            urls.timeline_verify_alarm,
            "acknowledged",
        )

    async def dismiss_timeline_event(self, timeline_id):
        """Dismiss/ignore a timeline alarm event."""
        return await self._process_timeline_event(
            timeline_id,
            urls.timeline_ignore_alarm,
            "dismissed",
        )

    async def _process_timeline_event(self, timeline_id, url_func, action):
        """Process a timeline event (acknowledge or dismiss).

        Args:
            timeline_id: ID of the timeline event to process
            url_func: Function to generate the URL (e.g., urls.timeline_verify_alarm)
            action: Action description for logging ('acknowledged' or 'dismissed')

        Returns:
            True if successful, raises exception otherwise
        """
        if not timeline_id:
            raise Exception(errors.MISSING_TIMELINE_ID)

        timeline_id = str(timeline_id)
        url = url_func(timeline_id)

        response = await self._send_request("post", url, raise_on_error=False)

        if response is None:
            raise Exception(errors.REQUEST)

        log.debug("Timeline Event URL (post): %s", url)
        log.debug("Timeline Event Response: %s", await response.text())

        # Check if request was successful
        if response.status < 400:
            response_object = await response.json()

            if not all(key in response_object for key in ("code", "message", "tid")):
                raise Exception(errors.ACK_TIMELINE_RESPONSE)

            if str(response_object.get("tid")) != timeline_id:
                raise Exception(errors.ACK_TIMELINE_RESPONSE)

            log.info("Timeline event %s %s", timeline_id, action)
            return True

        # Handle error responses
        try:
            error_response = await response.json()
            error_code = error_response.get("errorCode")
            error_message = error_response.get("message", "Unknown error")

            if error_code == errors.TIMELINE_EVENT_ALREADY_PROCESSED:
                log.info(
                    "Timeline event %s already %s: %s",
                    timeline_id,
                    action,
                    error_message,
                )
                return True

            log.error(
                "Failed to %s timeline event %s (code %s): %s",
                action.rstrip("ed"),
                timeline_id,
                error_code,
                error_message,
            )
            raise Exception(errors.REQUEST)
        except (ValueError, KeyError):
            log.error(
                "Failed to %s timeline event %s: unexpected response format",
                action.rstrip("ed"),
                timeline_id,
            )
            raise Exception(errors.REQUEST)

    async def get_timeline_events(self, size=10):
        """Fetch recent timeline events.

        Args:
            size (int): Number of recent events to fetch (default 10)

        Returns:
            list: List of timeline event dictionaries
        """
        response = await self.send_request("get", f"{urls.TIMELINE}?size={size}")

        log.debug("Get Timeline Events URL (get): %s", urls.TIMELINE)

        timeline_events = await response.json()

        log.debug("Get Timeline Events Response: %s", timeline_events)

        if not isinstance(timeline_events, list):
            log.warning(
                "Unexpected timeline response format: %s", type(timeline_events)
            )
            return []

        log.info("Fetched %d recent timeline events", len(timeline_events))
        return timeline_events

    async def get_test_mode(self):
        """Get the current test mode status using unified CMS settings fetch.

        Uses get_cms_settings() to avoid code duplication and ensure consistent
        caching behavior across all CMS setting reads.
        """
        if not self._test_mode_supported:
            raise Exception(errors.REQUEST)

        try:
            cms_settings = await self.get_cms_settings()
            test_mode_active = cms_settings.get("testModeActive", False)
            log.info(
                "Test mode is currently: %s",
                "enabled" if test_mode_active else "disabled",
            )
            return bool(test_mode_active)
        except Exception:
            # If CMS settings unavailable, disable test mode support
            log.info("Test mode endpoint unavailable; disabling test mode support")
            self._test_mode_supported = False
            return False

    async def set_test_mode(self, enabled):
        """Set the test mode for the monitoring service.

        When enabled, any triggered alarms will not be dispatched to monitoring service.
        Test mode automatically turns off after 30 minutes.

        Args:
            enabled: Boolean, True to enable test mode, False to disable

        Returns:
            Dict with the updated CMS settings
        """
        if not isinstance(enabled, bool):
            raise Exception(errors.INVALID_TEST_MODE_VALUE)

        try:
            response_object = await self.set_cms_setting("testModeActive", enabled)
            log.info("Test mode set to: %s", "enabled" if enabled else "disabled")
            return response_object
        except Exception as err:
            # If the error is specifically about test mode, wrap it appropriately
            if "testModeActive" in str(err):
                raise Exception(errors.SET_TEST_MODE_RESPONSE)
            raise

    async def get_cms_settings(self, ttl_seconds: int | None = 300):
        """Get all CMS settings from the panel.

        Returns a dictionary with all available CMS settings:
        - monitoringActive
        - testModeActive
        - sendMedia
        - dispatchWithoutVerification
        - dispatchPolice
        - dispatchFire
        - dispatchMedical
        """
        # Lazily initialize a lock to dedupe concurrent fetches
        if self._cms_lock is None:
            self._cms_lock = asyncio.Lock()

        async with self._cms_lock:
            ttl = ttl_seconds or 300
            # Return cached CMS if fresh to avoid hammering Abode
            if self._cms_cache and self._cms_cache_time:
                age = (datetime.now() - self._cms_cache_time).total_seconds()
                if age < ttl:
                    log.debug("Using cached CMS settings (age=%.1fs)", age)
                    return self._cms_cache

            combined: dict[str, bool] = {}

            # Cached panel CMS values (may be incomplete)
            if isinstance(self._panel, dict):
                panel_cms = self._panel.get("attributes", {}).get("cms", {})
                panel_norm = self._normalize_cms_settings(panel_cms)
                log.debug("CMS settings (panel cache): %s", panel_norm)
                combined.update(panel_norm)

            # Primary: dedicated CMS settings endpoint
            cms_resp = await self._fetch_cms_settings()
            cms_norm = self._normalize_cms_settings(cms_resp)
            log.debug("CMS settings (cms/settings): %s", cms_norm)
            combined.update(cms_norm)

            # Secondary: SECURITY_PANEL endpoint (fallback)
            sec_panel = await self._fetch_cms_from_security_panel()
            if sec_panel:
                sec_norm = self._normalize_cms_settings(sec_panel)
                log.debug("CMS settings (security-panel): %s", sec_norm)
                for key, value in sec_norm.items():
                    combined.setdefault(key, value)

            log.info("CMS settings (combined): %s", combined)
            self._cms_cache = combined
            self._cms_cache_time = datetime.now()
            return combined

    async def _fetch_cms_from_security_panel(self):
        response = await self.send_request(
            "get", urls.SECURITY_PANEL, raise_on_error=False
        )
        if response is None or response.status == 404:
            log.debug(
                "CMS settings endpoint unavailable (status=%s)",
                getattr(response, "status", "unknown"),
            )
            return {}

        try:
            response_data = await response.json()
        except Exception as exc:
            raw_text = await response.text()
            log.warning(
                "Security panel response not JSON (status=%s): %s (exc=%s)",
                getattr(response, "status", "unknown"),
                raw_text[:100] if raw_text else "<empty>",
                exc,
            )

            # Empty response indicates stale session - recreate entire session
            if not raw_text or raw_text.strip() == "":
                result = await self._handle_empty_response_and_retry(
                    urls.SECURITY_PANEL, "security panel"
                )
                if result is not None:
                    return result

            return {}

        log.debug("Get CMS Settings URL (get): %s", urls.SECURITY_PANEL)
        log.debug("Get CMS Settings Response (parsed): %s", response_data)

        return response_data.get("attributes", {}).get("cms", {}) or {}

    async def _fetch_cms_settings(self):
        """Fetch CMS settings from dedicated endpoint."""
        response = await self.send_request(
            "get", urls.CMS_SETTINGS, raise_on_error=False
        )
        if response is None:
            log.warning("CMS settings endpoint returned no response object")
            return {}

        status = getattr(response, "status", "unknown")
        if status == 404:
            log.warning("CMS settings endpoint unavailable (status=404)")
            return {}

        # Attempt JSON, fall back to raw text for debugging
        try:
            response_data = await response.json()
        except Exception as exc:
            raw_text = await response.text()
            log.warning(
                "CMS settings response not JSON (status=%s): %s (exc=%s)",
                status,
                raw_text[:100] if raw_text else "<empty>",
                exc,
            )

            # Empty response indicates stale session - recreate entire session
            if not raw_text or raw_text.strip() == "":
                result = await self._handle_empty_response_and_retry(
                    urls.CMS_SETTINGS, "CMS"
                )
                if result is not None:
                    return result
                return {}

        log.debug("Get CMS Settings URL (get): %s", urls.CMS_SETTINGS)
        log.debug("Get CMS Settings Response (parsed): %s", response_data)
        return response_data if isinstance(response_data, dict) else {}

    @staticmethod
    def _normalize_cms_settings(raw):
        """Normalize CMS settings keys to camelCase booleans."""
        if not isinstance(raw, dict):
            return {}

        key_map = {
            "monitoringactive": "monitoringActive",
            "monitoring_active": "monitoringActive",
            "monitoringActive": "monitoringActive",
            "testmodeactive": "testModeActive",
            "test_mode_active": "testModeActive",
            "testModeActive": "testModeActive",
            "sendmedia": "sendMedia",
            "send_media": "sendMedia",
            "sendMedia": "sendMedia",
            "dispatchwithoutverification": "dispatchWithoutVerification",
            "dispatch_without_verification": "dispatchWithoutVerification",
            "dispatchWithoutVerification": "dispatchWithoutVerification",
            "dispatchpolice": "dispatchPolice",
            "dispatch_police": "dispatchPolice",
            "dispatchPolice": "dispatchPolice",
            "dispatchfire": "dispatchFire",
            "dispatch_fire": "dispatchFire",
            "dispatchFire": "dispatchFire",
            "dispatchmedical": "dispatchMedical",
            "dispatch_medical": "dispatchMedical",
            "dispatchMedical": "dispatchMedical",
        }

        normalized = {}
        for key, value in raw.items():
            norm_key = key_map.get(str(key))
            if not norm_key:
                continue
            normalized[norm_key] = bool(value)

        return normalized

    async def set_cms_setting(self, key, value):
        """Set a specific CMS setting.

        Args:
            key: The CMS setting key (e.g., 'monitoringActive', 'sendMedia')
            value: The value to set (typically boolean)

        Returns:
            Dict with all updated CMS settings from the API response
        """
        if not isinstance(value, bool):
            log.error("CMS setting value must be boolean, got %s", type(value))
            raise Exception(errors.REQUEST)

        log.debug("Set CMS Setting Request - key=%s, value=%s", key, value)
        response = await self.send_request("post", urls.CMS_SETTINGS, data={key: value})
        response_object = await response.json()

        log.debug("Set CMS Setting URL (post): %s", urls.CMS_SETTINGS)
        log.debug("Set CMS Setting Response (parsed): %s", response_object)

        response_object = response_object if isinstance(response_object, dict) else {}

        # Validate response contains the setting we just changed
        if key not in response_object:
            log.error("%s field missing from response: %s", key, response_object)
            raise Exception(errors.REQUEST)

        if response_object.get(key) != value:
            log.error(
                "Set %s failed - expected %s, got %s",
                key,
                value,
                response_object.get(key),
            )
            raise Exception(errors.REQUEST)

        log.info("CMS setting %s set to: %s", key, value)

        # Invalidate cache to ensure fresh data on next read
        self._cms_cache = None
        self._cms_cache_time = None

        return response_object

    async def send_request(
        self, method, path, headers=None, data=None, raise_on_error=True
    ):
        """Send requests to Abode with retry and exponential backoff.

        Args:
            method: HTTP method (get, post, etc.)
            path: API endpoint path
            headers: Optional HTTP headers
            data: Optional request data
            raise_on_error: Whether to raise on HTTP errors

        Returns:
            ResponseWrapper with response data

        Raises:
            Exception: If all retries are exhausted or authentication fails
        """
        # Retry configuration
        max_attempts = 3
        retry_delay = 1  # seconds (for generic network retries)

        for attempt in range(max_attempts):
            try:
                return await self._send_request(
                    method, path, headers, data, raise_on_error=raise_on_error
                )
            except RateLimitException as exc:
                # Start rate-limit backoff at 30s (or Retry-After if provided)
                wait_seconds = max(30, exc.retry_after or 30)
                log.warning(
                    "Abode rate limit (429). Waiting %s seconds before retry %d/%d",
                    wait_seconds,
                    attempt + 1,
                    max_attempts,
                )
                self._set_connection_status("rate_limited", str(exc))
                await asyncio.sleep(wait_seconds)
                retry_delay = min(wait_seconds * 2, 300)
            except (TimeoutError, aiohttp.ClientError) as exc:
                # Track consecutive failures to detect session staleness
                self._consecutive_failures += 1
                log.info(
                    "Abode connection error (consecutive failures: %d): %s",
                    self._consecutive_failures,
                    exc,
                )

                # If 3+ consecutive failures, session likely stale - recreate it
                if self._consecutive_failures >= 3:
                    log.warning("Multiple consecutive failures - recreating session")
                    try:
                        await self._recreate_session()
                    except Exception as recreate_exc:
                        log.error("Session recreation failed: %s", recreate_exc)

                # Only retry on connection errors, not on auth errors
                if attempt == max_attempts - 1:
                    # Last attempt failed
                    log.error(
                        "Request failed after %d attempts: %s %s",
                        max_attempts,
                        method.upper(),
                        path,
                    )
                    raise

                # Attempt to relogin and retry
                log.warning(
                    "Request attempt %d/%d failed (%s), retrying in %d seconds: %s",
                    attempt + 1,
                    max_attempts,
                    type(exc).__name__,
                    retry_delay,
                    exc,
                )

                try:
                    # Wait before retry (with exponential backoff)
                    await asyncio.sleep(retry_delay)
                    # Try to relogin
                    await self.login()
                except Exception as login_exc:
                    log.error("Relogin attempt %d failed: %s", attempt + 1, login_exc)
                    if attempt == max_attempts - 1:
                        raise

                # Exponential backoff for next retry
                retry_delay = min(retry_delay * 2, 30)  # Max 30 seconds

    async def _send_request(
        self, method, path, headers=None, data=None, raise_on_error=True
    ):
        await self._async_initialize()

        if not self._token:
            await self.login()

        if not headers:
            headers = {}

        headers["Authorization"] = (
            f"Bearer {self._oauth_token}" if self._oauth_token else ""
        )
        headers["ABODE-API-KEY"] = self._token

        # Proactively recreate session if it's getting too old (prevent server idle timeout)
        if self._session_created_time:
            session_age = (datetime.now() - self._session_created_time).total_seconds()
            if session_age > self._session_max_age_seconds:
                log.warning(
                    "Session age (%d seconds) exceeds max age (%d seconds) - recreating session proactively",
                    int(session_age),
                    self._session_max_age_seconds,
                )
                await self._recreate_session()

        try:
            url = f"{urls.BASE}{path}"
            log.debug("API Request - method=%s, path=%s, data=%s", method, url, data)

            async with getattr(self._session, method)(
                url, headers=headers, json=data
            ) as response:
                log.debug("API Response - status=%s", response.status)

                # Extract all data INSIDE the context manager before response is closed
                status = response.status
                headers_dict = dict(response.headers)

                if status < 400:
                    await AuthenticationException.raise_for(response)
                    # Extract body while response is still valid
                    try:
                        body = await response.json()
                    except Exception as exc:
                        # JSON parsing failure - check if it's an auth issue
                        raw_text = await response.text()
                        log.warning(
                            "Response JSON decode failed for %s %s (status=%s, text=%s): %s",
                            method.upper(),
                            path,
                            status,
                            raw_text[:100] if raw_text else "<empty>",
                            exc,
                        )

                        # Empty or minimal response often indicates expired auth
                        if not raw_text or len(raw_text.strip()) < 10:
                            log.error(
                                "Empty/minimal response detected - expired auth likely"
                            )
                            # Clear token and raise auth exception to trigger retry with re-login
                            self._token = None
                            self._oauth_token = None
                            raise AuthenticationException(
                                (
                                    status,
                                    "Empty response - authentication likely expired",
                                )
                            )

                        # Not an auth issue - return text as fallback
                        body = raw_text
                    # Return wrapper with extracted data (safe to use outside context)
                    self._set_connection_status("connected")
                    self._last_successful_request = datetime.now()
                    self._consecutive_failures = 0
                    return ResponseWrapper(body, status, headers_dict)

                if status == 429:
                    retry_after_header = response.headers.get("Retry-After")
                    retry_after = (
                        int(retry_after_header)
                        if retry_after_header and retry_after_header.isdigit()
                        else None
                    )
                    message = await AuthenticationException.best_message(response)
                    raise RateLimitException((status, message), retry_after)

                if not raise_on_error:
                    # For error responses, avoid JSON parsing failures on HTML bodies
                    body = await response.text()
                    return ResponseWrapper(body, status, headers_dict)
        except aiohttp.ClientError as exc:
            log.info("Abode connection error: %s", exc)
            if not raise_on_error:
                status = getattr(exc, "status", 0) or 0
                return ResponseWrapper(str(exc), status, {})

        raise Exception(errors.REQUEST)

    @property
    def default_mode(self):
        """Get the default mode."""
        return self._default_alarm_mode

    @property
    def events(self):
        """Get the event controller."""
        return self._event_controller

    @property
    def uuid(self):
        """Get the UUID."""
        return self._cookies.get("uuid", "")

    @property
    def connection_status(self) -> str:
        """Get connection status for diagnostics."""
        return self._connection_status

    @property
    def last_error(self) -> str | None:
        """Get last connection error message."""
        return self._last_error

    @property
    def test_mode_supported(self) -> bool:
        """Return whether test mode endpoints are available."""
        return self._test_mode_supported

    def _set_connection_status(self, status: str, error: str | None = None) -> None:
        """Update connection status and last error."""
        self._connection_status = status
        self._last_error = error

    async def _get_session(self):
        """Get the session after ensuring login."""
        await self.send_request("get", urls.PANEL)
        return self._session

    async def _sync_socketio_cookies(self):
        """Sync cookies from main session to SocketIO."""
        if not self._session or not hasattr(self._session, "cookie_jar"):
            log.debug("No session or cookie jar available for sync")
            return

        try:
            cookie_str = ""
            cookies = self._session.cookie_jar.filter_cookies(urls.BASE)
            cookie_str = "; ".join(
                f"{name}={morsel.value}" for name, morsel in cookies.items()
            )

            if (
                cookie_str
                and self._event_controller
                and hasattr(self._event_controller, "_socketio")
            ):
                log.info("Syncing cookies to SocketIO (%d chars)", len(cookie_str))
                # Update SocketIO with fresh cookies
                self._event_controller._socketio.set_cookie(cookie_str)
            else:
                log.debug("No cookies to sync to SocketIO or SocketIO not available")
        except Exception as exc:
            log.warning("Failed to sync cookies to SocketIO: %s", exc)

    @property
    def connection_diagnostics(self):
        """Get connection health diagnostics."""
        session_age = None
        if self._session_created_time:
            session_age = int(
                (datetime.now() - self._session_created_time).total_seconds()
            )

        return {
            "connection_status": self._connection_status,
            "authenticated": bool(self._token or self._oauth_token),
            "auth_count": self._auth_count,
            "last_auth_time": self._last_auth_time.isoformat()
            if self._last_auth_time
            else None,
            "last_successful_request": self._last_successful_request.isoformat()
            if self._last_successful_request
            else None,
            "consecutive_failures": self._consecutive_failures,
            "session_recreate_count": self._session_recreate_count,
            "session_age_seconds": session_age,
            "session_max_age_seconds": self._session_max_age_seconds,
            "socketio_connected": self._event_controller._socketio_connected
            if self._event_controller
            else False,
        }
