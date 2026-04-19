import { test, expect } from "@playwright/test";

/**
 * /insights renders on the v2 shell (post-cutover).
 * AnalyticsSectionHeader renders its own h2 for each section; the h1
 * is the v2 page-title "Insights."
 */

const needsBackend = !!process.env.CI;

test.describe("Insights Page (v2 shell)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/insights");
  });

  test("page renders with v2 heading", async ({ page }) => {
    await expect(page.locator("h1.page-title")).toContainText(/Insights/i);
  });

  test("v2 shell chrome wraps the page", async ({ page }) => {
    await expect(page.locator(".dashboard-v2 aside.side")).toBeVisible();
    await expect(page.locator(".dashboard-v2 .pulse-bar")).toBeVisible();
  });

  test("v2 sidebar marks Insights as active", async ({ page }) => {
    const link = page.getByRole("link", { name: "Insights" });
    await expect(link).toHaveClass(/active/);
  });

  test("AI summary card renders", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend — run against staging");
    const card = page.getByRole("heading", { level: 2 }).or(page.locator("[class*='bg-card']"));
    await expect(card.first()).toBeVisible({ timeout: 10000 });
  });
});
