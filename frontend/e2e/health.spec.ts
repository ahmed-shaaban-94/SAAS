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
  test("v2 shell renders (sidebar + pulse bar mount)", async ({ page }) => {
    // Post-#502 the /dashboard route owns its own layout (no v2 shell).
    // /inventory still renders the shared v2 shell, so we smoke-test the
    // pulse-bar + sidebar there.
    await page.goto("/inventory");
    await expect(page.locator(".dashboard-v2 aside.side")).toBeVisible({
      timeout: 15000,
    });
    await expect(page.locator(".dashboard-v2 .pulse-bar")).toBeVisible();
  });

  test("new dashboard layout mounts at /dashboard", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(
      page.getByRole("heading", { level: 1, name: /Daily operations overview/ }),
    ).toBeVisible({ timeout: 15000 });
  });
});
