#!/bin/bash
# shellcheck shell=bash

# Script to create a proper GitHub release with automatic semantic versioning
# Based on conventional commits since the last version bump

set -e  # Exit on error

# Get current working directory
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_error() {
    echo -e "${RED}Error: $1${NC}" >&2
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# ============================================================================
# 1. VALIDATION CHECKS
# ============================================================================

log_info "Running validation checks..."

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    log_error "Working tree is dirty. Commit or stash changes before creating a release."
    git status --short
    exit 1
fi

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    log_error "GitHub CLI (gh) is not installed!"
    echo "Install it with: brew install gh"
    exit 1
fi

# Check if user is authenticated with GitHub
if ! gh auth status &> /dev/null; then
    log_error "Not authenticated with GitHub CLI"
    echo "Run: gh auth login"
    exit 1
fi

# Check if integration folder exists
if [ ! -d "custom_components/abode_security" ]; then
    log_error "custom_components/abode_security not found!"
    exit 1
fi

# Check if CHANGELOG.md exists
if [ ! -f "CHANGELOG.md" ]; then
    log_error "CHANGELOG.md not found!"
    exit 1
fi

log_success "All validation checks passed"

# ============================================================================
# 2. GET CURRENT VERSION AND FIND LAST BUMP COMMIT
# ============================================================================

log_info "Calculating version bump..."

MANIFEST_FILE="custom_components/abode_security/manifest.json"
CURRENT_VERSION=$(python3 -c "import json, sys; print(json.load(open(sys.argv[1]))['version'])" "$MANIFEST_FILE" 2>/dev/null || echo "1.0.0")

# Strip any pre-release suffix for base version
BASE_VERSION=$(echo "$CURRENT_VERSION" | sed -E 's/-.*$//')

# Find the last bump commit
LAST_BUMP_COMMIT=$(git log --grep="^bump:" --format="%H" -n 1 2>/dev/null || echo "")

if [ -z "$LAST_BUMP_COMMIT" ]; then
    # No previous bump commit, use all commits
    COMMIT_RANGE="HEAD"
else
    COMMIT_RANGE="${LAST_BUMP_COMMIT}..HEAD"
fi

# Get all commits since last bump (excluding merge commits)
COMMITS=$(git log "$COMMIT_RANGE" --format="%s" --no-merges 2>/dev/null || echo "")

# Filter out bump and misc commits, and check if anything remains
FILTERED_COMMITS=$(echo "$COMMITS" | grep -v "^bump:" | grep -v "^misc:" | grep -v "^$" || echo "")

if [ -z "$FILTERED_COMMITS" ]; then
    log_info "Nothing to release (no commits with feat, fix, or breaking changes since last version)"
    exit 0
fi

# ============================================================================
# 3. DETERMINE VERSION BUMP TYPE
# ============================================================================

BUMP_TYPE="patch"  # Default to patch

# Check for breaking changes (highest priority)
if echo "$FILTERED_COMMITS" | grep -qE "^(breaking:|BREAKING CHANGE:)"; then
    BUMP_TYPE="major"
# Check for features (medium priority)
elif echo "$FILTERED_COMMITS" | grep -qE "^(feat|feature)(\([^)]+\))?:"; then
    BUMP_TYPE="minor"
fi

# Parse base version
IFS='.' read -r MAJOR MINOR PATCH <<< "$BASE_VERSION"

# Calculate new version
case $BUMP_TYPE in
    major)
        NEW_VERSION="$((MAJOR + 1)).0.0"
        ;;
    minor)
        NEW_VERSION="${MAJOR}.$((MINOR + 1)).0"
        ;;
    patch)
        NEW_VERSION="${MAJOR}.${MINOR}.$((PATCH + 1))"
        ;;
esac

log_success "Version: $CURRENT_VERSION → $NEW_VERSION (bump type: $BUMP_TYPE)"

# ============================================================================
# 4. GENERATE CHANGELOG ENTRY
# ============================================================================

log_info "Generating changelog entry..."

CHANGELOG_DATE=$(date +"%Y-%m-%d")
CHANGELOG_ENTRY="## v${NEW_VERSION} (${CHANGELOG_DATE})"

# Add breaking changes section
BREAKING_CHANGES=$(echo "$FILTERED_COMMITS" | grep -E "^(breaking:|BREAKING CHANGE:)" || echo "")
if [ -n "$BREAKING_CHANGES" ]; then
    CHANGELOG_ENTRY="${CHANGELOG_ENTRY}

### Breaking Changes"
    while IFS= read -r commit; do
        if [ -n "$commit" ]; then
            DESC=$(echo "$commit" | sed -E 's/^(breaking:|BREAKING CHANGE:)\s*//')
            CHANGELOG_ENTRY="${CHANGELOG_ENTRY}
- ${DESC}"
        fi
    done <<< "$BREAKING_CHANGES"
fi

# Add features section
FEATURES=$(echo "$FILTERED_COMMITS" | grep -E "^(feat|feature)(\([^)]+\))?:" || echo "")
if [ -n "$FEATURES" ]; then
    CHANGELOG_ENTRY="${CHANGELOG_ENTRY}

### Features"
    while IFS= read -r commit; do
        if [ -n "$commit" ]; then
            DESC=$(echo "$commit" | sed -E 's/^(feat|feature)(\([^)]+\))?:\s*//')
            CHANGELOG_ENTRY="${CHANGELOG_ENTRY}
- ${DESC}"
        fi
    done <<< "$FEATURES"
fi

