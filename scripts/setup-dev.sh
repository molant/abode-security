#!/bin/bash
# Development environment setup script
set -e

echo "Setting up development environment..."

# Check if we're in a virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "❌ Not in a virtual environment!"
    echo "Please run: python3 -m venv .venv && source .venv/bin/activate"
    exit 1
fi

echo "✅ Virtual environment detected: $VIRTUAL_ENV"

# Install development dependencies
echo "📦 Installing development dependencies..."
pip install -r requirements-dev.txt

echo "✅ Development environment setup complete!"
echo ""
echo "You can now:"
echo "  - Run tests: pytest"
echo "  - Run linting: ruff check ."
echo "  - Run type checking: mypy custom_components/abode_security"
echo "  - Start dev environment: ./scripts/dev.sh"
