#!/bin/bash
# Quick local checks: lint, type check, and unit tests
# Use this before committing to catch issues early

set -e

# Change to project root directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "========================================="
echo "Running local checks"
echo "========================================="
echo ""

# Set PYTHONPATH to include vendored libraries and integration
export PYTHONPATH="$PROJECT_ROOT/custom_components:$PYTHONPATH"

# Lint with ruff
echo "Linting with ruff..."
uv run ruff check custom_components/abode_security tests
uv run ruff format --check custom_components/abode_security tests

# Type check with mypy
echo ""
echo "Type checking with mypy..."
uv run mypy custom_components/abode_security --ignore-missing-imports

# Strict type check with pyright. mypy and pyright catch different classes of
# issues (mypy is stricter on Any leakage, pyright on cached_property /
# variable-override compatibility against HA's entity base classes), so we run
# both. The integration was driven to 0 pyright errors in #70 and this gate
# protects future contributions from silently regressing.
echo ""
echo "Type checking with pyright..."
uv run pyright custom_components/abode_security

# Run tests with pytest
echo ""
echo "Running unit tests with pytest..."
uv run pytest tests/ -v --tb=short

# Frontend gates (lint + format + typecheck + tests) — only when this branch
# (or working tree) differs from origin/main on frontend files. Mirrors the
# pre-commit hook's selectivity so backend-only iterations don't pay the
# Playwright cost.
if git diff --name-only origin/main 2>/dev/null | grep -q '^frontend/'; then
    echo ""
    echo "Frontend changes detected — running frontend gates..."
    (cd frontend && npm run lint && npm run format && npm run typecheck && npm test)
fi

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}All checks passed!${NC}"
echo -e "${GREEN}=========================================${NC}"
