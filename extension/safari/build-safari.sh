#!/bin/bash
# Build Safari extension from shared Chrome extension source
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$SCRIPT_DIR/build"

echo "Building Bhapi Safari extension..."

# Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy shared extension source
cp -r "$EXT_DIR/src" "$BUILD_DIR/"
cp "$SCRIPT_DIR/manifest.json" "$BUILD_DIR/"
cp -r "$EXT_DIR/icons" "$BUILD_DIR/" 2>/dev/null || true

echo "Source copied to $BUILD_DIR"
echo ""
echo "Next steps:"
echo "1. Run: xcrun safari-web-extension-converter $BUILD_DIR --project-location $SCRIPT_DIR/xcode"
echo "2. Open the Xcode project and build"
