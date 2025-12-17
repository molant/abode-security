# Phase 2: Mock Abode API Server

**Status**: ⏳ Not Started

## Goal
Create a FastAPI mock server that implements core Abode API endpoints, returning fixture data for local testing without hitting the real Abode API.

## Context
The Abode API client (in `custom_components/abode_security/abode/`) makes requests to `https://my.goabode.com`. For local development, we need a mock server that:
- Responds to the same endpoints
- Returns realistic data from test fixtures
- Maintains state (panel mode, device status)
- Provides a reset endpoint for test isolation

From exploration, the key endpoints used are:
- Auth: `POST /api/auth2/login`, `GET /api/auth2/claims`
- Panel: `GET /api/v1/panel`, `PUT /api/v1/panel/mode/{area}/{mode}`
- Devices: `GET /api/v1/devices`
- Timeline: `GET /api/v1/timeline`
- CMS Settings: `GET /integrations/v1/cms/settings`

## Prerequisites
- Phase 1 completed (docker-compose.yml exists)
- Python 3.11+ knowledge
- Basic FastAPI understanding
- Test fixtures in `tests/fixtures/` (already exist)

## Steps

### 2.1 Create mock server directory structure
**Directory**: `/Users/molant/src/home-assistant-things/abode-security/tests/mock_server/`

**Files to create**:
- `main.py` - FastAPI application
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container build instructions
- `README.md` - API documentation

### 2.2 Implement main.py
**File**: `tests/mock_server/main.py`

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import json
from pathlib import Path
from typing import Any, Dict
import uvicorn

app = FastAPI(title="Abode Mock API", version="1.0.0")

# Load fixtures from existing test fixtures
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

def load_fixture(name: str) -> Dict[str, Any]:
    """Load a JSON fixture file."""
    fixture_path = FIXTURES_DIR / f"{name}.json"
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture not found: {name}.json")
    with open(fixture_path) as f:
        return json.load(f)

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
    }
}

# Initialize devices from fixture on startup
try:
    state["devices"] = load_fixture("devices")
except FileNotFoundError:
    state["devices"] = []

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

    if mode not in valid_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode. Must be one of: {', '.join(valid_modes)}"
        )

    state["panel_mode"] = mode

    return {
        "success": True,
        "area": area,
        "mode": mode,
    }

@app.post("/integrations/v1/panel/alarm")
async def trigger_alarm(request: Request):
    """
    Trigger manual alarm.

    Types: PANIC, SILENT_PANIC, MEDICAL, CO, SMOKE_CO, SMOKE, BURGLAR
    """
    body = await request.json()
    alarm_type = body.get("type", "PANIC")

    # Add to timeline
    state["timeline"].insert(0, {
        "id": f"timeline_{len(state['timeline']) + 1}",
        "event_type": "Alarm",
        "event_name": f"Manual {alarm_type} Alarm",
        "is_alarm": "1",
    })

    return {"success": True, "type": alarm_type}

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
    """
    try:
        return [load_fixture("automation")]
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
        state["devices"] = load_fixture("devices")
    except FileNotFoundError:
        state["devices"] = []

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

# ===== Server Setup =====

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
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
```

### 2.3 Create requirements.txt
**File**: `tests/mock_server/requirements.txt`
```
fastapi==0.115.0
uvicorn[standard]==0.32.0
```

### 2.4 Create Dockerfile
**File**: `tests/mock_server/Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .

EXPOSE 8000

# Run server
CMD ["python", "main.py"]
```

### 2.5 Document API
**File**: `tests/mock_server/README.md`

```markdown
# Abode Mock API Server

FastAPI-based mock server for Abode API endpoints used by the Home Assistant integration.

## Running Locally

### With Docker Compose (recommended)
```bash
docker-compose up mock-abode
```

### Standalone
```bash
cd tests/mock_server
pip install -r requirements.txt
python main.py
```

Server starts on http://localhost:8000

## API Documentation

FastAPI auto-generates docs at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Test Credentials

- **Username**: `test@example.com`
- **Password**: `testpassword`

## Key Endpoints

### Authentication
- `POST /api/auth2/login` - Login and get session
- `GET /api/auth2/claims` - Get OAuth token
- `POST /api/v1/logout` - Logout

### Panel
- `GET /api/v1/panel` - Get panel status
- `PUT /api/v1/panel/mode/{area}/{mode}` - Set alarm mode (standby/home/away)
- `POST /integrations/v1/panel/alarm` - Trigger manual alarm

### Devices
- `GET /api/v1/devices` - List all devices
- `GET /api/v1/devices/{id}` - Get specific device
- `PUT /api/v1/devices/{id}` - Update device

### Timeline
- `GET /api/v1/timeline?size=10` - Get recent events

### CMS Settings
- `GET /integrations/v1/cms/settings` - Get monitoring settings
- `POST /integrations/v1/cms/settings` - Update monitoring settings

### Test Utilities
- `POST /api/test/reset` - Reset all state to defaults
- `GET /api/test/state` - View current server state (debugging)

## State Management

The server maintains in-memory state for:
- Panel mode (standby/home/away)
- Devices (loaded from `tests/fixtures/devices.json`)
- Timeline events
- CMS settings

Use `POST /api/test/reset` to reset state between tests.

## Example Usage

### Login
```bash
curl -X POST http://localhost:8000/api/auth2/login \
  -H "Content-Type: application/json" \
  -d '{"id":"test@example.com","password":"testpassword"}'
```

### Set Panel Mode
```bash
curl -X PUT http://localhost:8000/api/v1/panel/mode/area_1/away
```

### Get Devices
```bash
curl http://localhost:8000/api/v1/devices
```

### Reset State
```bash
curl -X POST http://localhost:8000/api/test/reset
```
```

### 2.6 Test mock server

**Build and start**:
```bash
docker-compose up --build mock-abode
```

**Verify it's running**:
```bash
curl http://localhost:8000/
```

Expected response:
```json
{
  "name": "Abode Mock API Server",
  "version": "1.0.0",
  "docs": "/docs",
  ...
}
```

**Test login**:
```bash
curl -X POST http://localhost:8000/api/auth2/login \
  -H "Content-Type: application/json" \
  -d '{"id":"test@example.com","password":"testpassword"}'
```

**View auto-generated docs**:
Open http://localhost:8000/docs in browser

## Success Criteria
- ✅ Mock server builds and starts
- ✅ FastAPI docs accessible at http://localhost:8000/docs
- ✅ Login endpoint returns fixture data
- ✅ Panel and device endpoints work
- ✅ State reset endpoint works

## Commit Message
```
feat: Add FastAPI mock Abode API server

- Implement core endpoints: auth, panel, devices, timeline, CMS
- Load data from existing test fixtures
- Add state management for panel modes and devices
- Add test reset endpoint for test cleanup
- Dockerfile and requirements for containerization

Phase 2/8 of better-development feature
```

## Next Steps
After completing this phase:
- Move to [Phase 3: Integration URL Configuration](phase-3.md)
- Configure the integration to use the mock server instead of production
