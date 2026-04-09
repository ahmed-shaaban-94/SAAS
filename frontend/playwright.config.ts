import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",

  // In CI: mint a NextAuth session cookie before tests run so protected
  // routes are accessible. Skipped in local dev (uses real Auth0 flow).
  globalSetup: process.env.CI ? "./e2e/global-setup.ts" : undefined,

  use: {
    baseURL: "http://localhost:3000",
    // Use the pre-minted session in CI; tests that need a fresh unauthenticated
    // context (auth.spec.ts) override this via browser.newContext({ storageState: undefined }).
    storageState: process.env.CI ? "e2e/.auth/user.json" : undefined,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      // Pixel 5 uses Mobile Chrome (Chromium) — CI only installs Chromium,
      // so iPhone 13 (WebKit) cannot run there.
      name: "mobile",
      use: { ...devices["Pixel 5"] },
    },
  ],
  webServer: {
    command: process.env.CI
      ? "node .next/standalone/server.js"
      : "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
});
