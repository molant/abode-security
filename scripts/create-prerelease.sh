#!/bin/bash
# shellcheck shell=bash

# Script to create a GitHub pre-release for HACS integration testing

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

# Get current date/time in format: YYYYMMDD-HHMM
DATE_TIME=$(date +"%Y%m%d-%H%M")

# Get current branch name
BRANCH=$(git rev-parse --abbrev-ref HEAD)

# ============================================================================
# 1. VALIDATION CHECKS (fail fast - check prerequisites before doing work)
# ============================================================================

log_info "Running validation checks..."

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    log_error "GitHub CLI (gh) is not installed!"
    echo "Install it with: brew install gh"
    exit 1
fi

# Check if user is authenticated
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

log_success "All validation checks passed"

# ============================================================================
# 2. CHECK FOR UNCOMMITTED CHANGES
# ============================================================================

if [ -n "$(git status --porcelain)" ]; then
    echo ""
    log_info "Uncommitted changes detected:"
    echo ""
    git status --short
    echo ""
    read -p "Commit and push all changes before creating release? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        log_info "Staging all changes..."
        git add -A

        log_info "Committing changes..."
        COMMIT_MSG="Pre-release: ${DATE_TIME}"
        if ! git commit -m "${COMMIT_MSG}"; then
            log_error "Commit failed. This may be due to:"
            echo "  - Pre-commit hooks failing (check output above)"
            echo "  - No changes to commit"
            echo "  - Git configuration issues"
            exit 1
        fi

        log_info "Pushing to ${BRANCH}..."
        if ! git push origin "${BRANCH}"; then
            log_error "Push failed. Please check your git configuration."
            exit 1
        fi

        # Make sure working tree is clean after the commit
        if [ -n "$(git status --porcelain)" ]; then
            log_error "Working tree is still dirty after commit."
            git status --short
            exit 1
        fi

        log_success "Changes committed and pushed successfully!"
        echo ""
    else
        log_error "Cannot create a pre-release without committing/pushing changes."
        exit 1
    fi
else
    log_info "No uncommitted changes detected."
    echo ""
fi

# Get current commit hash (short) - updated after potential push
COMMIT=$(git rev-parse --short HEAD)

# Get commit message (first line)
COMMIT_MSG=$(git log -1 --pretty=%B | head -n 1)

# Get version from manifest.json using command-line argument to avoid injection
VERSION=$(python3 -c "import json, sys; print(json.load(open(sys.argv[1]))['version'])" "custom_components/abode_security/manifest.json" 2>/dev/null || echo "1.0.0")

# Create tag name: v1.0.0-pre-20250116-1430
TAG_NAME="v${VERSION}-pre-${DATE_TIME}"

# Create release title
TITLE="${TAG_NAME} - Pre-release"

# Create release notes
NOTES="Pre-release build from branch \`${BRANCH}\`

**Commit:** \`${COMMIT}\`
**Branch:** \`${BRANCH}\`
**Date:** $(date +"%Y-%m-%d %H:%M:%S")

**Latest commit message:**
${COMMIT_MSG}

---

**Installation:**
1. Download \`abode_security.zip\`
2. Extract to \`custom_components/\` in your HA config folder
3. Restart Home Assistant

This is a pre-release for testing. Use with caution."

# ============================================================================
# 3. BUILD FRONTEND
# ============================================================================

log_info "Building frontend..."
cd frontend
npm run build
cd "$REPO_DIR"

if [ ! -f "custom_components/abode_security/www/abode-security-panel.js" ]; then
    log_error "Frontend build failed - panel JS not found!"
    exit 1
fi

log_success "Frontend build complete"

# ============================================================================
# 4. CREATE ZIP FILE
# ============================================================================

ZIP_FILE="/tmp/abode_security.zip"
log_info "Creating release zip..."
rm -f "$ZIP_FILE"
cd custom_components
# Exclude: bytecode, cache, macOS files, node_modules (if any leaked), source maps
# The frontend/dist exclusion is a safety measure in case old build artifacts exist
zip -r "$ZIP_FILE" abode_security -x "*.pyc" -x "*__pycache__*" -x "*.DS_Store" -x "*node_modules*" -x "*/frontend/dist/*" -x "*.map"
cd "$REPO_DIR"

log_success "Zip file created"

# ============================================================================
# 5. CONFIRM AND CREATE RELEASE
# ============================================================================

echo ""
echo "=========================================="
echo "Creating GitHub Pre-Release"
echo "=========================================="
echo "Tag:        ${TAG_NAME}"
echo "Branch:     ${BRANCH}"
echo "Commit:     ${COMMIT}"
echo "Version:    ${VERSION}"
echo "Date/Time:  ${DATE_TIME}"
echo ""
echo "Release will include:"
echo "  - abode_security.zip (integration folder)"
echo ""
read -p "Create pre-release? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    rm -f "$ZIP_FILE"
    exit 1
fi

# Create the pre-release
echo ""
log_info "Creating pre-release..."
gh release create "${TAG_NAME}" \
    --target "${BRANCH}" \
    --prerelease \
    --title "${TITLE}" \
    --notes "${NOTES}" \
    "$ZIP_FILE"

rm -f "$ZIP_FILE"

echo ""
log_success "Pre-release created successfully!"
echo "   Tag: ${TAG_NAME}"
echo "   View: https://github.com/$(gh repo view --json owner,name -q '.owner.login + "/" + .name')/releases/tag/${TAG_NAME}"
