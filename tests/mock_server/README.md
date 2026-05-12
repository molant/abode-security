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
- `POST /api/test/emit` - Broadcast an arbitrary Socket.IO frame to all clients
- `POST /api/test/disconnect_all` - Force-disconnect every Socket.IO client (used by reconnect tests)

#### `POST /api/test/emit`

Used by integration tests to exercise the SocketIO push path
(`EventController._on_device_update`, `_on_mode_change`,
`_on_timeline_update`, `_on_automation_update`). The hook only calls
`sio.emit` — it does **not** mutate REST-side state, so tests that need a
coherent REST/push pair (e.g. `com.goabode.device.update` tests) must PUT the
REST change first and then emit the push.

Body:
```json
{ "event": "com.goabode.device.update", "data": "RF:01430030" }
```

`data` is forwarded verbatim as the frame payload; omit it to emit a frame
without a body.

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
