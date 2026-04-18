/** @type {import('jest').Config} */
module.exports = {
  preset: "ts-jest",
  testEnvironment: "node",
  testMatch: ["**/electron/__tests__/**/*.test.ts"],
  moduleFileExtensions: ["ts", "js"],
  transform: {
    "^.+\\.ts$": ["ts-jest", { tsconfig: "tsconfig.json" }],
  },
  coverageDirectory: "coverage",
  collectCoverageFrom: [
    "electron/**/*.ts",
    "!electron/__tests__/**",
    "!electron/main.ts",
    "!electron/preload.ts",
  ],
};
