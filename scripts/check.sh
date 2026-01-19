#!/bin/bash
# Quick local checks: lint, type check, and unit tests
# Use this before committing to catch issues early

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "========================================="
echo "Running local checks"
echo "========================================="
echo ""

# Set PYTHONPATH to include vendored libraries and integration
export PYTHONPATH="$(cd "$(dirname "$0")/../custom_components" && pwd):$PYTHONPATH"

# Lint with ruff
echo "Linting with ruff..."
uv run ruff check custom_components/abode_security tests
uv run ruff format --check custom_components/abode_security tests

# Type check with mypy
echo ""
echo "Type checking with mypy..."
uv run mypy custom_components/abode_security --ignore-missing-imports

# Run tests with pytest
echo ""
echo "Running unit tests with pytest..."
uv run pytest tests/ -v --tb=short

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}All checks passed!${NC}"
echo -e "${GREEN}=========================================${NC}"
