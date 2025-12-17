# Phase 3: Integration URL Configuration

**Status**: ⏳ Not Started

## Goal
Make the Abode client's base URL configurable via environment variable, allowing the integration to connect to the mock server in development while maintaining the production default.

## Context
Currently, the base URL is hardcoded in `custom_components/abode_security/abode/helpers/urls.py`:
```python
BASE = 'https://my.goabode.com'
```

All API calls in `client.py` use `urls.BASE`. By making this configurable via environment variable, we can:
- Use `http://mock-abode:8000` in Docker dev environment
- Keep production default unchanged
- No code changes needed when deploying to production

## Prerequisites
- Phase 1 completed (docker-compose.yml with ABODE_API_URL env var)
- Phase 2 completed (mock server running)
- Understanding of Python `os.environ`

## Steps

### 3.1 Update urls.py to support dynamic BASE
**File**: `custom_components/abode_security/abode/helpers/urls.py`

**Current code (line 1)**:
```python
BASE = 'https://my.goabode.com'
```

**Change to**:
```python
import os

# Support configurable base URL for development/testing
# Production default: https://my.goabode.com
# Dev environment: Set ABODE_BASE_URL env var (e.g., http://mock-abode:8000)
BASE = os.environ.get('ABODE_BASE_URL', 'https://my.goabode.com')
```

**Impact**:
- All API calls in `client.py` use `urls.BASE`
- This single change affects all endpoints automatically
- No other code changes needed in the abode/ client library

**Verification**:
Check that no other files directly reference 'https://my.goabode.com':
```bash
grep -r "my.goabode.com" custom_components/abode_security/
```

### 3.2 Add constants (optional, for consistency)
**File**: `custom_components/abode_security/const.py`

Add near other constants:
```python
# Environment variables
ENV_ABODE_BASE_URL = "ABODE_BASE_URL"

# Configuration keys
CONF_BASE_URL = "base_url"  # For future config flow support
```

**Why**: Documents the environment variable name for future reference. Not strictly necessary but follows HA patterns.

### 3.3 Update docker-compose.yml environment variable
**File**: `docker-compose.yml`

**Current** (from Phase 1):
```yaml
environment:
  - TZ=America/New_York
  - ABODE_API_URL=http://mock-abode:8000
```

**Change to** (match the env var name in urls.py):
```yaml
environment:
  - TZ=America/New_York
  - ABODE_BASE_URL=http://mock-abode:8000
```

**Note**: We're changing from `ABODE_API_URL` to `ABODE_BASE_URL` to match the code. Choose one naming convention and stick with it.

**Alternative**: Keep `ABODE_API_URL` in docker-compose and update urls.py to check both:
```python
BASE = os.environ.get('ABODE_BASE_URL') or os.environ.get('ABODE_API_URL', 'https://my.goabode.com')
```

### 3.4 Document environment variable
**File**: `.claude/CLAUDE.md`

Add section under "## Development":
```markdown
## Development Environment Variables

- `ABODE_BASE_URL`: Override Abode API base URL
  - **Default**: `https://my.goabode.com` (production)
  - **Dev**: Set to `http://mock-abode:8000` in docker-compose.yml
  - **Production**: Do not set this variable (uses default)
  - **Location**: Set in docker-compose.yml for containerized dev
```

### 3.5 Test with mock server

**Start the full environment**:
```bash
./scripts/dev.sh
```

**Check HA connects to mock server**:

1. **Watch mock server logs**:
```bash
docker logs -f abode-dev-mock
```

2. **Watch HA logs**:
```bash
docker logs -f abode-dev-ha
```

3. **Look for**:
   - Mock server: `POST /api/auth2/login` requests
   - Mock server: `GET /api/auth2/claims` requests
   - HA: "Successfully authenticated with Abode" or similar
   - HA: Integration loads without connection errors

**Test panel status**:

Check HA state:
```bash
docker exec abode-dev-ha ha core state | grep abode
```

Or visit http://localhost:8123 and check:
- Settings → Devices & Services → Abode Security
- Should show as "Configured" or "Loaded"

**Verify using mock server**:

Set panel mode via mock server:
```bash
curl -X PUT http://localhost:8000/api/v1/panel/mode/area_1/away
```

Check if HA reflects the change:
- Refresh HA dashboard
- Check alarm panel entity state

**Debug if not working**:

1. **Check environment variable is set**:
```bash
docker exec abode-dev-ha env | grep ABODE
```
Should show: `ABODE_BASE_URL=http://mock-abode:8000`

