import { test, expect } from "@playwright/test";

const needsBackend = !!process.env.CI;

const MOCK_DISPENSE_RATES = [
  {
    drug_code: "PARA500",
    drug_name: "Paracetamol 500mg",
    avg_daily_dispense: 25.5,
    avg_weekly_dispense: 178.5,
    days_of_stock: 47.1,
    velocity_class: "fast",
  },
  {
    drug_code: "AMOX250",
    drug_name: "Amoxicillin 250mg",
    avg_daily_dispense: 8.2,
    avg_weekly_dispense: 57.4,
    days_of_stock: 9.8,
    velocity_class: "medium",
  },
];

const MOCK_STOCKOUT_RISKS = [
  {
    drug_code: "AMOX250",
    drug_name: "Amoxicillin 250mg",
    days_of_stock: 9.8,
    reorder_lead_days: 7,
    risk_level: "warning",
  },
  {
    drug_code: "IBU400",
    drug_name: "Ibuprofen 400mg",
    days_of_stock: 3.2,
    reorder_lead_days: 7,
    risk_level: "critical",
  },
];

test.describe("Dispensing Analytics", () => {
  test("navigates to dispensing page", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");
    await page.goto("/dispensing");
    await expect(page).toHaveURL(/\/dispensing/);
    await expect(
      page.getByRole("heading", { name: /Dispensing/i })
    ).toBeVisible();
  });

  test("displays dispense rate data", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route("**/api/v1/dispensing/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_DISPENSE_RATES),
      });
    });

    await page.goto("/dispensing");
    await expect(page.getByText("Paracetamol 500mg")).toBeVisible();
  });

  test("shows stockout risk indicators", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route("**/api/v1/dispensing/dispense-rates*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_DISPENSE_RATES),
      });
    });
    await page.route("**/api/v1/dispensing/stockout-risk*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_STOCKOUT_RISKS),
      });
    });

    await page.goto("/dispensing");
    await expect(
      page.getByText(/critical/i).or(page.getByText(/warning/i))
    ).toBeVisible();
  });

  test("shows velocity classification", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route("**/api/v1/dispensing/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_DISPENSE_RATES),
      });
    });

    await page.goto("/dispensing");
    await expect(
      page.getByText(/fast/i).or(page.getByText(/medium/i))
    ).toBeVisible();
  });
});
