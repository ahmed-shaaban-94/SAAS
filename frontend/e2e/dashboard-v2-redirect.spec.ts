import { test, expect } from "@playwright/test";

/**
 * The v2 cutover retired the `/dashboard-v2` preview URL in favour of
 * `/dashboard`. A permanent (308) redirect is wired in `next.config.mjs`
 * so bookmarks and external links keep working.
 */

test.describe("/dashboard-v2 redirect", () => {
  test("navigating to /dashboard-v2 lands on /dashboard", async ({ page }) => {
    const response = await page.goto("/dashboard-v2");
    await expect(page).toHaveURL(/\/dashboard$/);
    // Permanent redirect — either 308 (Next.js default) or 301 is fine.
    // Intermediate responses show on the nav response; the final landing
    // response is 200 on /dashboard itself. Asserting URL is sufficient.
    expect(response?.ok()).toBe(true);
  });
});
