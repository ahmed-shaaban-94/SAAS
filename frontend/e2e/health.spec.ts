import { test, expect } from "@playwright/test";

/**
 * Post-v2 cutover: /dashboard uses the v2 shell which does not render the
 * sidebar-footer "API Connected" / "Offline" / "Checking..." text. API
 * health surfacing on v2 is tracked as a follow-up; for now we only
 * assert that the shell itself renders — the skip-to-content anchor and
 * the pulse-bar are the closest structural proxies.
 *
 * When a dedicated v2 health indicator lands, re-add an assertion against
 * its visible text here.
 */

test.describe("Health Check", () => {
  test("dashboard shell renders (v2 sidebar + pulse bar mount)", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.locator(".dashboard-v2 aside.side")).toBeVisible({
      timeout: 15000,
    });
    await expect(page.locator(".dashboard-v2 .pulse-bar")).toBeVisible();
  });
});
