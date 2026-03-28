import { test, expect } from "@playwright/test";

test.describe("AI Insights Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/insights");
  });

  test("page loads with title", async ({ page }) => {
    await expect(page.locator("h1")).toContainText("AI Insights");
  });

  test("AI summary card renders", async ({ page }) => {
    const card = page.getByRole("heading", { level: 2 }).or(page.locator("[class*='bg-card']"));
    await expect(card.first()).toBeVisible({ timeout: 10000 });
  });

  test("navigation includes insights link", async ({ page }) => {
    await expect(page.getByRole("link", { name: "Insights" })).toBeVisible();
  });

  test("insights link is active when on page", async ({ page }) => {
    const link = page.getByRole("link", { name: "Insights" });
    await expect(link).toHaveClass(/text-accent/);
  });
});
