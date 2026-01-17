#!/bin/bash

# This hook runs before Bash tool calls
# It checks if the command is a git commit and blocks it,
# instructing Claude to run the pre-commit-review agent first
#
# The review creates a JSON marker file at /tmp/.claude-review-<HASH>.json
# with status "APPROVED" or "BLOCKED" which this hook validates

REVIEW_DIR="/tmp"

# Read the tool input from stdin
INPUT=$(cat)

# Extract the command from the JSON input
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')

# Check if this is a git commit command
# Match git commit with any flags/options between git and commit:
# - git commit
# - git -C /path commit
# - git --git-dir=/path commit
# - git -c user.name="x" commit
if echo "$COMMAND" | grep -qE '\bgit\s+.*\bcommit\b|\bgit\s+commit\b|\./scripts/commit\.sh'; then
  # Extract -C path if present (handles: -C /path, -C=/path, -C/path)
  GIT_DIR_OPTS=""
  if echo "$COMMAND" | grep -qE '\bgit\s+-C\s'; then
    # -C /path format
    GIT_PATH=$(echo "$COMMAND" | sed -n 's/.*\bgit\s\+-C\s\+\([^ ]*\).*/\1/p')
    if [ -n "$GIT_PATH" ]; then
      GIT_DIR_OPTS="-C $GIT_PATH"
    fi
  fi

  # Block compound commands that include both git add and git commit
  # This prevents the bypass where git add && git commit would skip review
  # because staged changes don't exist yet when the hook runs (the add hasn't executed)
  # Pattern matches: git ... add ... (&&|;) ... (git ... commit | ./scripts/commit.sh)
  if echo "$COMMAND" | grep -qE 'git\b.*\badd\b.*(&&|;).*(git\b.*\bcommit\b|\./scripts/commit\.sh)'; then
    cat << 'EOF'
{
  "decision": "block",
  "reason": "Cannot combine 'git add' and 'git commit' in one command. Please run them separately:\n1. First run: git add <files>\n2. Then run: git commit -m \"message\"\n\nThis ensures changes can be reviewed before committing."
}
EOF
    exit 0
  fi

  # Check if we have staged changes to review
  if git $GIT_DIR_OPTS diff --staged --quiet 2>/dev/null; then
    # No staged changes, allow the commit (it will fail naturally)
    exit 0
  fi

  # Calculate hash of staged changes
  STAGED_HASH=$(git $GIT_DIR_OPTS diff --staged | shasum | cut -d' ' -f1)
  REVIEW_FILE="$REVIEW_DIR/.claude-review-$STAGED_HASH.json"

  # Check if this exact set of changes was already reviewed and approved
  if [ -f "$REVIEW_FILE" ]; then
    # Verify the review status using jq
    STATUS=$(jq -r '.status // ""' "$REVIEW_FILE" 2>/dev/null)

    if [ "$STATUS" = "APPROVED" ]; then
      # Approved, allow commit and clean up marker
      rm -f "$REVIEW_FILE"
      exit 0
    fi
  fi

  # Block the commit with explicit workflow instructions
  cat << 'EOF'
{
  "decision": "block",
  "reason": "Pre-commit review required. Follow these steps IN ORDER:\n\n1. Run review: Task tool with subagent_type='pre-commit-review'\n2. WAIT for review output with status (APPROVED/BLOCKED)\n3. Create marker: ./scripts/create-review-approval.sh <STATUS>\n4. DISPLAY complete review to user (all files, findings, status)\n5. WAIT for user confirmation:\n   - APPROVED: Ask 'Would you like to proceed with commit?' and WAIT for explicit confirmation\n   - BLOCKED: Tell user 'Issues found, please fix before committing' and DO NOT retry\n6. Only after user confirms, retry commit\n\nCritical: User MUST explicitly approve before commit, even if review is APPROVED."
}
EOF
  exit 0
fi

# Allow all other commands
exit 0
