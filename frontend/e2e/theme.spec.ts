import { test, expect } from "@playwright/test";

test.describe("Theme Toggle", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/dashboard");
  });

  test("theme toggle button exists in sidebar", async ({ page }) => {
    // The theme toggle button shows "Light Mode" when dark (default) or "Dark Mode" when light
    const themeButton = page
      .getByRole("button", { name: /Light Mode|Dark Mode/i });
    await expect(themeButton).toBeVisible({ timeout: 10000 });
  });

  test("clicking toggle switches theme class on html element", async ({ page }) => {
    // Default theme is dark — html element should have class "dark"
    await expect(page.locator("html")).toHaveClass(/dark/);

    // Click the theme toggle to switch to light
    const themeButton = page.getByRole("button", { name: /Light Mode/i });
    await expect(themeButton).toBeVisible({ timeout: 10000 });
    await themeButton.click();

    // html element should now have class "light" and not "dark"
    await expect(page.locator("html")).toHaveClass(/light/);

    // Button text should now say "Dark Mode"
    await expect(
      page.getByRole("button", { name: /Dark Mode/i })
    ).toBeVisible();
  });

  test("theme persists when navigating to a different page", async ({ page }) => {
    // Switch to light theme
    const themeButton = page.getByRole("button", { name: /Light Mode/i });
    await expect(themeButton).toBeVisible({ timeout: 10000 });
    await themeButton.click();
    await expect(page.locator("html")).toHaveClass(/light/);

    // Navigate to Products page
    await page.getByRole("link", { name: "Products" }).click();
    await expect(page).toHaveURL(/\/products/);

    // Theme should still be light after navigation
    await expect(page.locator("html")).toHaveClass(/light/);
    await expect(
      page.getByRole("button", { name: /Dark Mode/i })
    ).toBeVisible();
  });
});
