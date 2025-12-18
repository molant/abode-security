# Phase 3.5: WebSocket/SocketIO Configuration

**Status**: ✅ Complete (2025-12-17)
**Depends On**: Phase 3 (Integration URL Configuration)

## Goal
Make the WebSocket/SocketIO URL configurable to support real-time events in the development environment with the mock server.

## Context

Currently, the WebSocket URL is hardcoded in `custom_components/abode_security/abode/event_controller.py:18`:
```python
SOCKETIO_URL = "wss://my.goabode.com/socket.io/"
```

This prevents real-time events (device updates, timeline events, alarm triggers) from working with the mock server in development.

## Prerequisites

1. **Phase 3 completed** - REST API base URL is configurable
2. **Mock server WebSocket support** - FastAPI mock server needs WebSocket/SocketIO endpoints added

## Current State

**Mock Server:** `tests/mock_server/main.py` currently only has REST HTTP endpoints. No WebSocket/SocketIO support.

**EventController:** Uses hardcoded `SOCKETIO_URL` for connecting to Abode's real-time event stream.

**Impact:** In development, real-time events won't work even though REST API calls will succeed.

## Implementation Plan

### Part A: Add WebSocket Support to Mock Server

**File:** `tests/mock_server/main.py`

**Required Changes:**

1. **Install python-socketio dependency:**
   - Add to `tests/mock_server/requirements.txt` or Dockerfile
   - `python-socketio[asyncio]` for async FastAPI integration

2. **Set up Socket.IO server:**
   ```python
   import socketio

   # Create Socket.IO server
   sio = socketio.AsyncServer(
       async_mode='asgi',
       cors_allowed_origins='*',
       logger=True,
       engineio_logger=True
   )

   # Wrap FastAPI app with Socket.IO
   socket_app = socketio.ASGIApp(sio, app)
   ```

3. **Implement Socket.IO event handlers:**
   - `connect` - Handle client connections
   - `disconnect` - Handle disconnections
   - `subscribe` - Subscribe to device/panel updates (Abode uses this)
   - Emit events when panel mode changes, devices update, etc.

4. **Update uvicorn startup:**
   ```python
   if __name__ == "__main__":
       uvicorn.run(socket_app, host="0.0.0.0", port=8000, log_level="info")
   ```

5. **Emit events on state changes:**
   - When `set_panel_mode()` is called, emit `com.goabode.states` event
   - When `update_device()` is called, emit device update event
   - Match Abode's event format (see `event_controller.py` for expected format)

**Example event format to research:**
- Check `event_controller.py` lines 68+ to see what events it expects
- Look at existing test fixtures for event examples
- May need to capture real Abode WebSocket traffic for accurate format

### Part B: Make EventController WebSocket URL Configurable

**File:** `custom_components/abode_security/abode/event_controller.py`

**Current (line 18):**
```python
SOCKETIO_URL = "wss://my.goabode.com/socket.io/"
```

**Option 1: Derive from REST Base URL (Recommended)**
```python
import os
from .helpers import urls

# Derive WebSocket URL from base URL
# Production: wss://my.goabode.com/socket.io/
# Development: ws://mock-abode:8000/socket.io/
def _get_socketio_url():
    base = os.environ.get('ABODE_BASE_URL', 'https://my.goabode.com')
    # Convert http(s) to ws(s)
    if base.startswith('https://'):
        ws_url = base.replace('https://', 'wss://')
    elif base.startswith('http://'):
        ws_url = base.replace('http://', 'ws://')
    else:
        ws_url = f'wss://{base}'
    return f"{ws_url}/socket.io/"

SOCKETIO_URL = _get_socketio_url()
```

**Option 2: Separate Environment Variable**
```python
import os

# Allow separate WebSocket URL override if needed
# Default: Derive from ABODE_BASE_URL or use production
SOCKETIO_URL = os.environ.get('ABODE_SOCKETIO_URL')

if not SOCKETIO_URL:
    base = os.environ.get('ABODE_BASE_URL', 'https://my.goabode.com')
    # Convert and derive as in Option 1
    SOCKETIO_URL = _derive_ws_url(base)
```

