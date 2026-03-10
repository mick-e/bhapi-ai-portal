# Bhapi Safari Extension

Safari Web Extension build for the Bhapi AI Safety Monitor.

## Requirements

- **macOS 12+** (Monterey or later)
- **Xcode 14+** with Safari Web Extension support
- **Safari 16+**
- **Apple Developer account** (required for signing the extension)
- `safari-web-extension-converter` (included with Xcode)

## Build Steps

### Option 1: npm script (recommended)

From the `extension/` directory:

```bash
npm run build:safari
```

This builds the shared extension first, then runs the Safari converter.

### Option 2: Manual conversion

```bash
# 1. Build the shared extension
cd extension
npm run build

# 2. Make the convert script executable and run it
cd safari
chmod +x convert.sh
./convert.sh
```

### After conversion

1. Open the generated Xcode project: `open safari/xcode/*.xcodeproj`
2. Select your Apple Developer signing team in Xcode project settings
3. Build and run (Cmd+R)
4. Enable the extension in **Safari > Settings > Extensions**

## Project Structure

```
safari/
  SafariBhapiExtension/
    Info.plist                     # Extension bundle configuration (v2.0.0)
    SafariWebExtensionHandler.swift  # Native message bridge (NSExtensionRequestHandling)
  declarativeNetRequest/
    rules.json                     # Safari-specific header modification rules
  browser-polyfill.js              # browser.* API polyfill for Safari compatibility
  convert.sh                       # Build script using xcrun safari-web-extension-converter
  manifest.json                    # Safari-specific manifest overrides
  README.md                        # This file
```

## Architecture

The Safari extension reuses the same shared source code as the Chrome and Firefox builds. The conversion process:

1. Builds the shared Manifest V3 extension via webpack
2. Copies the built output to `safari/build/`
3. Overlays Safari-specific manifest, polyfill, and declarativeNetRequest rules
4. Runs `xcrun safari-web-extension-converter` to generate an Xcode project
5. The Xcode project includes `SafariWebExtensionHandler.swift` for native messaging

### Native Messaging

The `SafariWebExtensionHandler` Swift class handles messages sent via `browser.runtime.sendNativeMessage()`. Currently supports:

- `STATUS_CHECK` — confirms native messaging is operational
- `GET_NATIVE_CAPABILITIES` — reports available native features

### Browser Polyfill

`browser-polyfill.js` maps Safari's API surface to the standard `browser.*` namespace. It handles:

- `browser.runtime` — messaging, getURL, native messaging
- `browser.storage.local` — get, set, remove with localStorage fallback

Modern Safari (15.4+) exposes `chrome.*` APIs natively; the polyfill detects this and aliases directly.

## Notes

- The shared extension source is browser-agnostic (Chrome/Firefox/Safari)
- Safari Web Extensions use the same Manifest V3 format
- `declarativeNetRequest` rules add an `X-Bhapi-Extension: safari/2.0.0` header to AI platform requests
- The `build/` and `xcode/` directories are build artifacts (gitignored)
- You must run `chmod +x convert.sh` before first use on a fresh clone
