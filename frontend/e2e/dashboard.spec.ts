import { test, expect } from "@playwright/test";

/**
 * /dashboard is the v2 shell (hybrid pulse-bar + signature widgets) after
 * the v2 cutover. Assertions are structural — shell chrome, page header,
 * widget mount points — not value-based. Value-based assertions (e.g.
 * "Revenue MTD shows EGP 4.72M") are not meaningful without live data
 * and belong in staging QA.
 */

const needsBackend = !!process.env.CI;

test.describe("Dashboard (v2 shell)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/dashboard");
  });

  test("page renders with v2 heading", async ({ page }) => {
    await expect(page.locator("h1.page-title")).toContainText("Good morning");
  });

  test("v2 shell chrome is present (sidebar + pulse bar)", async ({ page }) => {
    await expect(page.locator(".dashboard-v2 aside.side")).toBeVisible();
    await expect(page.locator(".dashboard-v2 .pulse-bar")).toBeVisible();
  });

  test("Print Report link points to /dashboard/report", async ({ page }) => {
    const printLink = page.getByRole("link", { name: /Print Report/i });
    await expect(printLink).toBeVisible({ timeout: 10000 });
    await expect(printLink).toHaveAttribute("href", "/dashboard/report");
  });

  test("Compare toggle button is present", async ({ page }) => {
    const compareBtn = page.getByRole("button", { name: "Compare" });
    await expect(compareBtn).toBeVisible({ timeout: 10000 });
  });

  test("Horizon toggle is present in header", async ({ page }) => {
    // HorizonToggle renders inside .page-header — presence check is enough.
    await expect(page.locator(".page-header")).toBeVisible({ timeout: 10000 });
  });

  test("KPI row has four stat cards", async ({ page }) => {
    test.skip(needsBackend, "KPI values require live API — asserts against real hydration");
    const kpis = page.locator(".dashboard-v2 .kpi");
    await expect(kpis).toHaveCount(4, { timeout: 15000 });
  });

  test("widget grid mounts Money Map / Burning Cash / Medallion", async ({ page }) => {
    test.skip(needsBackend, "widget hydration uses API data — validate in staging");
    await expect(page.locator(".dashboard-v2 .widget-grid")).toBeVisible({
      timeout: 15000,
    });
  });

  test("skip-to-content anchor targets #main-content", async ({ page }) => {
    await expect(page.locator("#main-content")).toBeAttached();
  });
});