**Recommendation:** Use Option 1 (derive from base URL) for simplicity.

### Part C: Update docker-compose.yml (if using Option 2)

Only if implementing Option 2:

```yaml
environment:
  - TZ=America/New_York
  - ABODE_BASE_URL=http://mock-abode:8000
  - ABODE_SOCKETIO_URL=ws://mock-abode:8000/socket.io/
```

## Testing WebSocket Connection

### Test 1: Manual WebSocket Client

```python
# test_websocket.py
import socketio

sio = socketio.Client()

@sio.on('connect')
def on_connect():
    print('Connected to mock server')

@sio.on('com.goabode.states')
def on_state_change(data):
    print(f'State change: {data}')

sio.connect('http://localhost:8000')
sio.wait()
```

### Test 2: Integration Test

1. Start dev environment
2. Trigger panel mode change via mock server API:
   ```bash
   curl -X PUT http://localhost:8000/api/v1/panel/mode/area_1/away
   ```
3. Check HA logs for WebSocket event received
4. Verify HA alarm panel state updates in real-time

### Test 3: Check Event Controller Logs

```bash
docker logs -f abode-dev-ha 2>&1 | grep -i socketio
# Look for: "Connected to SocketIO", "Received event", etc.
```

## Abode WebSocket Event Format Research

**Need to determine:**
1. What events does Abode emit? (device updates, panel changes, timeline events)
2. What's the exact JSON structure?
3. What event names are used? (`com.goabode.states`, etc.)
4. Does it use rooms/namespaces?

**Sources to check:**
- Existing integration code in `event_controller.py`
- Test fixtures (if any WebSocket fixtures exist)
- Real Abode account WebSocket traffic (capture with browser DevTools)
- jaraco.abode library documentation

## Success Criteria

- ✅ Mock server has Socket.IO endpoint at `/socket.io/`
- ✅ Mock server emits events on state changes
- ✅ EventController connects to mock server's WebSocket (check logs)
- ✅ HA receives real-time updates when panel mode changes
- ✅ Device state changes propagate via WebSocket
- ✅ No errors in WebSocket connection logs
- ✅ Production WebSocket URL still works (wss://my.goabode.com/socket.io/)

## Edge Cases

1. **WebSocket connection failures** - Should degrade gracefully, fall back to polling if implemented
2. **Mock server restart** - EventController should reconnect automatically
3. **Invalid WebSocket URL** - Should log clear error message
4. **Missing Socket.IO dependency** - Add to requirements/Dockerfile

## Estimated Complexity

**Medium-High** (4-6 hours)
- Mock server Socket.IO integration: 2-3 hours
- Event format research: 1-2 hours
- EventController URL configuration: 30 minutes
- Testing and debugging: 1-2 hours

## Alternative Approach

If Socket.IO implementation is too complex:
- **Skip WebSocket in development** - Document that real-time events won't work in dev
- **Use polling instead** - Add polling mechanism to EventController as fallback
- **Defer until needed** - Only implement if real-time events are critical for testing

## Resources

- [python-socketio documentation](https://python-socketio.readthedocs.io/)
- [FastAPI with Socket.IO](https://github.com/miguelgrinberg/python-socketio#fastapi)
- [Socket.IO protocol specification](https://socket.io/docs/v4/)

## Commit Message Template

```
feat: Add WebSocket/SocketIO support to mock server and make URL configurable

- Implement Socket.IO server in FastAPI mock server
- Emit real-time events on panel and device state changes
- Make EventController WebSocket URL derive from ABODE_BASE_URL
- Support ws://mock-abode:8000/socket.io/ in development
- Maintain wss://my.goabode.com/socket.io/ default for production

Phase 3.5: WebSocket/SocketIO Configuration
```

## Next Steps

After completing this phase:
- Test real-time events work in development
- Verify polling still works if WebSocket fails
- Move to Phase 4: Migrate/Update Existing Tests
