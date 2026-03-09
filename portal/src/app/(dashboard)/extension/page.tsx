"use client";

import { useState } from "react";

const BROWSERS = [
  {
    name: "Chrome",
    icon: "chrome",
    url: "#",
    instructions: [
      "Click the download link above",
      "Click 'Add to Chrome' in the Chrome Web Store",
      "Click the bhapi extension icon in your toolbar",
      "Enter your setup code to pair the extension",
    ],
  },
  {
    name: "Firefox",
    icon: "firefox",
    url: "#",
    instructions: [
      "Click the download link above",
      "Click 'Add to Firefox'",
      "Click the bhapi extension icon",
      "Enter your setup code to pair",
    ],
  },
  {
    name: "Safari",
    icon: "safari",
    url: "#",
    instructions: [
      "Open Safari Preferences then Extensions",
      "Search for 'bhapi'",
      "Enable the extension",
      "Enter your setup code to pair",
    ],
  },
];

export default function ExtensionPage() {
  const [selectedBrowser, setSelectedBrowser] = useState<string>("Chrome");
  const browser =
    BROWSERS.find((b) => b.name === selectedBrowser) || BROWSERS[0];

  return (
    <div className="max-w-2xl mx-auto py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">
        Install Browser Extension
      </h1>
      <p className="text-gray-500 mb-8">
        The bhapi browser extension monitors AI platform usage and enforces
        blocking rules on your family members&apos; devices.
      </p>

      {/* Browser selector */}
      <div className="flex gap-3 mb-8">
        {BROWSERS.map((b) => (
          <button
            key={b.name}
            onClick={() => setSelectedBrowser(b.name)}
            className={`flex items-center gap-2 px-4 py-3 rounded-lg border transition-colors ${
              selectedBrowser === b.name
                ? "bg-primary-50 border-primary-300 text-primary-700"
                : "bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
            }`}
          >
            <span className="font-medium">{b.name}</span>
          </button>
        ))}
      </div>

      {/* Instructions */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Setup Instructions for {browser.name}
        </h2>
        <ol className="space-y-4">
          {browser.instructions.map((step, i) => (
            <li key={i} className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary-100 text-primary-700 text-sm font-medium flex items-center justify-center">
                {i + 1}
              </span>
              <span className="text-gray-700">{step}</span>
            </li>
          ))}
        </ol>
      </div>

      {/* Setup code section */}
      <div className="mt-8 bg-amber-50 border border-amber-200 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-amber-900 mb-2">
          Need a Setup Code?
        </h3>
        <p className="text-amber-700 text-sm mb-4">
          Go to the Members page, select a member, and click &quot;Generate
          Setup Code&quot; to create a pairing code for their device.
        </p>
        <a
          href="/members"
          className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm font-medium"
        >
          Go to Members
        </a>
      </div>
    </div>
  );
}
