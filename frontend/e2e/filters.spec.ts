import { test, expect } from "@playwright/test";

test.describe("Filters", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/dashboard");
  });

  test("date preset buttons are clickable", async ({ page }) => {
    const presetButton = page.getByText("30D").or(page.getByText("90D")).first();
    await expect(presetButton).toBeVisible({ timeout: 10000 });
    await presetButton.click();
    // After clicking, the page should still be functional (no crash)
    await expect(page.locator("h1")).toContainText("Executive Overview");
  });
});
