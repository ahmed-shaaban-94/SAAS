import { test, expect } from "@playwright/test";

const needsBackend = !!process.env.CI;

test.describe("Navigation", () => {
  test("sidebar links navigate to correct pages", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend — proxy errors cause navigation timeout");
    await page.goto("/dashboard");

    // Navigate to Products
    await page.getByRole("link", { name: "Products" }).click();
    await expect(page).toHaveURL(/\/products/);

    // Navigate to Customers
    await page.getByRole("link", { name: "Customers" }).click();
    await expect(page).toHaveURL(/\/customers/);

    // Navigate to Staff
    await page.getByRole("link", { name: "Staff" }).click();
    await expect(page).toHaveURL(/\/staff/);

    // Navigate to Sites
    await page.getByRole("link", { name: "Sites" }).click();
    await expect(page).toHaveURL(/\/sites/);

    // Navigate to Returns
    await page.getByRole("link", { name: "Returns" }).click();
    await expect(page).toHaveURL(/\/returns/);

    // Navigate back to Overview
    await page.getByRole("link", { name: "Overview" }).click();
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test("active nav item is highlighted", async ({ page }) => {
    await page.goto("/dashboard");
    const overviewLink = page.getByRole("link", { name: "Overview" });
    await expect(overviewLink).toHaveClass(/text-accent/);
  });

  test("root shows landing page", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("h1")).toContainText(/pharma sales and operations data/i, {
      timeout: 15000,
    });
  });
});
