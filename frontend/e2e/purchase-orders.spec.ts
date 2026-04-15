import { test, expect } from "@playwright/test";

const needsBackend = !!process.env.CI;

const MOCK_PO_LIST = [
  {
    po_number: "PO-2025-001",
    po_date: "2025-06-01",
    supplier_code: "SUP001",
    supplier_name: "PharmaCorp",
    status: "partial",
    total_amount: 5500.0,
    expected_date: "2025-06-10",
  },
  {
    po_number: "PO-2025-002",
    po_date: "2025-06-05",
    supplier_code: "SUP002",
    supplier_name: "MediSupply",
    status: "draft",
    total_amount: 12000.0,
    expected_date: "2025-06-15",
  },
];

test.describe("Purchase Orders", () => {
  test("navigates to purchase orders page", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");
    await page.goto("/dashboard/purchase-orders");
    await expect(page).toHaveURL(/\/purchase-orders/);
    await expect(
      page.getByRole("heading", { name: /Purchase Orders/i })
    ).toBeVisible();
  });

  test("displays PO list table", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route("**/api/v1/purchase-orders*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_PO_LIST),
      });
    });

    await page.goto("/dashboard/purchase-orders");
    await expect(page.getByText("PO-2025-001")).toBeVisible();
    await expect(page.getByText("PharmaCorp")).toBeVisible();
  });

  test("shows PO status indicators", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route("**/api/v1/purchase-orders*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_PO_LIST),
      });
    });

    await page.goto("/dashboard/purchase-orders");
    await expect(page.getByText(/partial/i)).toBeVisible();
    await expect(page.getByText(/draft/i)).toBeVisible();
  });

  test("shows empty state when no purchase orders", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route("**/api/v1/purchase-orders*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    await page.goto("/dashboard/purchase-orders");
    await expect(
      page
        .getByText(/No purchase orders/i)
        .or(page.getByText(/No data/i))
    ).toBeVisible();
  });
});
