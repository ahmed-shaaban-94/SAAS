import { test, expect } from "@playwright/test";

test.describe("Pipeline Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/pipeline");
  });

  test("page loads with title", async ({ page }) => {
    await expect(page.locator("h1")).toContainText("Pipeline Status");
  });

  test("trigger button is visible", async ({ page }) => {
    await expect(page.getByRole("button", { name: /trigger/i })).toBeVisible();
  });

  test("pipeline overview cards render", async ({ page }) => {
    const cards = page.getByRole("heading", { level: 2 }).or(page.locator("[class*='bg-card']"));
    await expect(cards.first()).toBeVisible({ timeout: 10000 });
  });

  test("navigation includes pipeline link", async ({ page }) => {
    await expect(page.getByRole("link", { name: "Pipeline" })).toBeVisible();
  });
});