2. **Check network connectivity**:
```bash
docker exec abode-dev-ha ping -c 3 mock-abode
```
Should succeed (both containers on same network).

3. **Check URLs being used**:
Add debug logging in `urls.py`:
```python
import logging
import os

_LOGGER = logging.getLogger(__name__)

BASE = os.environ.get('ABODE_BASE_URL', 'https://my.goabode.com')
_LOGGER.info(f"Using Abode API base URL: {BASE}")
```

4. **Restart containers**:
```bash
docker-compose restart
```

### 3.6 Create test script (optional)
**File**: `scripts/test-api-config.sh`

```bash
#!/bin/bash
# Test that integration uses configured base URL

set -e

echo "Testing Abode API URL configuration..."

# Check environment variable
echo "1. Checking ABODE_BASE_URL in container..."
ABODE_URL=$(docker exec abode-dev-ha env | grep ABODE_BASE_URL | cut -d'=' -f2)
echo "   Found: $ABODE_URL"

if [ "$ABODE_URL" != "http://mock-abode:8000" ]; then
    echo "   ❌ FAILED: Expected http://mock-abode:8000"
    exit 1
fi
echo "   ✅ PASSED"

# Test mock server is reachable
echo "2. Testing mock server connectivity..."
docker exec abode-dev-ha wget -q -O- http://mock-abode:8000/ > /dev/null
echo "   ✅ PASSED"

# Check integration logs for connection
echo "3. Checking integration connection..."
if docker logs abode-dev-ha 2>&1 | grep -q "my.goabode.com"; then
    echo "   ⚠️  WARNING: Integration may still be using production URL"
else
    echo "   ✅ PASSED: No production URL references found"
fi

echo ""
echo "All checks passed! Integration configured for local development."
```

Make executable:
```bash
chmod +x scripts/test-api-config.sh
```

Run:
```bash
./scripts/test-api-config.sh
```

## Success Criteria
- ✅ `urls.BASE` reads from `ABODE_BASE_URL` environment variable
- ✅ Docker environment sets `ABODE_BASE_URL=http://mock-abode:8000`
- ✅ Integration connects to mock server (check logs)
- ✅ Mock server receives auth requests
- ✅ Panel status retrieved successfully from mock server
- ✅ Production default (`https://my.goabode.com`) unchanged when env var not set

## Troubleshooting

**Integration still connects to production**:
- Restart containers: `docker-compose restart`
- Rebuild: `docker-compose up --build`
- Check env var: `docker exec abode-dev-ha env | grep ABODE`
- Check urls.py was modified correctly

**Mock server not reachable**:
- Verify network: `docker network ls` should show `abode-dev`
- Check both containers on same network: `docker network inspect abode-dev`
- Test ping: `docker exec abode-dev-ha ping mock-abode`

**SocketIO issues**:
- SocketIO URL is hardcoded separately in `event_controller.py`
- May need similar changes if you need real-time events
- Not critical for basic testing

## Commit Message
```
feat: Add configurable base URL for Abode API

- Make urls.BASE configurable via ABODE_BASE_URL env var
- Default to production URL (https://my.goabode.com)
- Docker dev environment uses ABODE_BASE_URL=http://mock-abode:8000
- Enables local testing against mock server
- Add documentation for environment variable

Phase 3/8 of better-development feature
```

## Next Steps
After completing this phase:
- Move to [Phase 4: Migrate/Update Existing Tests](phase-4.md)
- Update test infrastructure to use mock server
- Enable ~190 previously disabled tests
