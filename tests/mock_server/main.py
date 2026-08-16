import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import socketio
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from socketio.asyncio_manager import AsyncManager as _AsyncManager


# python-socketio 4.6.1's AsyncManager.emit passes raw coroutines to
# asyncio.wait. Support for that was deprecated in 3.8 and REMOVED in 3.11
# (asyncio/tasks.py raises TypeError("Passing coroutines is forbidden, use
# tasks explicitly.")), so every emit -- including emit_state_change for
# REST-driven device/panel updates -- returns 500 on every supported runtime
# (Docker mock and local both run python:3.14-slim / Py3.14). Apply the
# coroutine-to-task shim unconditionally; it's a no-op on the rare Python
# <3.11 runtime and required everywhere else. Upstream fix is in
# python-socketio 5.x, but we're stuck on 4.x for Engine.IO v3 compatibility
# (#105).
async def _emit_wrapping_coroutines_in_tasks(self, event, data, namespace, **kwargs):
    if namespace not in self.rooms or kwargs.get("room") not in self.rooms[namespace]:
        return
    skip_sid = kwargs.get("skip_sid")
    if not isinstance(skip_sid, list):
        skip_sid = [skip_sid]
    callback = kwargs.get("callback")
    tasks = []
    for sid in self.get_participants(namespace, kwargs.get("room")):
        if sid in skip_sid:
            continue
        ack_id = (
            self._generate_ack_id(sid, namespace, callback)
            if callback is not None
            else None
        )
        tasks.append(
            asyncio.ensure_future(
                self.server._emit_internal(sid, event, data, namespace, ack_id)
            )
        )
    if tasks:
        await asyncio.wait(tasks)


_AsyncManager.emit = _emit_wrapping_coroutines_in_tasks

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="Abode Mock API", version="1.0.0")

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi", cors_allowed_origins="*", logger=True, engineio_logger=False
)

# Load fixtures from existing test fixtures.
# In Docker, docker-compose mounts `./tests/fixtures` at
# `/app/fixtures` (== `Path(__file__).parent / "fixtures"`).
# Outside Docker (local dev / CI alternatives), the volume mount is absent
# and the fixtures live next to this file's parent directory, at
# `tests/fixtures`. Search both so the mock works in either layout without
# needing a symlink.
_FIXTURES_CANDIDATES = (
    Path(__file__).parent / "fixtures",
    Path(__file__).parent.parent / "fixtures",
)


def load_fixture(name: str) -> Any:
    """Load a JSON fixture file. May return a dict or a list at top level."""
    for base in _FIXTURES_CANDIDATES:
        fixture_path = base / f"{name}.json"
        if fixture_path.exists():
            with open(fixture_path) as f:
                return json.load(f)
    raise FileNotFoundError(f"Fixture not found: {name}.json")


# In-memory state (reset between test runs)
state = {
    "session_token": None,
    "oauth_token": None,
    "panel_mode": "standby",
    "devices": [],
    "timeline": [],
    "cms_settings": {
        "testModeActive": False,
        "monitoringActive": True,
        "sendMedia": True,
        "dispatchWithoutVerification": False,
        "dispatchPolice": True,
        "dispatchFire": True,
        "dispatchMedical": True,
    },
}

# Initialize devices from fixture on startup
try:
    devices_data = load_fixture("devices")
    state["devices"] = devices_data if isinstance(devices_data, list) else []
    log.info(f"Loaded {len(state['devices'])} devices from fixture")
except FileNotFoundError:
    log.warning("devices.json fixture not found, using empty device list")
    state["devices"] = []


# ===== Socket.IO Event Handlers =====


@sio.event
async def connect(sid, _environ):
    """Handle client connection."""
    log.info(f"Socket.IO client connected: {sid}")
    return True


@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    log.info(f"Socket.IO client disconnected: {sid}")


@sio.event
async def subscribe(sid, data):
    """
    Handle subscription requests.

    Abode clients subscribe to device/panel updates.
    """
    log.info(f"Socket.IO client {sid} subscribed to: {data}")
    # In real Abode, this would register interest in specific device updates
    # For mock, we'll just acknowledge
    return {"status": "subscribed"}


async def emit_state_change(event_type: str, data: dict):
    """
    Emit state change event to all connected clients.

    Args:
        event_type: Type of event (e.g., 'com.goabode.states')
        data: Event data
    """
    log.info(f"Emitting Socket.IO event: {event_type} - {data}")
    await sio.emit(event_type, data)


# ===== Authentication Endpoints =====


@app.post("/api/auth2/login")
async def login(request: Request):
    """
    Login endpoint - validates credentials and returns session token.

    Test credentials:
    - username: test@example.com
    - password: testpassword
    """
    body = await request.json()

    if body.get("id") == "test@example.com" and body.get("password") == "testpassword":
        login_data = load_fixture("login")

        # Store session for this mock instance
        state["session_token"] = "mock-session-token-12345"

        # Return login response with session cookie
        response = JSONResponse(login_data)
        response.set_cookie(
            key="SESSION",
            value=state["session_token"],
            httponly=True,
            secure=False,  # For local dev
        )
        log.info("User logged in successfully")
        return response

    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/api/auth2/claims")
