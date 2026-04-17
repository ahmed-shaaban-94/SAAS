import { test, expect } from "@playwright/test";

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

test.describe("Inventory Management", () => {
  test("navigates to inventory page", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");
    await page.goto("/dashboard/inventory");
    await expect(page).toHaveURL(/\/inventory/);
    await expect(
      page.getByRole("heading", { name: /Inventory/i })
    ).toBeVisible();
  });

  test("displays stock level table with mock data", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route("**/api/v1/inventory/stock-levels*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_STOCK_LEVELS),
      });
    });

    await page.goto("/dashboard/inventory");
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

    await page.goto("/dashboard/inventory");
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

    await page.goto("/dashboard/inventory");
    await expect(
      page.getByText(/No inventory data/i).or(page.getByText(/No data/i))
    ).toBeVisible();
  });
});
