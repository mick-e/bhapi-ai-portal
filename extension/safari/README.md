# Bhapi Safari Extension

## Build Requirements
- macOS 12+ with Xcode 14+
- Safari 16+
- `safari-web-extension-converter` (included with Xcode)

## Build Steps

1. Ensure the Chrome extension builds successfully first
2. Run the build script: `./build-safari.sh`
3. Open the generated Xcode project
4. Sign with your Apple Developer certificate
5. Build and run in Safari

## Notes
- The extension source is browser-agnostic (shared with Chrome/Firefox)
- Safari Web Extensions use the same Manifest V3 format
- `declarativeNetRequest` rules may need adjustment for Safari
