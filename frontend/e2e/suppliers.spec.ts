import { test, expect } from "@playwright/test";

const needsBackend = !!process.env.CI;

const MOCK_SUPPLIERS = [
  {
    supplier_code: "SUP001",
    supplier_name: "PharmaCorp International",
    contact_name: "Ahmed Hassan",
    contact_email: "ahmed@pharmacorp.com",
    payment_terms_days: 30,
    lead_time_days: 7,
    is_active: true,
  },
  {
    supplier_code: "SUP002",
    supplier_name: "MediSupply Ltd",
    contact_name: "Sara Mohamed",
    contact_email: "sara@medisupply.com",
    payment_terms_days: 45,
    lead_time_days: 14,
    is_active: true,
  },
];

test.describe("Suppliers", () => {
  test("navigates to suppliers page", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");
    await page.goto("/suppliers");
    await expect(page).toHaveURL(/\/suppliers/);
    await expect(
      page.getByRole("heading", { name: /Suppliers/i })
    ).toBeVisible();
  });

  test("displays supplier table", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route("**/api/v1/suppliers*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_SUPPLIERS),
      });
    });

    await page.goto("/suppliers");
    await expect(page.getByText("PharmaCorp International")).toBeVisible();
    await expect(page.getByText("MediSupply Ltd")).toBeVisible();
  });

  test("shows supplier contact information", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route("**/api/v1/suppliers*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_SUPPLIERS),
      });
    });

    await page.goto("/suppliers");
    await expect(page.getByText("Ahmed Hassan")).toBeVisible();
  });

  test("shows lead time and payment terms", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route("**/api/v1/suppliers*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_SUPPLIERS),
      });
    });

    await page.goto("/suppliers");
    // Look for lead time or payment terms data
    await expect(
      page.getByText(/30/).or(page.getByText(/7 days/i))
    ).toBeVisible();
  });
});
