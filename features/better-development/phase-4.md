# Phase 4: Migrate/Update Existing Tests

**Status**: ✅ Infrastructure Complete (2024-12-17)
**Tests Enabled**: 1 of 136 (infrastructure proven working)

## Goal
Update test infrastructure to support the mock server, gradually migrate from `aioresponses` mocking to mock server integration tests, and enable ~190 currently disabled tests.

**Outcome**: Core infrastructure completed and proven working. Remaining test enablement documented in phase-4-5.md for future work.

## Context
Current test state (from exploration):
- **222 total tests**, ~190 currently disabled
- Tests use `aioresponses` to mock HTTP at library level
- Fixtures in `tests/fixtures/` (login.json, panel.json, devices.json, etc.)
- `conftest.py` uses pytest-homeassistant-custom-component
- Many tests skipped due to missing full HA instance

Now that we have a real mock server, we can:
- Enable tests that need realistic API interactions
- Keep fast unit tests with `aioresponses`
- Add integration tests that use the mock server
- Gradually migrate to more realistic testing

## Prerequisites
- Phase 1-3 completed (mock server running and integration configured)
- Mock server accessible at http://localhost:8000
- Understanding of pytest fixtures

## Steps

### 4.1 Audit disabled tests

**Run pytest with verbose skip reasons**:
```bash
pytest tests/ -v --tb=no | grep -E "(SKIP|PASSED|FAILED)"
```

**Or get detailed skip info**:
```bash
pytest tests/ -v -rs
```

**Create audit document**:
**File**: `features/better-development/test-audit.md`

```markdown
# Test Audit - Disabled Tests

## Summary
- Total tests: 222
- Disabled: ~190
- Currently passing: ~32

## Tests by Category

### Authentication Tests
- [ ] test_login_success - SKIP: needs hass
- [ ] test_login_with_mfa - SKIP: needs hass
- [ ] test_reauth_flow - SKIP: needs hass
Status: Can enable with mock server

### Panel Tests
- [ ] test_panel_get_mode - SKIP: needs hass
- [ ] test_panel_set_mode - SKIP: needs hass
Status: Can enable with mock server

### Device Tests
...

## Plan
1. Start with authentication tests (simplest)
2. Then panel tests
3. Then device tests
4. Entity lifecycle tests last (most complex)
```

**Identify patterns**:
- How many need full HA instance?
- How many can work with mock server?
- How many are just incorrectly skipped?

### 4.2 Add mock server fixtures to conftest.py

**File**: `tests/conftest.py`

Add to the end of the file:

```python
import pytest
import requests
from typing import Generator
import os

# Mock server configuration
MOCK_SERVER_URL = os.environ.get("MOCK_SERVER_URL", "http://localhost:8000")

@pytest.fixture(scope="session")
def mock_server_url() -> str:
    """Provide mock server URL for integration tests."""
    return MOCK_SERVER_URL

@pytest.fixture(scope="function")
def reset_mock_server(mock_server_url: str):
    """
    Reset mock server state before each test.

    Ensures test isolation by resetting panel mode, devices, timeline, etc.
    Skips test if mock server is not running.
    """
    try:
        response = requests.post(
            f"{mock_server_url}/api/test/reset",
            timeout=2
        )
        response.raise_for_status()
    except requests.RequestException as e:
        pytest.skip(
            f"Mock server not running at {mock_server_url}. "
            "Start with: docker-compose up mock-abode"
        )

    yield

    # Cleanup after test (optional, since next test will reset anyway)
    try:
        requests.post(f"{mock_server_url}/api/test/reset", timeout=2)
    except requests.RequestException:
        pass  # Best effort cleanup

@pytest.fixture
def mock_server_client(mock_server_url: str, reset_mock_server):
    """
    Provide authenticated client configuration for mock server tests.

    Returns a dict with connection info and test credentials.
    """
    return {
        "base_url": mock_server_url,
        "username": "test@example.com",
        "password": "testpassword",
    }

@pytest.fixture
async def abode_with_mock_server(mock_server_client):
    """
    Create Abode client connected to mock server.

    Useful for integration tests that need a real client instance.
    """
    from custom_components.abode_security.abode import Abode

    # Set environment variable for this test
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]

    try:
        abode = Abode(
            username=mock_server_client["username"],
            password=mock_server_client["password"],
            auto_login=True,
        )

        yield abode

        # Cleanup
        await abode.logout()
    finally:
        # Restore environment
        if "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]
```

