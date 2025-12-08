#!/bin/bash
set -e

# ============================================================================
# YNOT GitHub Release Script
# ============================================================================
#
# Prerequisites:
#   - GitHub CLI installed: brew install gh
#   - Authenticated: gh auth login
#   - Built and notarized app in dist/
#
# Usage:
#   ./release.sh 0.1.0
#   ./release.sh 0.1.0 "Bug fixes and improvements"
#
# ============================================================================

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo_step() { echo -e "${GREEN}==>${NC} $1"; }
echo_error() { echo -e "${RED}Error:${NC} $1"; exit 1; }

# Get version from argument
VERSION="${1:?Usage: ./release.sh <version> [release notes]}"
NOTES="${2:-Release v$VERSION}"

# Validate version format
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo_error "Version must be in format X.Y.Z (e.g., 0.1.0)"
fi

TAG="v$VERSION"
DMG_PATH="dist/ynot.dmg"
APP_PATH="dist/ynot.app"

# Check prerequisites
command -v gh >/dev/null 2>&1 || echo_error "GitHub CLI not installed. Run: brew install gh"
[ -f "$DMG_PATH" ] || echo_error "DMG not found at $DMG_PATH. Run ./build_macos.sh first"

# Check if authenticated
gh auth status >/dev/null 2>&1 || echo_error "Not authenticated. Run: gh auth login"

# Update version in pyproject.toml
echo_step "Updating version to $VERSION..."
sed -i '' "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml

# Update version in spec file
sed -i '' "s/'CFBundleVersion': '.*'/'CFBundleVersion': '$VERSION'/" ynot.spec
sed -i '' "s/'CFBundleShortVersionString': '.*'/'CFBundleShortVersionString': '$VERSION'/" ynot.spec

# Stage changes
echo_step "Staging version changes..."
git add pyproject.toml ynot.spec

# Commit
echo_step "Committing..."
git commit -m "Release $TAG" || echo "No changes to commit"

# Create and push tag
echo_step "Creating tag $TAG..."
git tag -a "$TAG" -m "Release $TAG"

echo_step "Pushing to origin..."
git push origin main
git push origin "$TAG"

# Create GitHub release with DMG
echo_step "Creating GitHub release..."
gh release create "$TAG" \
    --title "YNOT $TAG" \
    --notes "$NOTES" \
    "$DMG_PATH"

echo ""
echo_step "Release complete!"
echo ""
echo "Release URL: $(gh release view "$TAG" --json url -q .url)"

