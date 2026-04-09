import { test, expect } from "@playwright/test";

test.describe("Enhancement 3 — Dashboard Upgrades", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/dashboard");
    // Wait for dashboard to load
    await expect(page.locator("h1")).toContainText("Executive Overview");
  });

  test("new KPI cards render (basket size, returns, transactions)", async ({ page }) => {
    // Wait for KPI grid to load
    await expect(page.getByText("Net Sales").first()).toBeVisible({ timeout: 15000 });
    // Check new secondary KPI cards
    await expect(page.getByText("Avg Basket Size")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Daily Returns")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("MTD Transactions")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("YTD Transactions")).toBeVisible({ timeout: 10000 });
  });

  test("tooltip appears on info icon hover", async ({ page }) => {
    await expect(page.getByText("Net Sales").first()).toBeVisible({ timeout: 15000 });
    // Find an info icon button and hover it — must be present (no silent skip)
    const infoButton = page.locator("button[aria-label='Metric info']").first();
    await expect(infoButton).toBeVisible({ timeout: 10000 });
    await infoButton.hover();
    // Tooltip popover should appear
    await expect(page.getByText("Net sales amount")).toBeVisible({ timeout: 5000 });
  });

  test("sparkline SVG exists inside KPI card", async ({ page }) => {
    await expect(page.getByText("Today Net Sales")).toBeVisible({ timeout: 15000 });
    // Sparklines render as Recharts AreaChart SVGs
    const sparklineSvgs = page.locator(".recharts-surface");
    await expect(sparklineSvgs.first()).toBeVisible({ timeout: 10000 });
  });

  test("billing donut chart renders", async ({ page }) => {
    await expect(page.getByText("Billing Method Distribution")).toBeVisible({ timeout: 15000 });
    // Recharts PieChart renders SVG
    const section = page.locator("text=Billing Method Distribution").locator("..");
    await expect(section.locator("svg").first()).toBeVisible({ timeout: 10000 });
  });

  test("customer type stacked bar chart renders", async ({ page }) => {
    await expect(page.getByText("Customer Type Distribution")).toBeVisible({ timeout: 15000 });
  });

  test("compare toggle on trend charts", async ({ page }) => {
    // Find the Compare button on daily trend chart
    const compareBtn = page.getByRole("button", { name: "Compare" }).first();
    await expect(compareBtn).toBeVisible({ timeout: 15000 });
    // Click to activate comparison
    await compareBtn.click();
    // Button should show active state
    await expect(compareBtn).toHaveClass(/text-accent|text-chart-blue/);
  });

  test("top movers card renders", async ({ page }) => {
    await expect(page.getByText("Top Movers")).toBeVisible({ timeout: 15000 });
    // Tab selector should be visible
    await expect(page.getByRole("button", { name: "Products" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Customers" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Staff" })).toBeVisible();
  });
});

test.describe("Enhancement 3 — Products Hierarchy", () => {
  test("product hierarchy toggle and expand/collapse", async ({ page }) => {
    await page.goto("/products");
    await expect(page.locator("h1")).toContainText("Product Analytics");

    // Find hierarchy view toggle — must be present (no silent skip)
    const hierarchyBtn = page.getByRole("button", { name: "Category / Brand" });
    await expect(hierarchyBtn).toBeVisible({ timeout: 10000 });
    await hierarchyBtn.click();
    // Should show category rows with expand icons
    await expect(
      page.locator("button").filter({ has: page.locator("svg") }).first()
    ).toBeVisible({ timeout: 10000 });
  });
});

test.describe("Enhancement 3 — Site Detail Page", () => {
  test("site names are clickable from sites page", async ({ page }) => {
    await page.goto("/sites");
    // Wait for site data to load — must be present (no silent skip)
    const siteLink = page.locator("a[href^='/sites/']").first();
    await expect(siteLink).toBeVisible({ timeout: 15000 });
    await expect(siteLink).toHaveAttribute("href", /\/sites\/\d+/);
  });
});
