/**
 * Pack extension for different browser stores.
 *
 * Usage:
 *   node scripts/pack.js chrome    → bhapi-chrome.zip
 *   node scripts/pack.js firefox   → bhapi-firefox.zip + bhapi-firefox-source.zip
 *   node scripts/pack.js edge      → bhapi-edge.zip
 *   node scripts/pack.js all       → all of the above
 */

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const DIST = path.resolve(__dirname, "..", "dist");
const ROOT = path.resolve(__dirname, "..");
const OUT = ROOT; // zips go in extension/

const target = process.argv[2] || "all";

function readManifest() {
  return JSON.parse(fs.readFileSync(path.join(DIST, "manifest.json"), "utf8"));
}

function writeManifest(manifest) {
  fs.writeFileSync(
    path.join(DIST, "manifest.json"),
    JSON.stringify(manifest, null, 2) + "\n"
  );
}

function createZip(zipName, sourceDir) {
  const zipPath = path.join(OUT, zipName);
  // Remove old zip
  if (fs.existsSync(zipPath)) fs.unlinkSync(zipPath);

  // Use PowerShell on Windows, zip on Unix
  if (process.platform === "win32") {
    execSync(
      `powershell -Command "Compress-Archive -Path '${sourceDir}\\*' -DestinationPath '${zipPath}' -Force"`,
      { stdio: "inherit" }
    );
  } else {
    execSync(`cd "${sourceDir}" && zip -r "${zipPath}" . -x "*.d.ts" "*.d.ts.map" "*.map"`, {
      stdio: "inherit",
    });
  }
  const size = (fs.statSync(zipPath).size / 1024).toFixed(1);
  console.log(`  Created: ${zipName} (${size} KB)`);
}

function createSourceZip(zipName) {
  const zipPath = path.join(OUT, zipName);
  if (fs.existsSync(zipPath)) fs.unlinkSync(zipPath);

  // Include source files Firefox reviewers need to rebuild
  const includes = [
    "src",
    "icons",
    "manifest.json",
    "webpack.config.js",
    "tsconfig.json",
    "package.json",
    "package-lock.json",
  ].map((f) => path.join(ROOT, f));

  if (process.platform === "win32") {
    execSync(
      `powershell -Command "Compress-Archive -Path '${includes.join("','")}' -DestinationPath '${zipPath}' -Force"`,
      { stdio: "inherit" }
    );
  } else {
    const paths = includes.map((p) => `"${p}"`).join(" ");
    execSync(`cd "${ROOT}" && zip -r "${zipPath}" src icons manifest.json webpack.config.js tsconfig.json package.json package-lock.json -x "node_modules/*"`, {
      stdio: "inherit",
    });
  }
  const size = (fs.statSync(zipPath).size / 1024).toFixed(1);
  console.log(`  Created: ${zipName} (${size} KB)`);
}

// --- Chrome / Edge (identical format) ---
function packChrome(zipName = "bhapi-chrome.zip") {
  console.log(`\nPacking for Chrome/Edge → ${zipName}`);
  const manifest = readManifest();
  // Remove any Firefox-specific fields
  delete manifest.browser_specific_settings;
  writeManifest(manifest);
  createZip(zipName, DIST);
}

// --- Firefox ---
function packFirefox() {
  console.log("\nPacking for Firefox → bhapi-firefox.zip");
  const manifest = readManifest();

  // Add Firefox-specific settings
  manifest.browser_specific_settings = {
    gecko: {
      id: "safety-monitor@bhapi.ai",
      strict_min_version: "109.0",
    },
  };

  // Firefox MV3 uses background.scripts instead of service_worker
  if (manifest.background && manifest.background.service_worker) {
    manifest.background = {
      scripts: [manifest.background.service_worker],
      type: "module",
    };
  }

  writeManifest(manifest);
  createZip("bhapi-firefox.zip", DIST);

  // Restore original manifest for other builds
  delete manifest.browser_specific_settings;
  if (manifest.background && manifest.background.scripts) {
    manifest.background = {
      service_worker: manifest.background.scripts[0],
      type: "module",
    };
  }
  writeManifest(manifest);

  // Firefox requires source code upload for webpack builds
  console.log("Packing Firefox source → bhapi-firefox-source.zip");
  createSourceZip("bhapi-firefox-source.zip");
}

// --- Main ---
console.log("Bhapi Extension Packager");
console.log("========================");

const targets = target === "all" ? ["chrome", "firefox", "edge"] : [target];

for (const t of targets) {
  switch (t) {
    case "chrome":
      packChrome("bhapi-chrome.zip");
      break;
    case "edge":
      packChrome("bhapi-edge.zip");
      break;
    case "firefox":
      packFirefox();
      break;
    default:
      console.error(`Unknown target: ${t}`);
      process.exit(1);
  }
}

console.log("\nDone! Upload the zip files to the respective stores.");
