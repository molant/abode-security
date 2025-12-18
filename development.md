# Development Guide

This guide will help you get started with developing the Abode Security custom integration for Home Assistant.

## Prerequisites

- Docker and Docker Compose (or Colima on macOS)
- Python 3.11+
- Git

## Quick Start

### 1. Set Up Python Virtual Environment

Create and activate a virtual environment:
```bash
# Create virtual environment
python3 -m venv .venv

# Activate it (macOS/Linux)
source .venv/bin/activate

# Install development dependencies
./scripts/setup-dev.sh
```

**Note**: You need to activate the virtual environment each time you open a new terminal:
```bash
source .venv/bin/activate
```

### 2. Start Docker

If using Colima on macOS:
```bash
colima start
```

### 3. Launch Development Environment

```bash
./scripts/dev.sh
```

This will:
- Build and start a Home Assistant container
- Mount your integration code for live editing
- Start on http://localhost:8123

### 3. Access Home Assistant

Open http://localhost:8123 in your browser.

**Login credentials:**
- Username: `admin`
- Password: `admin`

### 4. Stop the Environment

Press `Ctrl+C` or run:
```bash
docker-compose down
```

## Development Workflow

### File Watching

Changes to files in `custom_components/abode_security/` are automatically synced to the container via volume mount. To see your changes:

1. Edit code in `custom_components/abode_security/`
2. Restart Home Assistant container or reload via Developer Tools > YAML > Restart

### Running Tests

The project uses a pre-commit hook that runs automatically on every commit:

```bash
git commit -m "your message"
```

This will execute:
- **Ruff** - Code linting and formatting
- **MyPy** - Type checking
- **Pytest** - Unit and integration tests

To run tests manually:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=custom_components/abode_security

# Run specific test file
pytest tests/test_advanced_features.py
```

### Code Quality

Before committing, ensure:
- Code is formatted with Ruff
- Type hints are correct (MyPy passes)
- All tests pass
- No `--no-verify` flag on commits

## Project Structure

```
abode-security/
├── custom_components/abode_security/  # Integration code
│   ├── __init__.py                    # Main integration setup
│   ├── config_flow.py                 # UI configuration
│   ├── const.py                       # Constants
│   ├── abode/                         # Abode API client library
│   └── [platform].py                  # HA platform implementations
├── tests/                             # Test suite
├── config/                            # Dev HA configuration
├── scripts/dev.sh                     # Development startup script
└── docker-compose.yml                 # Docker orchestration
```

## Docker Environment Details

### Services

- **homeassistant**: Main HA container
  - Port: 8123
  - Config: `./config`
  - Integration: `./custom_components/abode_security`

- **mock-abode**: Mock Abode API server
  - Port: 8000
  - Status: Running on port 8000
  - Test credentials: test@example.com / testpassword
  - API docs: http://localhost:8000/docs

### Logs

View Home Assistant logs:
```bash
docker logs -f abode-dev-ha
```

View all services:
```bash
docker-compose logs -f
```

## Configuring the Integration

The Abode Security integration uses config_flow (UI-based configuration):

1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "Abode Security"
4. Follow the setup wizard

**Note:** Mock server is available for local development. Use test credentials:
- Username: `test@example.com`
- Password: `testpassword`

The mock server provides all core Abode API endpoints without requiring a real Abode account.

## Common Tasks

### Reset Development Environment

```bash
# Stop containers
docker-compose down

# Remove config state (keeps templates)
rm -rf config/.storage/core.* config/home-assistant.* config/.HA_VERSION

# Restart
./scripts/dev.sh
```

### Update Dependencies

Dependencies are managed in `custom_components/abode_security/manifest.json`:

```json
{
  "requirements": ["platformdirs", "keyring", "lomond", "aiohttp"]
}
```

Home Assistant will automatically install these when the integration loads.

### Debugging

Enable debug logging by adding to `config/configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.abode_security: debug
```

Then restart HA and check logs.

## Git Workflow

### Commit Messages

Use conventional commit format:
- `feat:` - New features
- `fix:` - Bug fixes
- `refactor:` - Code refactoring
- `test:` - Test updates
- `docs:` - Documentation
- `chore:` - Maintenance

Example:
```bash
git commit -m "feat: Add support for new sensor type

- Implement temperature sensor platform
- Add unit tests for sensor
- Update documentation

Phase 2.3 of sensor-improvements feature"
```

### Pre-commit Hook

The hook runs automatically and will **block commits** if:
- Linting fails
- Type checking fails
- Tests fail

Never use `--no-verify` unless explicitly required.

## Troubleshooting

### Docker won't start
```bash
# Check if Docker is running
docker ps

# On macOS with Colima
colima status
colima start
```

### Port 8123 already in use
```bash
# Find and kill the process
lsof -i :8123
kill -9 <PID>
```

### Integration not loading
1. Check logs: `docker logs abode-dev-ha`
2. Verify manifest.json is valid
3. Ensure dependencies are correct
4. Check for Python syntax errors

### Tests failing
```bash
# Run tests with verbose output
pytest -v

# Run specific failing test
pytest tests/test_file.py::test_name -v
```

## Production Deployment

To deploy to production (192.168.1.60):

```bash
# SSH to production
ssh molant@192.168.1.60

# Copy integration files
scp -r custom_components/abode_security molant@192.168.1.60:/homeassistant/custom_components/

# Check logs
ssh molant@192.168.1.60 "ha core logs"
```

## Additional Resources

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Integration Structure](https://developers.home-assistant.io/docs/creating_integration_file_structure)
- [Config Flow](https://developers.home-assistant.io/docs/config_entries_config_flow_handler)

## Support

- GitHub Issues: https://github.com/molant/abode-security/issues
- Original Library: https://github.com/molant/jaraco.abode
