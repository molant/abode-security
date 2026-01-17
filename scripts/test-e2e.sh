#!/bin/bash
set -e

echo "========================================="
echo "Abode Security E2E Test Runner"
echo "========================================="
echo ""

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose not found"
    exit 1
fi

# Start services
echo "Starting services (HA + Mock Server)..."
docker-compose up -d

# Wait for Home Assistant to be ready
echo "Waiting for Home Assistant to start..."
MAX_WAIT=120
ELAPSED=0
while ! curl -f http://localhost:8123 > /dev/null 2>&1; do
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    if [ $ELAPSED -ge $MAX_WAIT ]; then
        echo "Error: Home Assistant failed to start within ${MAX_WAIT}s"
        docker-compose logs homeassistant
        exit 1
    fi
    echo -n "."
done
echo " Ready!"

# Wait for mock server
echo "Waiting for Mock Server..."
ELAPSED=0
while ! curl -f http://localhost:8000 > /dev/null 2>&1; do
    sleep 1
    ELAPSED=$((ELAPSED + 1))
    if [ $ELAPSED -ge 30 ]; then
        echo "Error: Mock server failed to start"
        exit 1
    fi
done
echo "Mock Server ready!"

# Run Playwright tests
echo ""
echo "Running Playwright tests..."
npm run test:e2e "$@"
TEST_EXIT_CODE=$?

# Cleanup (optional - comment out to leave running for debugging)
# echo ""
# echo "Stopping services..."
# docker-compose down

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "All tests passed!"
else
    echo "Tests failed (exit code: $TEST_EXIT_CODE)"
    echo ""
    echo "To debug:"
    echo "  - View logs: docker-compose logs"
    echo "  - Run UI mode: npm run test:e2e:ui"
    echo "  - View report: npm run test:e2e:report"
fi

exit $TEST_EXIT_CODE
