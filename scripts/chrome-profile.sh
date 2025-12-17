#!/bin/bash
# Create tmp Chrome profile and launch for easier debugging

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
  http://192.168.1.60:8123