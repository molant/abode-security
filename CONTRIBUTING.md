# Contributing to Abode Security Integration

Thank you for your interest in contributing! This document provides guidelines for contributing to the Abode Security Home Assistant integration.

## Getting Started

1. Read [development.md](development.md) for setup instructions
2. Fork the repository
3. Create a feature branch
4. Make your changes
5. Submit a pull request

## Development Setup

```bash
git clone https://github.com/YOUR-USERNAME/abode-security.git
cd abode-security
./scripts/dev.sh
```

See [development.md](development.md) for detailed instructions.

## Code Style

- **Python**: Follow PEP 8, enforced by `ruff`
- **TypeScript**: Follow project's TSConfig settings
- **Commits**: Use conventional commit format (feat:, fix:, docs:, test:, chore:, ci:, refactor:)

### Running Linters

Dev tooling is managed by `uv` (see `development.md` for full setup). Run
checks through `uv run` so they hit the pinned versions in `uv.lock`:

```bash
# Python linting and formatting
uv run ruff check .
uv run ruff format .

# Type checking (both run in CI)
uv run mypy custom_components/abode_security/
uv run pyright custom_components/abode_security/
```

Or run the full local check suite (ruff + mypy + pyright + pytest):
```bash
./scripts/check.sh
```

## Testing

All contributions must include tests:
- Unit tests for new functions/methods
- Integration tests for API interactions
- E2E tests for UI changes

### Run Tests Before Submitting

```bash
# Unit tests
uv run pytest

# Integration tests (requires mock server)
docker-compose up -d mock-abode
uv run pytest -m integration

# E2E tests (requires full environment)
./scripts/test-e2e.sh
```

## Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make your changes**
   - Write clear, well-documented code
   - Add tests for new functionality
   - Update documentation if needed

3. **Ensure all checks pass**
   - Pre-commit hooks run automatically
   - All linting, type checking, and tests must pass

4. **Commit with clear messages**
   ```bash
   git commit -m "feat: Add support for new sensor type

   - Implement temperature sensor platform
   - Add unit tests for sensor
   - Update documentation"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/my-feature
   ```

6. **Update CHANGELOG** if applicable

7. **Request review** from maintainers

## Commit Message Guidelines

Use conventional commit format:

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `test:` - Test updates
- `chore:` - Maintenance tasks
- `ci:` - CI/CD changes
- `refactor:` - Code refactoring

Example:
```
feat: Add support for wireless door locks

- Implement lock entity platform
- Add lock/unlock service calls
- Add tests for lock operations

Closes #123
```

## Pre-commit Hook

The project uses a pre-commit hook (`.githooks/pre-commit`) that runs all
checks through `uv run` against the project's `.venv`:
- Ruff linting and formatting
- MyPy and Pyright type checking
- Pytest unit tests

**Never use `--no-verify`** - all checks must pass before committing.

## Reporting Issues

When reporting issues:
1. Check existing issues first
2. Use the issue templates
3. Provide clear reproduction steps
4. Include relevant logs and configuration

## Feature Requests

When proposing new features:
1. Open an issue for discussion first
2. Describe the use case and benefits
3. Consider backward compatibility
4. Be willing to help implement it

## Questions?

- Open an issue for bugs
- Start a discussion for feature ideas
- Check existing issues/PRs first

Thank you for contributing!
