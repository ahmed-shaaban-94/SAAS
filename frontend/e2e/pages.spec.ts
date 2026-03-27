import { test, expect } from "@playwright/test";

const pages = [
  { path: "/products", heading: /product/i },
  { path: "/customers", heading: /customer/i },
  { path: "/staff", heading: /staff/i },
  { path: "/sites", heading: /site/i },
  { path: "/returns", heading: /return/i },
];

test.describe("Analytics Pages", () => {
  for (const { path, heading } of pages) {
    test(`${path} page loads`, async ({ page }) => {
      await page.goto(path);
      await expect(page.locator("h1").first()).toContainText(heading, {
        timeout: 15000,
      });
    });
  }
});