# Add fixes section
FIXES=$(echo "$FILTERED_COMMITS" | grep -E "^fix(\([^)]+\))?:" || echo "")
if [ -n "$FIXES" ]; then
    CHANGELOG_ENTRY="${CHANGELOG_ENTRY}

### Fixes"
    while IFS= read -r commit; do
        if [ -n "$commit" ]; then
            DESC=$(echo "$commit" | sed -E 's/^fix(\([^)]+\))?:\s*//')
            CHANGELOG_ENTRY="${CHANGELOG_ENTRY}
- ${DESC}"
        fi
    done <<< "$FIXES"
fi

# Add other changes section
OTHERS=$(echo "$FILTERED_COMMITS" | grep -vE "^(breaking:|BREAKING CHANGE:|feat|feature|fix)(\([^)]+\))?:" | grep -vE "^(test|docs|chore|ci|refactor)(\([^)]+\))?:" || echo "")
if [ -n "$OTHERS" ]; then
    CHANGELOG_ENTRY="${CHANGELOG_ENTRY}

### Other Changes"
    while IFS= read -r commit; do
        if [ -n "$commit" ]; then
            CHANGELOG_ENTRY="${CHANGELOG_ENTRY}
- ${commit}"
        fi
    done <<< "$OTHERS"
fi

echo ""
echo "Changelog entry:"
echo "----------------------------------------"
echo "$CHANGELOG_ENTRY"
echo "----------------------------------------"
echo ""

# ============================================================================
# 5. CONFIRM BEFORE PROCEEDING
# ============================================================================

read -p "Proceed with release v${NEW_VERSION}? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

# ============================================================================
# 6. UPDATE FILES
# ============================================================================

log_info "Updating files..."

# Update manifest.json version using environment variables to avoid injection
export MANIFEST_FILE NEW_VERSION
python3 -c '
import json
import os

manifest_file = os.environ["MANIFEST_FILE"]
new_version = os.environ["NEW_VERSION"]

with open(manifest_file, "r") as f:
    data = json.load(f)
data["version"] = new_version
with open(manifest_file, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
'

# Update CHANGELOG.md - insert changelog entry before the first version section (## [...])
# The CHANGELOG has a header block (title + description), then version sections starting with "## "
CHANGELOG_TEMP=$(mktemp)
FIRST_VERSION_LINE=$(grep -n "^## \[" CHANGELOG.md | head -1 | cut -d: -f1)

if [ -n "$FIRST_VERSION_LINE" ]; then
    # Insert before the first version section
    head -n $((FIRST_VERSION_LINE - 1)) CHANGELOG.md > "$CHANGELOG_TEMP"
    echo "$CHANGELOG_ENTRY" >> "$CHANGELOG_TEMP"
    echo "" >> "$CHANGELOG_TEMP"
    tail -n +"$FIRST_VERSION_LINE" CHANGELOG.md >> "$CHANGELOG_TEMP"
else
    # No version sections found, append to end
    cat CHANGELOG.md > "$CHANGELOG_TEMP"
    echo "" >> "$CHANGELOG_TEMP"
    echo "$CHANGELOG_ENTRY" >> "$CHANGELOG_TEMP"
fi
mv "$CHANGELOG_TEMP" CHANGELOG.md

log_success "Files updated"

# ============================================================================
# 7. BUILD FRONTEND
# ============================================================================

log_info "Building frontend..."

cd frontend
npm run build
cd "$REPO_DIR"

if [ ! -f "custom_components/abode_security/www/abode-security-panel.js" ]; then
    log_error "Frontend build failed - panel JS not found!"
    exit 1
fi

log_success "Build complete"

# ============================================================================
# 8. GIT COMMIT AND PUSH
# ============================================================================

log_info "Committing changes..."

git add "$MANIFEST_FILE" CHANGELOG.md custom_components/abode_security/www/abode-security-panel.js

git commit -m "bump: v${NEW_VERSION}"

BRANCH=$(git rev-parse --abbrev-ref HEAD)
git push origin "$BRANCH"

log_success "Changes committed and pushed"

# ============================================================================
# 9. CREATE RELEASE ZIP
# ============================================================================

log_info "Creating release zip..."

ZIP_FILE="/tmp/abode_security.zip"
rm -f "$ZIP_FILE"
cd custom_components
# Exclude: bytecode, cache, macOS files, node_modules (if any leaked), source maps
# The frontend/dist exclusion is a safety measure in case old build artifacts exist
zip -r "$ZIP_FILE" abode_security -x "*.pyc" -x "*__pycache__*" -x "*.DS_Store" -x "*node_modules*" -x "*/frontend/dist/*" -x "*.map"
cd "$REPO_DIR"

# ============================================================================
# 10. CREATE GITHUB RELEASE
# ============================================================================

log_info "Creating GitHub release..."

# Prepare release notes
RELEASE_NOTES=$(printf '%s\n\n---\n\n**Installation:**\n1. Download `abode_security.zip`\n2. Extract to `custom_components/` in your HA config folder\n3. Restart Home Assistant' "$CHANGELOG_ENTRY")

# Create release with built file
gh release create "v${NEW_VERSION}" \
    --title "v${NEW_VERSION}" \
    --notes "$RELEASE_NOTES" \
    "$ZIP_FILE"

rm -f "$ZIP_FILE"

log_success "Release created successfully!"

REPO_URL=$(gh repo view --json url -q '.url')
echo ""
echo "Release: ${REPO_URL}/releases/tag/v${NEW_VERSION}"