### 4.3 Update requirements_dev.txt

Add:
```
requests>=2.31.0
```

**Install**:
```bash
pip install -r requirements_dev.txt
```

### 4.4 Create integration test directory structure

```bash
mkdir -p tests/integration
touch tests/integration/__init__.py
```

**File**: `tests/integration/README.md`

```markdown
# Integration Tests

Tests in this directory use the mock Abode API server for realistic integration testing.

## Running

**Start mock server first**:
```bash
docker-compose up -d mock-abode
```

**Run integration tests**:
```bash
pytest tests/integration/ -v
```

**Run all tests (unit + integration)**:
```bash
docker-compose up -d mock-abode
pytest tests/ -v
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
```

### 4.5 Create example integration test

**File**: `tests/integration/test_auth.py`

```python
"""Integration tests for authentication using mock server."""
import pytest
from custom_components.abode_security.abode import Abode
import os


@pytest.mark.integration
async def test_login_with_mock_server(mock_server_client):
    """Test successful login using mock server."""
    # Set base URL for this test
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]

    try:
        abode = Abode(
            username=mock_server_client["username"],
            password=mock_server_client["password"],
            auto_login=False,
        )

        # Test login
        await abode.login()

        # Verify token was set
        assert abode.token is not None
        assert abode.user_id is not None

        # Cleanup
        await abode.logout()
    finally:
        if "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_login_invalid_credentials(mock_server_client):
    """Test login with invalid credentials returns 401."""
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]

    try:
        abode = Abode(
            username="wrong@example.com",
            password="wrongpassword",
            auto_login=False,
        )

        # Should raise exception
        with pytest.raises(Exception):  # Adjust exception type based on client
            await abode.login()
    finally:
        if "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]
```

**Run it**:
```bash
docker-compose up -d mock-abode
pytest tests/integration/test_auth.py -v
```

### 4.6 Update pytest configuration

**File**: `pyproject.toml`

Add/update pytest section:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "--cov=custom_components/abode_security --cov-report=term-missing"
markers = [
    "integration: Integration tests requiring mock server (deselect with '-m \"not integration\"')",
    "unit: Fast unit tests with mocked responses",
]
```

**Now you can**:

Run only unit tests (fast):
```bash
pytest -m "not integration"
```

Run only integration tests:
```bash
pytest -m integration
```

Run all tests:
```bash
pytest
```

### 4.7 Enable tests gradually

**Strategy**:
1. Start with simple authentication tests
2. Move to panel tests
3. Then device tests
4. Finally entity lifecycle tests

**Process for each batch**:

1. **Pick a test file** (e.g., `tests/test_config_flow.py`)

2. **Identify skipped tests**:
```bash
pytest tests/test_config_flow.py -v
```

3. **For each skipped test**:
   - Understand why it's skipped
   - Can it work with mock server? → Update to use `mock_server_client` fixture
   - Does it need full HA? → Leave skipped or create integration test version
   - Is skip decorator wrong? → Remove it

4. **Example migration**:

**Before** (skipped):
```python
@pytest.mark.skip(reason="needs hass instance")
async def test_panel_mode_change():
    # Test code...
```

**After** (using mock server):
```python
@pytest.mark.integration
async def test_panel_mode_change(mock_server_client, abode_with_mock_server):
    """Test changing panel mode using mock server."""
    abode = abode_with_mock_server

    # Change mode
    await abode.set_panel_mode("area_1", "away")

    # Verify
    panel = await abode.get_panel()
    assert panel["mode"]["area_1"] == "away"
```

