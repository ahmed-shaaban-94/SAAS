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
    // v2 shell marks the current nav link with class "active" (see
    // src/components/dashboard-v2/shell.tsx `.nav-link.active`).
    const overviewLink = page.getByRole("link", { name: "Overview" });
    await expect(overviewLink).toHaveClass(/active/);
  });

  test("root shows landing page", async ({ page }) => {
    await page.goto("/");
    // Editorial landing v2 (PR #436) renamed the hero. Keep this test
    // about "does the landing page load (not login / error)" rather than
    // about specific hero wording — that belongs in marketing.spec.ts
    // once it is rewritten against the new copy.
    await expect(page.locator("h1")).toBeVisible({ timeout: 15000 });
    // And the route should not have redirected us to /login.
    await expect(page).toHaveURL("/");
  });
});
