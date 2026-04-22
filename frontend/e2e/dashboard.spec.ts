import { test, expect } from "@playwright/test";

/**
 * /dashboard — Daily Operations Overview (new design, epic #501/#502).
 *
 * Structural smoke test: confirms the 10 design-handoff widgets all mount
 * without a network error. Value-based assertions (e.g. "Revenue MTD
 * shows EGP 4.72M") are intentionally out of scope — those belong in
 * staging QA where the live pipeline is running.
 */

const needsBackend = !!process.env.CI;

test.describe("Dashboard (new design)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/dashboard");
  });

  test("page renders with greeting + title", async ({ page }) => {
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "Daily operations overview",
    );
  });

  test("primary sidebar navigation is present", async ({ page }) => {
    // After #573 switched /dashboard to DashboardShell v2, NAV_GROUPS
    // labels the /dashboard item "Overview" (not "Dashboard"). "Dashboard"
    // as an accessibility name now substring-matches "My Dashboard"
    // (/my-dashboard) which is NOT the active link.
    const nav = page.getByRole("navigation", { name: "Primary navigation" });
    await expect(nav).toBeVisible();
    await expect(
      nav.getByRole("link", { name: "Overview", exact: true }),
    ).toHaveAttribute("aria-current", "page");
  });

  test("period segmented control has 5 options", async ({ page }) => {
    const tabs = page.getByRole("tablist", { name: "Period" }).getByRole("tab");
    await expect(tabs).toHaveCount(5);
  });

  test("Export and New report actions are in the header", async ({ page }) => {
    await expect(page.getByRole("button", { name: /Export/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /New report/i })).toBeVisible();
  });

  test("four action-center zones mount", async ({ page }) => {
    test.skip(needsBackend, "widget hydration uses API data — validate in staging");
    // Zone 1 — AttentionQueue (hero)
    await expect(page.getByRole("region", { name: "Attention queue" })).toBeVisible({
      timeout: 15000,
    });
    // Zone 2 — KpiStrip
    await expect(
      page.getByRole("region", { name: "Key performance indicators" }),
    ).toBeVisible();
    // Zone 3 Row A — RevenueChart + ExpiryHeatmap
    await expect(page.getByRole("heading", { name: "Revenue trend" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Expiry calendar" })).toBeVisible();
    // Zone 3 Row B — InventoryTable + BranchListRollup
    await expect(
      page.getByRole("heading", { name: "Inventory — reorder watchlist" }),
    ).toBeVisible();
    await expect(page.getByRole("region", { name: "Branches" })).toBeVisible();
    // Zone 4 — DashboardFooterBar
    await expect(page.getByRole("button", { name: /Channels/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /All anomalies/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /All reports/i })).toBeVisible();
  });

  test("expiry calendar exposes 98 grid cells for screen readers", async ({ page }) => {
    test.skip(needsBackend, "widget hydration uses API data — validate in staging");
    const grid = page.getByRole("grid", {
      name: /Expiry severity calendar, 14 weeks/,
    });
    await expect(grid).toBeVisible({ timeout: 15000 });
    await expect(grid.getByRole("gridcell")).toHaveCount(98);
  });

  test("skip-to-content anchor targets #main-content", async ({ page }) => {
    // V2Layout provides the canonical <main#main-content> above the
    // per-route content — scope to the element to avoid strict-mode
    // duplicates that a nested layout could produce.
    await expect(page.locator("main#main-content")).toBeAttached();
  });

  test("no pageerrors and no 5xx on initial render", async ({ page }) => {
    test.skip(needsBackend, "hitting live backend in CI; asserts stable in staging");
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));
    page.on("response", (resp) => {
      if (resp.status() >= 500) errors.push(`${resp.status()} ${resp.url()}`);
    });
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");
    expect(errors, errors.join("\n")).toEqual([]);
  });
});

test.describe("dashboard — Arabic (#604 RTL)", () => {
  test("renders with dir=rtl and Arabic sidebar labels", async ({ page, context }) => {
    await context.addCookies([
      {
        name: "NEXT_LOCALE",
        value: "ar",
        url: "http://localhost:3000",
      },
    ]);
    await page.goto("/dashboard");
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    await expect(page.locator("html")).toHaveAttribute("lang", "ar");
    // At least one sidebar nav label should be Arabic, not English.
    const sidebar = page.locator('[data-testid="sidebar-nav"]');
    await expect(sidebar).toContainText(/لوحة|الفواتير|الإعدادات/);
  });
});
