/** @type {import('jest').Config} */
module.exports = {
  preset: "ts-jest",
  testEnvironment: "node",
  roots: ["<rootDir>/__tests__"],
  moduleFileExtensions: ["ts", "js", "json"],
  transform: {
    "^.+\\.ts$": ["ts-jest", {
      tsconfig: {
        // Override strict settings that conflict with test mocks
        noUnusedLocals: false,
        noUnusedParameters: false,
        strict: true,
        target: "ES2020",
        module: "commonjs",
        esModuleInterop: true,
        moduleResolution: "node",
        types: ["jest", "chrome-types"],
      },
    }],
  },
  setupFiles: ["fake-indexeddb/auto"],
};
