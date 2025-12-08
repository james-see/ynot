#!/bin/bash
set -e

# ============================================================================
# YNOT macOS Build, Sign & Notarize Script
# ============================================================================
# 
# Prerequisites:
#   1. PyInstaller installed: pip install pyinstaller
#   2. Developer ID Application certificate installed in Keychain
#   3. Environment variables set (see .env.example)
#
# Usage:
#   source .env
#   ./build_macos.sh
#
# ============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_step() {
    echo -e "${GREEN}==>${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}Warning:${NC} $1"
}

echo_error() {
    echo -e "${RED}Error:${NC} $1"
}

# ============================================================================
# Configuration
# ============================================================================

APP_NAME="ynot"
BUNDLE_ID="com.ynot.app"
ENTITLEMENTS="entitlements.plist"

# These should be set via environment variables
: "${APPLE_TEAM_ID:?Please set APPLE_TEAM_ID environment variable}"
: "${APPLE_API_KEY_ID:?Please set APPLE_API_KEY_ID environment variable}"
: "${APPLE_API_ISSUER_ID:?Please set APPLE_API_ISSUER_ID environment variable}"
: "${APPLE_API_KEY_PATH:?Please set APPLE_API_KEY_PATH environment variable}"

# Derive signing identity from keychain
SIGNING_IDENTITY=$(security find-identity -v -p codesigning | grep "Developer ID Application" | head -1 | sed 's/.*"\(.*\)".*/\1/')

if [ -z "$SIGNING_IDENTITY" ]; then
    echo_error "No Developer ID Application certificate found in keychain"
    echo "Please install your Developer ID certificate first."
    exit 1
fi

echo_step "Using signing identity: $SIGNING_IDENTITY"

# ============================================================================
# Clean previous builds
# ============================================================================

echo_step "Cleaning previous builds..."
rm -rf build dist "${APP_NAME}.app" "${APP_NAME}.zip" "${APP_NAME}.dmg"

# ============================================================================
# Build with PyInstaller
# ============================================================================

echo_step "Building app with PyInstaller..."
pyinstaller --clean --noconfirm ynot.spec

# ============================================================================
# Sign the application
# ============================================================================

APP_PATH="dist/${APP_NAME}.app"

if [ ! -d "$APP_PATH" ]; then
    echo_error "App bundle not found at $APP_PATH"
    exit 1
fi

echo_step "Signing embedded binaries and frameworks..."

# Find and sign all Mach-O binaries, dylibs, and frameworks
find "$APP_PATH" -type f \( -name "*.dylib" -o -name "*.so" -o -perm +111 \) | while read -r binary; do
    # Check if it's a Mach-O file
    if file "$binary" | grep -q "Mach-O"; then
        echo "  Signing: $binary"
        codesign --force --options runtime --timestamp \
            --entitlements "$ENTITLEMENTS" \
            --sign "$SIGNING_IDENTITY" \
            "$binary" 2>/dev/null || true
    fi
done

# Sign frameworks
find "$APP_PATH" -type d -name "*.framework" | while read -r framework; do
    echo "  Signing framework: $framework"
    codesign --force --options runtime --timestamp \
        --entitlements "$ENTITLEMENTS" \
        --sign "$SIGNING_IDENTITY" \
        "$framework" 2>/dev/null || true
done

# Sign the main executable
echo_step "Signing main executable..."
codesign --force --options runtime --timestamp \
    --entitlements "$ENTITLEMENTS" \
    --sign "$SIGNING_IDENTITY" \
    "$APP_PATH/Contents/MacOS/${APP_NAME}"

# Sign the entire app bundle
echo_step "Signing app bundle..."
codesign --force --deep --options runtime --timestamp \
    --entitlements "$ENTITLEMENTS" \
    --sign "$SIGNING_IDENTITY" \
    "$APP_PATH"

