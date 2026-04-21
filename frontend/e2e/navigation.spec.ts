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
    // /dashboard uses the new design sidebar (#502) which marks the
    // current link with aria-current="page". (The v2 shell's
    // `.active` class is covered indirectly by the /dashboard-v2 →
    // /dashboard redirect spec and by navigation flows below.)
    await page.goto("/dashboard");
    const dashboardLink = page.getByRole("link", { name: "Dashboard" });
    await expect(dashboardLink).toHaveAttribute("aria-current", "page");
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
