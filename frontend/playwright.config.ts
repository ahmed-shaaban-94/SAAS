import { defineConfig, devices } from "@playwright/test";

const isCi = !!process.env.CI;

// Mobile project uses a narrow viewport where the sidebar is a drawer —
// tests that assert sidebar elements fail because the drawer is closed.
// Run mobile tests locally with a real backend; CI runs only chromium.
const projects = [
  {
    name: "chromium",
    use: { ...devices["Desktop Chrome"] },
  },
  ...(isCi
    ? []
    : [
        {
          name: "mobile",
          use: { ...devices["Pixel 5"] },
        },
      ]),
];

export default defineConfig({
  testDir: "./e2e",
  // Exclude real-backend smoke tests — they need a live API and run in the
  // dedicated e2e-real-backend CI job (playwright.real-backend.config.ts).
  testIgnore: ["**/api-smoke.spec.ts"],
  fullyParallel: true,
  forbidOnly: isCi,
  retries: isCi ? 1 : 0,
  workers: isCi ? 1 : undefined,
  reporter: "html",

  // In CI: mint a NextAuth session cookie before tests run so protected
  // routes are accessible. Skipped in local dev (uses real Auth0 flow).
  globalSetup: isCi ? "./e2e/global-setup.ts" : undefined,

  use: {
    baseURL: "http://localhost:3000",
    // Use the pre-minted session in CI; tests that need a fresh unauthenticated
    // context (auth.spec.ts) override this via browser.newContext({ storageState: undefined }).
    storageState: isCi ? "e2e/.auth/user.json" : undefined,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects,
  webServer: {
    command: isCi ? "node .next/standalone/server.js" : "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !isCi,
    timeout: 120000,
  },
});
