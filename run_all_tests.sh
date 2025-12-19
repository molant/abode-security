#!/bin/bash
# Script to run all tests (unit + integration) with mock server

set -e

echo "========================================="
echo "Running Full Test Suite"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    echo "Please start Docker and try again"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping mock server..."
    docker-compose down > /dev/null 2>&1 || true
}

# Register cleanup function to run on exit
trap cleanup EXIT

# Start mock server
echo "Starting mock server..."
docker-compose up -d

# Wait for mock server to be ready
echo "Waiting for mock server to be ready..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}Mock server is ready!${NC}"
        echo ""
        break
    fi
    attempt=$((attempt + 1))
    if [ $attempt -eq $max_attempts ]; then
        echo -e "${RED}Error: Mock server failed to start after ${max_attempts} seconds${NC}"
        exit 1
    fi
    sleep 1
done

# Run all tests (override default -m 'not integration')
echo "Running all tests (unit + integration)..."
echo ""

# Set PYTHONPATH to include vendored libraries
export PYTHONPATH="$(pwd)/custom_components:$PYTHONPATH"

# Run pytest with coverage, including integration tests
if python3 -m pytest tests/ -v --cov=custom_components/abode_security --cov-report=term-missing -m ''; then
    echo ""
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}All tests passed!${NC}"
    echo -e "${GREEN}=========================================${NC}"
    exit 0
else
    exit_code=$?
    echo ""
    echo -e "${RED}=========================================${NC}"
    echo -e "${RED}Some tests failed${NC}"
    echo -e "${RED}=========================================${NC}"
    exit $exit_code
fi
