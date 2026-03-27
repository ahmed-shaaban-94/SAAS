import { test, expect } from "@playwright/test";

test.describe("Filters", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/dashboard");
  });

  test("date preset buttons are clickable", async ({ page }) => {
    const presetButton = page
      .getByText("Last 30 days")
      .or(page.getByText("Last 90 days"))
      .first();
    await expect(presetButton).toBeVisible({ timeout: 10000 });
    await presetButton.click();
    // After clicking, the page should still be functional (no crash)
    await expect(page.locator("h1")).toContainText("Executive Overview");
  });

  test("clicking a date preset updates URL search params", async ({ page }) => {
    // Wait for filter bar to be visible
    const last30 = page.getByText("Last 30 days");
    await expect(last30).toBeVisible({ timeout: 10000 });

    // Click "Last 30 days" preset
    await last30.click();

    // URL should now contain start_date and end_date query params
    await page.waitForURL(/start_date=/, { timeout: 5000 });
    const url = new URL(page.url());
    expect(url.searchParams.has("start_date")).toBe(true);
    expect(url.searchParams.has("end_date")).toBe(true);

    // Dates should be in yyyy-MM-dd format
    const startDate = url.searchParams.get("start_date")!;
    const endDate = url.searchParams.get("end_date")!;
    expect(startDate).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(endDate).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  test("clicking a different preset changes the URL params", async ({ page }) => {
    const last7 = page.getByText("Last 7 days");
    await expect(last7).toBeVisible({ timeout: 10000 });

    // Click "Last 7 days"
    await last7.click();
    await page.waitForURL(/start_date=/, { timeout: 5000 });
    const firstUrl = new URL(page.url());
    const firstStart = firstUrl.searchParams.get("start_date")!;

    // Now click "Last 90 days" — start_date should change
    const last90 = page.getByText("Last 90 days");
    await last90.click();
    await page.waitForFunction(
      (prevStart) => {
        const params = new URLSearchParams(window.location.search);
        return params.get("start_date") !== prevStart;
      },
      firstStart,
      { timeout: 5000 },
    );
    const secondUrl = new URL(page.url());
    const secondStart = secondUrl.searchParams.get("start_date")!;
    expect(secondStart).not.toBe(firstStart);
  });

  test("Clear button removes URL search params", async ({ page }) => {
    // First apply a filter
    const last30 = page.getByText("Last 30 days");
    await expect(last30).toBeVisible({ timeout: 10000 });
    await last30.click();
    await page.waitForURL(/start_date=/, { timeout: 5000 });

    // Click Clear
    const clearButton = page.getByText("Clear");
    await expect(clearButton).toBeVisible({ timeout: 5000 });
    await clearButton.click();

    // URL should no longer have filter params
    await page.waitForFunction(
      () => !window.location.search.includes("start_date"),
      undefined,
      { timeout: 5000 },
    );
    const url = new URL(page.url());
    expect(url.searchParams.has("start_date")).toBe(false);
    expect(url.searchParams.has("end_date")).toBe(false);
  });
});
