#!/bin/bash
# Quiet commit wrapper for Claude - reduces token usage
# Full output saved to /tmp/commit-output.log

# Pass all arguments to git commit, capture output
OUTPUT_FILE="/tmp/commit-output.log"
git commit "$@" > "$OUTPUT_FILE" 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  echo "✓ Pre-commit passed"
else
  echo "✗ Pre-commit failed. Output:"
  echo ""
  cat "$OUTPUT_FILE"
fi

exit $EXIT_CODE
