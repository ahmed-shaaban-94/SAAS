import { test, expect } from "@playwright/test";

const needsBackend = !!process.env.CI;

const MOCK_EXPIRY_ALERTS = [
  {
    drug_code: "PARA500",
    batch_number: "B2025-001",
    days_to_expiry: 15,
    severity: "critical",
    current_quantity: 50,
  },
  {
    drug_code: "AMOX250",
    batch_number: "B2025-050",
    days_to_expiry: 45,
    severity: "warning",
    current_quantity: 200,
  },
  {
    drug_code: "IBU400",
    batch_number: "B2024-100",
    days_to_expiry: -5,
    severity: "expired",
    current_quantity: 30,
  },
];

test.describe("Expiry & Batch Management", () => {
  test("navigates to expiry page", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");
    await page.goto("/dashboard/expiry");
    await expect(page).toHaveURL(/\/expiry/);
    await expect(
      page.getByRole("heading", { name: /Expiry/i })
    ).toBeVisible();
  });

  test("displays expiry alerts with severity levels", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route("**/api/v1/expiry/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_EXPIRY_ALERTS),
      });
    });

    await page.goto("/dashboard/expiry");
    await expect(page.getByText("B2025-001")).toBeVisible();
    await expect(page.getByText(/critical/i)).toBeVisible();
  });

  test("near-expiry list has time range filters", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route("**/api/v1/expiry/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_EXPIRY_ALERTS),
      });
    });

    await page.goto("/dashboard/expiry");
    // Look for time range tabs/filters (30d, 60d, 90d)
    await expect(
      page
        .getByText(/30/i)
        .or(page.getByRole("tab", { name: /30/i }))
        .or(page.getByRole("button", { name: /30/i }))
    ).toBeVisible();
  });

  test("shows empty state when no expiry data", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route("**/api/v1/expiry/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    await page.goto("/dashboard/expiry");
    await expect(
      page.getByText(/No batch data/i).or(page.getByText(/No data/i))
    ).toBeVisible();
  });
});
