#!/bin/bash
# Development environment setup script.
#
# `pyproject.toml` `[project.optional-dependencies].dev` is the single source
# of truth for dev/CI deps; `uv sync` resolves it against `uv.lock` and
# manages `.venv` itself, so there's no separate `python -m venv` step.
set -e

echo "Setting up development environment..."

if ! command -v uv > /dev/null 2>&1; then
    echo "❌ uv not found on PATH."
    echo "Install it from https://docs.astral.sh/uv/getting-started/installation/"
    echo "(macOS: 'brew install uv'; Linux: 'curl -LsSf https://astral.sh/uv/install.sh | sh')"
    exit 1
fi

echo "📦 Installing development dependencies via uv sync..."
uv sync --extra dev

echo "✅ Development environment setup complete!"
echo ""
echo "You can now:"
echo "  - Run tests:           uv run pytest"
echo "  - Run linting:         uv run ruff check ."
echo "  - Run type checking:   uv run mypy custom_components/abode_security"
echo "  - Run full local CI:   ./scripts/check.sh"
echo "  - Start dev env:       ./scripts/dev.sh"
