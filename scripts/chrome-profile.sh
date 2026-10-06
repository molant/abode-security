#!/bin/bash
# Create tmp Chrome profile and launch for easier debugging.
# Opens http://$DEPLOY_HOST:8123, with DEPLOY_HOST read from .deploy.env.

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "$PROJECT_ROOT/.deploy.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/.deploy.env"
  set +a
fi
: "${DEPLOY_HOST:?DEPLOY_HOST not set. Copy .deploy.env.example to .deploy.env and edit, or set in env.}"

# Create a temporary Chrome profile directory
mkdir -p /tmp/chrome-debug-profile

# Copy your authentication data from your regular Chrome profile
cp -r ~/Library/Application\ Support/Google/Chrome/Default/Cookies /tmp/chrome-debug-profile/ 2>/dev/null || true
cp -r ~/Library/Application\ Support/Google/Chrome/Default/Cookies-journal /tmp/chrome-debug-profile/ 2>/dev/null || true

# Kill existing Chrome and start with temp profile + remote debugging
pkill -9 "Google Chrome" 2>/dev/null
sleep 2

/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --user-data-dir=/tmp/chrome-debug-profile \
  --remote-debugging-port=9222 \
  "http://${DEPLOY_HOST}:8123"