async def oauth_claims():
    """
    OAuth token endpoint - returns Bearer token for API requests.
    """
    oauth_data = load_fixture("oauth_claims")
    state["oauth_token"] = oauth_data.get("access_token")
    return oauth_data


@app.post("/api/v1/logout")
async def logout():
    """Logout and clear session."""
    state["session_token"] = None
    state["oauth_token"] = None
    log.info("User logged out")
    return {"success": True}


# ===== Panel Endpoints =====


@app.get("/api/v1/panel")
async def get_panel():
    """
    Get panel status including current alarm mode.
    """
    panel_data = load_fixture("panel")

    # Update with current state
    panel_data["mode"]["area_1"] = state["panel_mode"]

    return panel_data


@app.put("/api/v1/panel/mode/{area}/{mode}")
async def set_panel_mode(area: str, mode: str):
    """
    Set alarm panel mode.

    Valid modes: standby, home, away
    Valid areas: area_1, area_2
    """
    valid_modes = ["standby", "home", "away"]
    valid_areas = ["area_1", "area_2"]

    if area not in valid_areas:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid area. Must be one of: {', '.join(valid_areas)}",
        )

    if mode not in valid_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode. Must be one of: {', '.join(valid_modes)}",
        )

    state["panel_mode"] = mode
    log.info(f"Panel mode changed to {mode} for {area}")

    # Emit Socket.IO event for panel mode change
    await emit_state_change(
        "com.goabode.states",
        {
            "id": "alarm1",
            "type_tag": "device_type.alarm",
            "mode": mode,
            "area": area,
        },
    )

    return {
        "success": True,
        "area": area,
        "mode": mode,
    }


# Abode only accepts these three on triggerAlarm. The other alarm types it
# defines (CO, SMOKE, SMOKE_CO, BURGLAR) are inbound classifications reported
# by sensors, and the real API rejects them with 400 errorCode 16013.
#
# The mock used to accept *any* type unconditionally, which is why an action
# wired to the BURGLAR switch passed every unit, integration, and E2E run
# while failing on every single real trigger.
TRIGGERABLE_ALARM_TYPES = {"PANIC", "SILENT_PANIC", "MEDICAL"}


@app.post("/integrations/v1/panel/alarm")
async def trigger_alarm(request: Request):
    """
    Trigger manual alarm.

    Accepts PANIC, SILENT_PANIC, MEDICAL. Anything else reproduces the real
    API's rejection.
    """
    body = await request.json()
    alarm_type = body.get("type", "PANIC")

    if alarm_type not in TRIGGERABLE_ALARM_TYPES:
        log.warning(f"Rejecting untriggerable alarm type: {alarm_type}")
        return JSONResponse(
            status_code=400,
            content={
                "errorCode": 16013,
                "message": "invalid {{param}} value.",
                "errorProperties": {"action": "triggerAlarm", "type": alarm_type},
            },
        )

    # Add to timeline
    state["timeline"].insert(
        0,
        {
            "id": f"timeline_{len(state['timeline']) + 1}",
            "event_type": "Alarm",
            "event_name": f"Manual {alarm_type} Alarm",
            "is_alarm": "1",
        },
    )

    log.info(f"Manual {alarm_type} alarm triggered")

    # Return format expected by alarm.py:117
    return {
        "code": 200,
        "message": f"Manual {alarm_type} alarm triggered",
        "type": alarm_type,
    }


# ===== Device Endpoints =====


@app.get("/api/v1/devices")
async def get_devices():
    """
    Get all devices.
    """
    return state["devices"]


@app.get("/api/v1/devices/{device_id}")
async def get_device(device_id: str):
    """
    Get specific device by ID.
    """
    device = next((d for d in state["devices"] if d.get("id") == device_id), None)

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return device


@app.put("/api/v1/devices/{device_id}")
async def update_device(device_id: str, request: Request):
    """
    Update device status (e.g., turn on/off light, lock/unlock door).
    """
    body = await request.json()

    # Find and update device
    for device in state["devices"]:
        if device.get("id") == device_id:
            device.update(body)
            log.info(f"Device {device_id} updated")

            # Emit Socket.IO event for device update
            await emit_state_change("com.goabode.states", device)

            return device

    raise HTTPException(status_code=404, detail="Device not found")


# ===== Timeline Endpoints =====


@app.get("/api/v1/timeline")
async def get_timeline(size: int = 10):
    """
    Get recent timeline events.
    """
    return state["timeline"][:size]


# ===== CMS Settings Endpoints =====


@app.get("/integrations/v1/cms/settings")
async def get_cms_settings():
    """
    Get Central Monitoring Service settings.
    """
    return state["cms_settings"]


@app.post("/integrations/v1/cms/settings")
async def update_cms_settings(request: Request):
    """
    Update CMS settings.
    """
    body = await request.json()
    state["cms_settings"].update(body)
    log.info(f"CMS settings updated: {body}")
    return state["cms_settings"]