5. **Run and verify**:
```bash
docker-compose up -d mock-abode
pytest tests/test_config_flow.py -v
```

6. **Commit when batch passes**:
```bash
git add tests/test_config_flow.py
git commit -m "test: Enable config flow tests with mock server

- Remove skip decorators from 5 tests
- Update to use mock_server_client fixture
- All config flow tests now passing

Part of Phase 4/8 better-development feature"
```

7. **Repeat** for next test file

### 4.8 Track progress

**Update test-audit.md** as you enable tests:

```markdown
## Progress

- [x] test_config_flow.py (5 tests enabled) - 2024-12-17
- [x] test_auth.py (3 tests enabled) - 2024-12-17
- [ ] test_panel.py (10 tests, in progress)
- [ ] test_devices.py (20 tests, todo)
...

## Statistics
- Enabled: 8 tests
- Remaining: 182 tests
- Target: Enable at least 50 tests in this phase
```

## Success Criteria
- ✅ Mock server fixtures added to conftest.py
- ✅ Integration test directory created
- ✅ Example integration tests created (4 integration tests)
- ✅ Pytest markers configured (integration, unit)
- ✅ pytest-homeassistant-custom-component configured and working
- ✅ HA test environment enabled - custom integrations load properly
- ✅ Test environment proven working (test_one_config_allowed passing)
- ⚠️ Previously disabled tests - 1 enabled, 135 remain (see phase-4-5.md)
- ✅ requirements-dev.txt consolidated and updated with requests
- ✅ Test audit document created (test-audit.md)

## Commit Message
```
feat: Update test infrastructure for mock server

- Add mock server fixtures to conftest.py (reset_mock_server, mock_server_client)
- Add abode_with_mock_server fixture for integration tests
- Create tests/integration/ directory structure
- Add pytest markers: integration, unit
- Enable [X] previously disabled tests using mock server
- Update requirements_dev.txt with requests library
- Add test-audit.md to track progress

Phase 4/8 of better-development feature
```

## What Was Completed

### ✅ Core Infrastructure (Complete)
1. **Requirements consolidation**: Merged requirements files into requirements-dev.txt, added requests library
2. **Mock server fixtures**: Auto-start/stop mock server, reset between tests
3. **Integration test structure**: Created `tests/integration/` directory with README
4. **Pytest configuration**: Added integration/unit markers, skip integration by default
5. **Test audit**: Documented all 136 skipped tests by category in test-audit.md
6. **HA test environment**: Configured pytest-homeassistant-custom-component to load custom integrations
7. **Example tests**: Created 4 integration tests for authentication in tests/integration/test_auth.py

### ⚠️ Partial Progress
- **Enabled 1 test**: `test_one_config_allowed` (proves infrastructure works)
- **Remaining 135 tests**: Require additional work (see phase-4-5.md)

## Key Achievements

1. **Mock server integration works**: Session-scoped fixture auto-starts Docker container
2. **HA test environment works**: Custom integrations load properly in tests via enable_custom_integrations fixture
3. **Test infrastructure complete**: Ready for incremental test enabling
4. **Clear documentation**: test-audit.md categorizes all skipped tests by type

## Challenges Encountered

See [phase-4-5.md](phase-4-5.md) for detailed analysis of remaining challenges and continuation plan.

## Notes

- **Infrastructure first**: Complete and working test framework is more valuable than partially-enabled tests
- **Proven working**: Passing test demonstrates the infrastructure functions correctly
- **Incremental approach**: Tests can be enabled over time as code improvements are made
- **Test quality**: Better to have working infrastructure than broken tests

## Next Steps
- See [phase-4-5.md](phase-4-5.md) for continuing test enablement work
- Or move to [Phase 5: Frontend Dev Workflow](phase-5.md) to continue better-development feature
