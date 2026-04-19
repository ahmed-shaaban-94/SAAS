import { test, expect } from "@playwright/test";

test.describe("Marketing SEO", () => {
  test("meta title and description present", async ({ page }) => {
    await page.goto("/");
    const title = await page.title();
    expect(title).toContain("DataPulse");

    // Loosened: editorial landing v2 metadata focuses on "pharmacy /
    // transactions / heartbeat" copy rather than "sales". Keep the
    // assertion about presence + brand-relevant substring rather than a
    // single fragile keyword.
    const description = page.locator('meta[name="description"]');
    await expect(description).toHaveAttribute(
      "content",
      /pharmacy|transactions|sales|business/i,
    );
  });

  test("Open Graph tags present", async ({ page }) => {
    await page.goto("/");

    const ogTitle = page.locator('meta[property="og:title"]');
    await expect(ogTitle).toHaveAttribute("content", /DataPulse/i);

    const ogType = page.locator('meta[property="og:type"]');
    await expect(ogType).toHaveAttribute("content", "website");
  });

  test("JSON-LD script tag present", async ({ page }) => {
    await page.goto("/");

    const jsonLd = page.locator('script[type="application/ld+json"]');
    const count = await jsonLd.count();
    expect(count).toBeGreaterThanOrEqual(2); // Organization + WebSite + FAQPage
  });

  test("robots meta allows indexing on public pages", async ({ page }) => {
    await page.goto("/");

    // Should NOT have noindex
    const robots = page.locator('meta[name="robots"]');
    const count = await robots.count();
    if (count > 0) {
      const content = await robots.getAttribute("content");
      expect(content).not.toContain("noindex");
    }
  });

  test("sitemap.xml is accessible", async ({ page }) => {
    const response = await page.goto("/sitemap.xml");
    expect(response?.status()).toBe(200);
  });

  test("robots.txt is accessible", async ({ page }) => {
    const response = await page.goto("/robots.txt");
    expect(response?.status()).toBe(200);
  });
});
