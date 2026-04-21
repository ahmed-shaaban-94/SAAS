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
    // /dashboard is now rendered inside DashboardShell v2 (#573). The
    // NAV_GROUPS entry for /dashboard is labeled "Overview"; the old
    // locator `{ name: "Dashboard" }` substring-matches "My Dashboard"
    // (/my-dashboard) which is not the active link. Use exact:true to
    // keep the test pinned to the correct link.
    await page.goto("/dashboard");
    const overviewLink = page
      .getByRole("navigation", { name: "Primary navigation" })
      .getByRole("link", { name: "Overview", exact: true });
    await expect(overviewLink).toHaveAttribute("aria-current", "page");
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
