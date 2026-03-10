#!/bin/bash
# ---------------------------------------------------------------------------
# Bhapi AI Safety Monitor — Safari Extension Converter
#
# Converts the shared Manifest V3 web extension into a Safari Web Extension
# Xcode project using Apple's safari-web-extension-converter tool.
#
# Requirements:
#   - macOS 12+ with Xcode 14+ installed
#   - safari-web-extension-converter (ships with Xcode)
#   - Apple Developer account (for signing)
#
# Usage:
#   cd extension/safari && ./convert.sh
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$SCRIPT_DIR/build"
XCODE_DIR="$SCRIPT_DIR/xcode"

echo "=== Bhapi Safari Extension Converter ==="
echo ""

# Verify we are on macOS
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Error: Safari extension conversion requires macOS."
  echo "This script must be run on a Mac with Xcode installed."
  exit 1
fi

# Verify xcrun is available
if ! command -v xcrun &> /dev/null; then
  echo "Error: xcrun not found. Please install Xcode command-line tools:"
  echo "  xcode-select --install"
  exit 1
fi

# Verify safari-web-extension-converter is available
if ! xcrun --find safari-web-extension-converter &> /dev/null; then
  echo "Error: safari-web-extension-converter not found."
  echo "Please install Xcode 14+ from the Mac App Store."
  exit 1
fi

# Step 1: Build the shared extension if dist/ does not exist
if [ ! -d "$EXT_DIR/dist" ]; then
  echo "Building shared extension..."
  (cd "$EXT_DIR" && npm run build)
  echo ""
fi

# Step 2: Clean previous build
echo "Cleaning previous Safari build..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Step 3: Copy built extension to Safari build directory
echo "Copying extension build output..."
cp -r "$EXT_DIR/dist/"* "$BUILD_DIR/"

# Step 4: Overlay Safari-specific manifest
echo "Applying Safari manifest overrides..."
cp "$SCRIPT_DIR/manifest.json" "$BUILD_DIR/manifest.json"

# Step 5: Copy Safari polyfill
if [ -f "$SCRIPT_DIR/browser-polyfill.js" ]; then
  echo "Including browser polyfill..."
  cp "$SCRIPT_DIR/browser-polyfill.js" "$BUILD_DIR/browser-polyfill.js"
fi

# Step 6: Copy declarativeNetRequest rules
if [ -d "$SCRIPT_DIR/declarativeNetRequest" ]; then
  echo "Including declarativeNetRequest rules..."
  cp -r "$SCRIPT_DIR/declarativeNetRequest" "$BUILD_DIR/declarativeNetRequest"
fi

# Step 7: Copy Safari Xcode extension handler
if [ -d "$SCRIPT_DIR/SafariBhapiExtension" ]; then
  echo "Including native extension handler..."
  mkdir -p "$BUILD_DIR/SafariBhapiExtension"
  cp -r "$SCRIPT_DIR/SafariBhapiExtension/"* "$BUILD_DIR/SafariBhapiExtension/"
fi

# Step 8: Run the converter
echo ""
echo "Running safari-web-extension-converter..."
echo "  Source: $BUILD_DIR"
echo "  Output: $XCODE_DIR"
echo ""

rm -rf "$XCODE_DIR"

xcrun safari-web-extension-converter "$BUILD_DIR" \
  --project-location "$XCODE_DIR" \
  --app-name "Bhapi AI Safety Monitor" \
  --bundle-identifier "ai.bhapi.safari-extension" \
  --no-prompt \
  --no-open

echo ""
echo "=== Safari extension conversion complete ==="
echo ""
echo "Next steps:"
echo "  1. Open the Xcode project: open $XCODE_DIR/*.xcodeproj"
echo "  2. Select your Apple Developer signing team"
echo "  3. Build and run (Cmd+R)"
echo "  4. Enable the extension in Safari > Settings > Extensions"
