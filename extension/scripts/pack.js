/**
 * Pack extension for different browser stores.
 *
 * Usage:
 *   node scripts/pack.js chrome    → bhapi-chrome.zip
 *   node scripts/pack.js firefox   → bhapi-firefox.zip + bhapi-firefox-source.zip
 *   node scripts/pack.js edge      → bhapi-edge.zip
 *   node scripts/pack.js all       → all of the above
 *
 * Uses scripts/zipdir.py to create cross-platform zips with forward slashes.
 * (PowerShell Compress-Archive creates backslash paths that Firefox rejects.)
 */

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const DIST = path.resolve(__dirname, "..", "dist");
const ROOT = path.resolve(__dirname, "..");
const OUT = ROOT;
const ZIPDIR = path.join(__dirname, "zipdir.py");

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
  execSync(`python "${ZIPDIR}" "${sourceDir}" "${zipPath}"`, { stdio: "inherit" });
}

function createSourceZip(zipName) {
  const zipPath = path.join(OUT, zipName);
  const includes = "src icons manifest.json webpack.config.js tsconfig.json package.json package-lock.json";
  execSync(`python "${ZIPDIR}" "${ROOT}" "${zipPath}" --include ${includes}`, { stdio: "inherit" });
}

// --- Chrome / Edge ---
function packChrome(zipName = "bhapi-chrome.zip") {
  console.log(`\nPacking for Chrome/Edge → ${zipName}`);
  const manifest = readManifest();
  delete manifest.browser_specific_settings;
  writeManifest(manifest);
  createZip(zipName, DIST);
}

// --- Firefox ---
function packFirefox() {
  console.log("\nPacking for Firefox → bhapi-firefox.zip");
  const manifest = readManifest();

  manifest.browser_specific_settings = {
    gecko: {
      id: "safety-monitor@bhapi.ai",
      strict_min_version: "109.0",
      data_collection_permissions: {
        required: ["websiteActivity"],
        optional: ["technicalAndInteraction"],
      },
    },
  };

  if (manifest.background && manifest.background.service_worker) {
    manifest.background = {
      scripts: [manifest.background.service_worker],
      type: "module",
    };
  }

  writeManifest(manifest);
  createZip("bhapi-firefox.zip", DIST);

  // Restore original manifest
  delete manifest.browser_specific_settings;
  if (manifest.background && manifest.background.scripts) {
    manifest.background = {
      service_worker: manifest.background.scripts[0],
      type: "module",
    };
  }
  writeManifest(manifest);

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
