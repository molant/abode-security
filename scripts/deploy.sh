#!/bin/bash
# Deploy the custom_components/abode_security tree to a running Home Assistant
# instance over SSH/rsync. Config comes from environment variables, sourced from
# .deploy.env at the project root if present (see .deploy.env.example).
#
# Usage:
#   ./scripts/deploy.sh                  # rsync + restart
#   ./scripts/deploy.sh --no-restart     # rsync only
#   ./scripts/deploy.sh --dry-run        # show what would change, no transfer
#   DEPLOY_HOST=ha.lan ./scripts/deploy.sh   # override per-invocation
#
# Required env vars (set in .deploy.env or your shell):
#   DEPLOY_HOST   SSH host or IP of the HA instance (e.g. 192.168.1.60)
#   DEPLOY_USER   SSH user on that host (e.g. molant)
#
# Optional:
#   DEPLOY_PATH   Remote install path. Default: /homeassistant/custom_components/abode_security

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# Source .deploy.env if present. Use `set -a` so every var becomes exported and
# visible to subsequent commands without prefixing each line with `export`.
if [ -f .deploy.env ]; then
    set -a
    # shellcheck disable=SC1091
    source .deploy.env
    set +a
fi

# Parse flags
RESTART=1
DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --no-restart) RESTART=0 ;;
        --dry-run)    DRY_RUN=1 ;;
        -h|--help)
            # Print the header comment block (lines 2 through the first blank
            # comment-free line) with the leading `# ` stripped. Walks until
            # the first non-comment line so adding/removing header lines
            # doesn't silently truncate `--help`.
            awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "$0"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown flag: $arg${NC}" >&2
            exit 2
            ;;
    esac
done

# Required vars (also needed for --dry-run so the preview targets the real host).
: "${DEPLOY_HOST:?DEPLOY_HOST not set. Copy .deploy.env.example to .deploy.env and edit, or set in env.}"
: "${DEPLOY_USER:?DEPLOY_USER not set. Copy .deploy.env.example to .deploy.env and edit, or set in env.}"
: "${DEPLOY_PATH:=/homeassistant/custom_components/abode_security}"

# Refuse to rsync --delete against a non-leaf path. Without this guard, a typo
# like `DEPLOY_PATH=/homeassistant` would wipe the entire HA config dir on the
# remote. The integration's install location is always .../custom_components/
# abode_security; anything else is almost certainly a mistake.
case "$DEPLOY_PATH" in
    */custom_components/abode_security|*/custom_components/abode_security/) ;;
    *)
        echo -e "${RED}Refusing: DEPLOY_PATH must end in /custom_components/abode_security${NC}" >&2
        echo "  got: $DEPLOY_PATH" >&2
        echo "  this guard exists because rsync --delete would otherwise nuke whatever lives at the wrong path." >&2
        exit 2
        ;;
esac

echo -e "${GREEN}=========================================${NC}"
echo "Deploying custom_components/abode_security"
echo "  to: ${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}"
if [ "$DRY_RUN" = "1" ]; then
    echo -e "  ${YELLOW}(dry run — no files will be transferred)${NC}"
fi
echo -e "${GREEN}=========================================${NC}"

# rsync flags:
#   -a  archive (preserve perms, symlinks, etc.)
#   -v  verbose
#   -z  compress in transit
#   --delete                     prune files on remote that no longer exist locally
#   --exclude='__pycache__'      skip Python bytecode caches from dev venv
#   --exclude='*.pyc'            (defensive — usually inside __pycache__ but not always)
#   --exclude='.*.swp'           vim swap files if you edit on the local checkout
RSYNC_ARGS=(-avz --delete --exclude='__pycache__' --exclude='*.pyc' --exclude='.*.swp')
if [ "$DRY_RUN" = "1" ]; then
    RSYNC_ARGS+=(--dry-run)
fi

# Trailing slash on source is intentional: "rsync foo/ user@host:bar/" syncs
# the *contents* of foo into bar. Without it, foo itself would be created
# inside bar (one level too deep).
rsync "${RSYNC_ARGS[@]}" \
    custom_components/abode_security/ \
    "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}/"

if [ "$DRY_RUN" = "1" ]; then
    echo ""
    echo -e "${YELLOW}Dry run complete — no files transferred and no restart issued.${NC}"
    exit 0
fi

if [ "$RESTART" = "1" ]; then
    echo ""
    echo "Restarting Home Assistant core..."
    ssh "${DEPLOY_USER}@${DEPLOY_HOST}" 'ha core restart'
    echo -e "${GREEN}Restart issued. Tail logs with: ssh ${DEPLOY_USER}@${DEPLOY_HOST} 'ha core logs -f'${NC}"
else
    echo ""
    echo -e "${YELLOW}Skipped restart (--no-restart). Restart manually when ready.${NC}"
fi

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Deploy complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