# Verify signature
echo_step "Verifying signature..."
codesign --verify --deep --strict --verbose=2 "$APP_PATH"

# Check Gatekeeper acceptance
echo_step "Checking Gatekeeper acceptance..."
spctl --assess --type execute --verbose "$APP_PATH" || echo_warn "Gatekeeper check failed (expected before notarization)"

# ============================================================================
# Create ZIP for notarization
# ============================================================================

echo_step "Creating ZIP archive for notarization..."
cd dist
ditto -c -k --keepParent "${APP_NAME}.app" "${APP_NAME}.zip"
cd ..

ZIP_PATH="dist/${APP_NAME}.zip"

# ============================================================================
# Submit for notarization
# ============================================================================

echo_step "Submitting for notarization..."
echo "This may take several minutes..."

NOTARIZE_OUTPUT=$(xcrun notarytool submit "$ZIP_PATH" \
    --key "$APPLE_API_KEY_PATH" \
    --key-id "$APPLE_API_KEY_ID" \
    --issuer "$APPLE_API_ISSUER_ID" \
    --wait 2>&1)

echo "$NOTARIZE_OUTPUT"

# Check if notarization succeeded
if echo "$NOTARIZE_OUTPUT" | grep -q "status: Accepted"; then
    echo_step "Notarization successful!"
else
    echo_error "Notarization failed. Check the output above for details."
    
    # Extract submission ID for log retrieval
    SUBMISSION_ID=$(echo "$NOTARIZE_OUTPUT" | grep "id:" | head -1 | awk '{print $2}')
    if [ -n "$SUBMISSION_ID" ]; then
        echo_step "Fetching notarization log..."
        xcrun notarytool log "$SUBMISSION_ID" \
            --key "$APPLE_API_KEY_PATH" \
            --key-id "$APPLE_API_KEY_ID" \
            --issuer "$APPLE_API_ISSUER_ID"
    fi
    exit 1
fi

# ============================================================================
# Staple the notarization ticket
# ============================================================================

echo_step "Stapling notarization ticket to app..."
xcrun stapler staple "$APP_PATH"

# Verify stapling
echo_step "Verifying stapled app..."
xcrun stapler validate "$APP_PATH"

# Final Gatekeeper check
echo_step "Final Gatekeeper verification..."
spctl --assess --type execute --verbose "$APP_PATH"

# ============================================================================
# Create distributable DMG (optional)
# ============================================================================

echo_step "Creating DMG..."
DMG_PATH="dist/${APP_NAME}.dmg"

# Create a temporary directory for DMG contents
DMG_TEMP="dist/dmg_temp"
mkdir -p "$DMG_TEMP"
cp -R "$APP_PATH" "$DMG_TEMP/"

# Create symlink to Applications
ln -s /Applications "$DMG_TEMP/Applications"

# Create DMG
hdiutil create -volname "$APP_NAME" -srcfolder "$DMG_TEMP" -ov -format UDZO "$DMG_PATH"

# Clean up temp directory
rm -rf "$DMG_TEMP"

# Sign the DMG
echo_step "Signing DMG..."
codesign --force --sign "$SIGNING_IDENTITY" "$DMG_PATH"

# Notarize the DMG
echo_step "Notarizing DMG..."
xcrun notarytool submit "$DMG_PATH" \
    --key "$APPLE_API_KEY_PATH" \
    --key-id "$APPLE_API_KEY_ID" \
    --issuer "$APPLE_API_ISSUER_ID" \
    --wait

# Staple the DMG
echo_step "Stapling DMG..."
xcrun stapler staple "$DMG_PATH"

# ============================================================================
# Done!
# ============================================================================

echo ""
echo_step "Build complete!"
echo ""
echo "Outputs:"
echo "  - App:  $APP_PATH"
echo "  - DMG:  $DMG_PATH"
echo ""
echo "The app is now signed, notarized, and ready for distribution."
echo "Users will no longer see Gatekeeper warnings when installing."

