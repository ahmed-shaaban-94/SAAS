import { test, expect } from "@playwright/test";

test.describe("Health Check", () => {
  test("API health indicator shows in sidebar", async ({ page }) => {
    await page.goto("/dashboard");
    // The health indicator should show either "API Connected" or "API Offline"
    const healthText = page
      .getByText("API Connected")
      .or(page.getByText("API Offline"))
      .or(page.getByText("Checking..."));
    await expect(healthText).toBeVisible({ timeout: 15000 });
  });
});
