# Integration Tests

Tests in this directory use the mock Abode API server for realistic integration testing.

## Running Integration Tests

**Start mock server automatically (recommended)**:
```bash
pytest tests/integration/ -v -m integration
```

The mock server will start automatically when running integration tests via the `mock_server` fixture in `conftest.py`.

**Or start mock server manually**:
```bash
docker-compose up -d mock-abode
pytest tests/integration/ -v
```

**Run all tests (unit + integration)**:
```bash
pytest tests/ -v
```

**Run only unit tests (fast, no mock server)**:
```bash
pytest -m "not integration" -v
```

## Test Structure

- `test_auth.py` - Authentication flows
- `test_panel.py` - Panel operations
- `test_devices.py` - Device operations
- `test_timeline.py` - Timeline events

## Key Differences from Unit Tests

- **Unit tests** (`tests/test_*.py`): Use `aioresponses`, fast, no network
- **Integration tests** (`tests/integration/`): Use mock server, slower, realistic

Both are valuable! Unit tests for TDD and quick feedback, integration tests for confidence.

## Mock Server Details

- **URL**: http://localhost:8000
- **Test credentials**:
  - Username: `test@example.com`
  - Password: `testpassword`
- **API docs**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

## Fixtures Available

- `mock_server` - Session-scoped fixture that starts/stops mock server
- `reset_mock_server` - Function-scoped fixture that resets server state before each test
- `mock_server_client` - Provides test credentials and URL
- `abode_with_mock_server` - Provides authenticated Abode client instance
