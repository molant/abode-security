# Phase 1: Docker Dev Environment Setup

**Status**: ✅ Completed (2025-12-17)

## Goal
Create a dockerized Home Assistant development environment that auto-loads the integration with file watching for hot reload.

## Context
Currently, testing requires deploying to production (ssh to 192.168.1.60), which is cumbersome and risky. This phase creates a local Docker environment that mimics production but runs entirely on your development machine.

## Prerequisites
- Docker and Docker Compose installed
- Basic understanding of docker-compose.yml syntax
- Access to Home Assistant documentation for .storage file formats

## Steps

### 1.1 Create docker-compose.yml
**File**: `/Users/molant/src/home-assistant-things/abode-security/docker-compose.yml`

```yaml
services:
  homeassistant:
    container_name: abode-dev-ha
    image: homeassistant/home-assistant:stable
    volumes:
      - ./config:/config
      - ./custom_components/abode_security:/config/custom_components/abode_security
    environment:
      - TZ=America/New_York
      - ABODE_API_URL=http://mock-abode:8000
    ports:
      - "8123:8123"
    restart: unless-stopped
    depends_on:
      - mock-abode
    networks:
      - abode-dev

  mock-abode:
    container_name: abode-dev-mock
    build: ./tests/mock_server
    ports:
      - "8000:8000"
    networks:
      - abode-dev

networks:
  abode-dev:
    driver: bridge
```

**Key points**:
- Volume mount for integration code enables hot reload (changes trigger HA restart)
- ABODE_API_URL environment variable will be used in Phase 3
- Depends on mock-abode server (will be created in Phase 2)
- Uses latest stable Home Assistant image

### 1.2 Create config/ directory structure

**Directory**: `/Users/molant/src/home-assistant-things/abode-security/config/`

#### File: `config/configuration.yaml`
```yaml
default_config:

http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 172.16.0.0/12

abode_security:
  username: test@example.com
  password: testpassword
```

**Why these settings**:
- `default_config`: Enables all default HA integrations
- `http` config: Required for proper Docker networking
- `abode_security`: Matches test credentials in Phase 2 mock server

#### File: `config/.storage/onboarding`
```json
{
  "data": {
    "done": ["user", "core_config", "analytics"]
  },
  "key": "onboarding",
  "version": 4
}
```

This skips the initial onboarding wizard.

#### File: `config/.storage/auth`
Pre-configured test user. You may need to:
1. Start HA once and create a user manually
2. Copy the generated `.storage/auth` and `.storage/auth_provider.homeassistant` files
3. Or search HA core repo for example auth storage format

**Note**: If you can't find the format, it's okay to skip this initially. HA will create a user on first run, and you can use those credentials.

#### File: `config/.storage/lovelace`
```json
{
  "data": {
    "config": {
      "views": [
        {
          "title": "Home",
          "cards": []
        }
      ]
    }
  },
  "key": "lovelace",
  "version": 1
}
```

Empty dashboard - we'll add the Abode panel in Phase 5.

### 1.3 Create scripts/dev.sh
**File**: `/Users/molant/src/home-assistant-things/abode-security/scripts/dev.sh`

```bash
#!/bin/bash
set -e

echo "Starting Abode Security dev environment..."
docker-compose up --build
```

**Make executable**:
```bash
chmod +x scripts/dev.sh
```

### 1.4 Update .gitignore
Add to `.gitignore`:
```
# Home Assistant runtime files (don't commit these)
config/.storage/auth_provider.homeassistant
config/.storage/core.restore_state
config/home-assistant.log
config/home-assistant_v2.db*
config/.cloud/
config/deps/
config/tts/
config/.HA_VERSION

# Keep templates (do commit these)
!config/configuration.yaml
!config/.storage/auth
!config/.storage/onboarding
!config/.storage/lovelace
```

**Why**: We want to commit the config templates but not HA's runtime files.

### 1.5 Verify integration loads

**Start the environment**:
```bash
./scripts/dev.sh
```

**Expected behavior**:
1. Docker downloads Home Assistant image (first time only)
2. HA starts on http://localhost:8123
3. Mock server fails to start (expected - we create it in Phase 2)
4. Integration fails to load (expected - it can't reach mock server yet)

**Check HA logs**:
```bash
docker logs -f abode-dev-ha
```

Look for:
- "Starting Home Assistant" message
- Integration loading attempts
- Any errors (expected at this stage)

**Test file watching**:
1. Edit a comment in `custom_components/abode_security/__init__.py`
2. Save the file
3. Watch logs - you should see HA detect the change and reload

## Success Criteria
- ✅ `./scripts/dev.sh` starts HA container
- ✅ HA accessible at http://localhost:8123
- ✅ File changes in custom_components/ trigger reload
- ✅ Config directory structure created
- ⚠️ Integration not fully loaded yet (needs Phase 2 mock server)

## Troubleshooting

**HA won't start**:
- Check Docker is running: `docker ps`
- Check logs: `docker-compose logs homeassistant`
- Verify port 8123 isn't in use: `lsof -i :8123`

**File changes not triggering reload**:
- Check volume mount in docker-compose.yml
- Restart containers: `docker-compose restart`

**Can't access config/.storage/ files**:
- Start HA once, let it create the files
- Copy them as templates
- Commit the templates to git

## Commit Message
```
feat: Add Docker development environment

- Create docker-compose.yml with HA container and mock server
- Add config/ directory with pre-configured test HA instance
- Add scripts/dev.sh for easy environment startup
- Update .gitignore for HA runtime files

Phase 1/8 of better-development feature
```

## Next Steps
After completing this phase and committing:
- Move to [Phase 2: Mock Abode API Server](phase-2.md)
- The mock server will provide data for the integration to connect to