@app.get("/integrations/v1/security-panel")
async def get_security_panel():
    """
    Get enhanced panel info with CMS settings.
    """
    panel_data = load_fixture("panel")
    panel_data["mode"]["area_1"] = state["panel_mode"]
    panel_data["attributes"] = {"cms": state["cms_settings"]}
    return panel_data


# ===== Automation Endpoints =====


@app.get("/integrations/v1/automations/")
async def get_automations():
    """
    Get all automations.

    `automation.json` is already a JSON array of automations, so we return
    it directly. Wrapping it in another list would produce ``[[...]]``,
    which `Client._update_all` cannot iterate -- it expects each element
    to be an automation dict.
    """
    try:
        return load_fixture("automation")
    except FileNotFoundError:
        return []


# ===== Test Utilities =====


@app.post("/api/test/reset")
async def reset_state():
    """
    Reset server state to defaults.

    Use this between tests to ensure clean state.
    """
    state["session_token"] = None
    state["oauth_token"] = None
    state["panel_mode"] = "standby"
    state["timeline"] = []
    state["cms_settings"] = {
        "testModeActive": False,
        "monitoringActive": True,
        "sendMedia": True,
        "dispatchWithoutVerification": False,
        "dispatchPolice": True,
        "dispatchFire": True,
        "dispatchMedical": True,
    }

    # Reload devices from fixture
    try:
        devices_data = load_fixture("devices")
        state["devices"] = devices_data if isinstance(devices_data, list) else []
    except FileNotFoundError:
        log.warning("devices.json fixture not found during reset")
        state["devices"] = []

    log.info("State reset to defaults")
    return {"status": "reset", "message": "State reset to defaults"}


@app.get("/api/test/state")
async def get_state():
    """
    Get current mock server state (for debugging).
    """
    return {
        "has_session": state["session_token"] is not None,
        "panel_mode": state["panel_mode"],
        "device_count": len(state["devices"]),
        "timeline_count": len(state["timeline"]),
    }


@app.post("/api/test/disconnect_all")
async def disconnect_all():
    """Force-disconnect every connected Socket.IO client.

    Used by integration tests to exercise the vendored client's reconnect
    path: it closes the underlying websocket, which the client treats as a
    transient disconnect and re-establishes after backoff. Unlike
    `/api/v1/logout` (which only clears REST session state without touching
    the websocket), this hook actually delivers a CLOSE frame.
    """
    # sio.manager.rooms maps namespace → room → {sid: bool}. python-socketio
    # uses None as the default broadcast room key (NOT an empty string), so
    # every connected sid in the default namespace lives under rooms["/"][None].
    # Iterate over a snapshot since sio.disconnect mutates rooms.
    sids = list(sio.manager.rooms.get("/", {}).get(None, {}).keys())
    for sid in sids:
        await sio.disconnect(sid)
    log.info(f"Disconnected {len(sids)} Socket.IO client(s)")
    return {"status": "disconnected", "count": len(sids)}


@app.post("/api/test/emit")
async def emit_event(request: Request):
    """Broadcast an arbitrary Socket.IO frame to all connected clients.

    Tests use this to exercise EventController's push-event handlers
    (com.goabode.device.update, com.goabode.gateway.mode,
    com.goabode.gateway.timeline, com.goabode.automation) without driving them
    indirectly through REST mutations -- the REST endpoints emit
    `com.goabode.states`, which the integration does not listen for.

    Request body must include `event` (str). `data` is optional; when present
    it's forwarded verbatim as the SocketIO frame payload. The endpoint does
    not mutate any REST-side state -- callers that need a coherent
    REST/push pair (e.g. device.update tests) should PUT the REST update first
    and then POST here.
    """
    try:
        body = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid JSON body: {exc.msg}"
        ) from exc
    if not isinstance(body, dict):
        raise HTTPException(
            status_code=400, detail="Request body must be a JSON object"
        )
    event = body.get("event")
    if not isinstance(event, str) or not event:
        raise HTTPException(
            status_code=400, detail="'event' must be a non-empty string"
        )

    data = body.get("data")
    if data is None:
        await sio.emit(event)
    else:
        await sio.emit(event, data)
    log.info(f"Test-emitted Socket.IO event: {event}")
    return {"status": "emitted", "event": event}


# ===== Server Setup =====


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/")
async def root():
    """
    Root endpoint - shows API info.
    """
    return {
        "name": "Abode Mock API Server",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "auth": "/api/auth2/login",
            "panel": "/api/v1/panel",
            "devices": "/api/v1/devices",
            "test": "/api/test/reset",
            "test_emit": "/api/test/emit",
        },
        "websocket": "Socket.IO available at /socket.io/",
    }


# Wrap FastAPI app with Socket.IO
socket_app = socketio.ASGIApp(sio, app)

if __name__ == "__main__":
    uvicorn.run(socket_app, host="0.0.0.0", port=8000, log_level="info")
