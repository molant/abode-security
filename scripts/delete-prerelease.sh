#!/bin/bash
# shellcheck shell=bash

# Script to delete all GitHub pre-releases and associated tags
# Usage: ./delete-prerelease.sh [--dry-run]

set -e  # Exit on error

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

# Parse arguments
DRY_RUN=false
if [ "$1" = "--dry-run" ] || [ "$1" = "-n" ]; then
    DRY_RUN=true
fi

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

# Get repository info
REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner')

echo "=========================================="
if [ "$DRY_RUN" = true ]; then
    echo "Delete GitHub Pre-Releases (DRY RUN)"
else
    echo "Delete GitHub Pre-Releases and Tags"
fi
echo "=========================================="
echo "Repository: ${REPO}"
echo ""

# Get list of all pre-releases
log_info "Fetching pre-releases..."
PRERELEASE_COUNT=$(gh release list --limit 1000 --json isDraft,isPrerelease,tagName -q '.[] | select(.isPrerelease==true) | .tagName' | wc -l | tr -d ' ')

if [ "$PRERELEASE_COUNT" -eq 0 ]; then
    log_info "No pre-releases found."
    exit 0
fi

echo "Found ${PRERELEASE_COUNT} pre-release(s)"
echo ""
echo "Pre-releases to be deleted:"
gh release list --limit 1000 --json isDraft,isPrerelease,tagName,name -q '.[] | select(.isPrerelease==true) | "  - \(.tagName): \(.name)"'
echo ""

if [ "$DRY_RUN" = true ]; then
    log_info "Dry run complete. No changes were made."
    echo "Run without --dry-run to actually delete these pre-releases."
    exit 0
fi

read -p "Delete all pre-releases and associated tags? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

# Get list of pre-release tags
TAGS=$(gh release list --limit 1000 --json isDraft,isPrerelease,tagName -q '.[] | select(.isPrerelease==true) | .tagName')

# Delete each pre-release and its associated tag
DELETED_COUNT=0
echo ""
log_info "Deleting pre-releases and tags..."
while IFS= read -r TAG; do
    if [ -n "$TAG" ]; then
        echo "  Deleting release ${TAG}..."
        gh release delete "${TAG}" --yes --cleanup-tag
        ((DELETED_COUNT++))
    fi
done <<< "$TAGS"

echo ""
log_success "Successfully deleted ${DELETED_COUNT} pre-release(s) and tag(s)!"
