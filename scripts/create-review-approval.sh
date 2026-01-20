#!/bin/bash
# Creates a JSON marker for pre-commit review
#
# Usage: ./scripts/create-review-approval.sh <STATUS>
#   STATUS must be "APPROVED" or "BLOCKED"
#
# This script is called by the main Claude agent after the pre-commit-review
# subagent completes its analysis. The workflow is:
#   1. Main agent runs pre-commit-review subagent
#   2. Subagent returns status (APPROVED/BLOCKED) and findings
#   3. Main agent calls this script with the status
#   4. Script creates JSON marker file with hash of staged changes
#   5. Main agent displays review to user and waits for confirmation
#   6. User confirms, main agent retries commit
#   7. Hook checks marker file status, allows commit if APPROVED
#   8. Hook cleans up marker file after successful commit
#
# Example:
#   ./scripts/create-review-approval.sh APPROVED
#   ./scripts/create-review-approval.sh BLOCKED

set -e

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
  echo "Error: Not in a git repository"
  exit 1
fi

STATUS="${1}"

if [ -z "$STATUS" ]; then
  echo "Error: Status parameter required (APPROVED or BLOCKED)"
  exit 1
fi

if [ "$STATUS" != "APPROVED" ] && [ "$STATUS" != "BLOCKED" ]; then
  echo "Error: Status must be APPROVED or BLOCKED, got: $STATUS"
  exit 1
fi

# Check if there are staged changes to review
if git diff --staged --quiet 2>/dev/null; then
  echo "Warning: No staged changes to review"
fi

# Calculate hash of staged changes
HASH=$(git diff --staged | shasum | cut -d' ' -f1)
REVIEW_DIR="/tmp"
REVIEW_FILE="$REVIEW_DIR/.claude-review-${HASH}.json"
# Use TZ=UTC for portability across macOS (BSD date) and Linux (GNU date)
TIMESTAMP=$(TZ=UTC date +%Y-%m-%dT%H:%M:%SZ)

# Create the review marker JSON file
cat > "${REVIEW_FILE}" << REVIEW_EOF
{
  "hash": "${HASH}",
  "timestamp": "${TIMESTAMP}",
  "status": "${STATUS}",
  "message": "Review completed"
}
REVIEW_EOF

echo "✓ Created review marker: ${REVIEW_FILE}"
echo "✓ Status: ${STATUS}"
echo "✓ Staged changes hash: ${HASH}"
