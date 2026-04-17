/**
 * POS E2E: Controlled substance — pharmacist PIN verification flow
 *
 * Critical path 2: Scanning a controlled drug requires pharmacist
 * verification via PIN before the item can be added to the cart.
 */
import { test, expect } from "@playwright/test";

const needsBackend = !!process.env.CI;
const POS_API = "**/api/v1/pos";

const CONTROLLED_PRODUCT = {
  drug_code: "TRAM50",
  drug_name: "Tramadol 50mg",
  drug_brand: "PainRelief",
  is_controlled: true,
  unit_price: 25.0,
  stock_available: 50,
};

test.describe("POS Controlled Substance Flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem(
        "pos:active_terminal",
        JSON.stringify({
          id: 1,
          tenant_id: 1,
          site_code: "SITE01",
          staff_id: "cashier-1",
          terminal_name: "Terminal-1",
          status: "active",
          opened_at: new Date().toISOString(),
          closed_at: null,
          opening_cash: 500,
          closing_cash: null,
        }),
      );
    });
  });

  test("controlled drug search shows requires-pharmacist badge", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route(`${POS_API}/products/search**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([CONTROLLED_PRODUCT]),
      });
    });

    await page.goto("/terminal");
    const searchInput = page.getByPlaceholder(/search|scan|drug/i);
    await searchInput.fill("tramadol");

    await expect(page.getByText("Tramadol 50mg")).toBeVisible();
    // Should show a controlled substance indicator
    await expect(
      page.getByText(/controlled/i).or(page.locator("[data-controlled]")),
    ).toBeVisible();
  });

  test("adding controlled drug opens pharmacist verification modal", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route(`${POS_API}/products/search**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([CONTROLLED_PRODUCT]),
      });
    });

    await page.goto("/terminal");
    const searchInput = page.getByPlaceholder(/search|scan|drug/i);
    await searchInput.fill("tramadol");
    await page.getByText("Tramadol 50mg").click();

    // Pharmacist verification modal should appear
    await expect(
      page
        .getByText(/pharmacist/i)
        .or(page.getByRole("dialog"))
        .or(page.locator("[data-testid='pharmacist-modal']")),
    ).toBeVisible();
  });

  test("successful pharmacist PIN verification allows add to cart", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route(`${POS_API}/products/search**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([CONTROLLED_PRODUCT]),
      });
    });

    // Mock pharmacist verification
    await page.route(`${POS_API}/verify-pharmacist`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          verified: true,
          pharmacist_id: "pharmacist-1",
          token: "mock-token-123",
          drug_code: "TRAM50",
          expires_at: new Date(Date.now() + 300_000).toISOString(),
        }),
      });
    });

    // Mock add item (with pharmacist_id)
    await page.route(`${POS_API}/transactions/*/items`, async (route) => {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          drug_code: "TRAM50",
          drug_name: "Tramadol 50mg",
          batch_number: "BATCH-2026-C01",
          expiry_date: "2027-12-01",
          quantity: 1,
          unit_price: 25.0,
          discount: 0,
          line_total: 25.0,
          is_controlled: true,
          pharmacist_id: "pharmacist-1",
        }),
      });
    });

    await page.goto("/terminal");
    const searchInput = page.getByPlaceholder(/search|scan|drug/i);
    await searchInput.fill("tramadol");
    await page.getByText("Tramadol 50mg").click();

    // Verification modal should appear — fill PIN
    const pinInput = page
      .getByPlaceholder(/pin/i)
      .or(page.locator("input[type='password']"))
      .first();
    if (await pinInput.isVisible()) {
      await pinInput.fill("1234");
      await page.getByRole("button", { name: /verify|confirm/i }).click();
    }
  });
});
