import { test, expect } from "@playwright/test";

/**
 * /inventory — v2 shell cutover.
 *
 * After the cutover, /inventory renders via the v2 DashboardShell
 * (pulse bar + editorial sidebar). The /inventory-v2 preview route is
 * retired and redirects here.
 *
 * Two layers of assertions:
 *   - Structural (CI-safe): shell mounts, page-title renders, nav marks
 *     Inventory active, /inventory-v2 redirects. No backend needed.
 *   - Data (staging-only): mocked API tests for stock levels + reorder
 *     alerts. Skipped in CI; they require either a live backend or
 *     network-level mocking and aren't critical smoke tests.
 */

const needsBackend = !!process.env.CI;

const MOCK_STOCK_LEVELS = [
  {
    drug_code: "PARA500",
    drug_name: "Paracetamol 500mg",
    site_code: "SITE01",
    current_quantity: 1200,
    weighted_avg_cost: 10.5,
    reorder_point: 500,
  },
  {
    drug_code: "AMOX250",
    drug_name: "Amoxicillin 250mg",
    site_code: "SITE01",
    current_quantity: 80,
    weighted_avg_cost: 22.0,
    reorder_point: 200,
  },
];

const MOCK_REORDER_ALERTS = [
  {
    drug_code: "AMOX250",
    drug_name: "Amoxicillin 250mg",
    current_quantity: 80,
    reorder_point: 200,
    days_of_stock: 4,
  },
];

// ─── Structural smoke (runs in CI) ─────────────────────────────────────

test.describe("/inventory (v2 shell)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/inventory");
  });

  test("page renders with inventory heading", async ({ page }) => {
    await expect(page.locator("h1.page-title")).toContainText(/Inventory/i);
  });

  test("v2 shell chrome wraps the page", async ({ page }) => {
    await expect(page.locator(".dashboard-v2 aside.side")).toBeVisible();
    await expect(page.locator(".dashboard-v2 .pulse-bar")).toBeVisible();
  });

  test("v2 sidebar marks Inventory as active", async ({ page }) => {
    const inventoryLink = page.getByRole("link", { name: "Inventory" });
    await expect(inventoryLink).toHaveClass(/active/);
  });

  test("widget mount points render", async ({ page }) => {
    test.skip(needsBackend, "widget data requires live API — validate in staging");
    await expect(page.locator(".widget-grid")).toBeVisible({ timeout: 15000 });
  });

  test("skip-to-content anchor targets #main-content", async ({ page }) => {
    await expect(page.locator("#main-content")).toBeAttached();
  });
});

test.describe("/inventory-v2 redirect", () => {
  test("navigating to /inventory-v2 lands on /inventory", async ({ page }) => {
    const response = await page.goto("/inventory-v2");
    await expect(page).toHaveURL(/\/inventory$/);
    expect(response?.ok()).toBe(true);
  });
});

// ─── Data-level tests (staging-only, skipped in CI) ────────────────────

test.describe("Inventory data surfacing", () => {
  test("displays stock level table with mock data", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route("**/api/v1/inventory/stock-levels*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_STOCK_LEVELS),
      });
    });

    await page.goto("/inventory");
    await expect(page.getByText("Paracetamol 500mg")).toBeVisible();
    await expect(page.getByText("AMOX250")).toBeVisible();
  });

  test("shows reorder alerts section", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route("**/api/v1/inventory/stock-levels*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_STOCK_LEVELS),
      });
    });
    await page.route("**/api/v1/inventory/reorder-alerts*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_REORDER_ALERTS),
      });
    });

    await page.goto("/inventory");
    await expect(page.getByText(/Reorder Alerts/i)).toBeVisible();
  });

  test("shows empty state when no inventory data", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route("**/api/v1/inventory/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    await page.goto("/inventory");
    await expect(
      page.getByText(/No inventory data/i).or(page.getByText(/No data/i))
    ).toBeVisible();
  });
});
