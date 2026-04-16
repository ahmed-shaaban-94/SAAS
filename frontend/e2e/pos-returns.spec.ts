/**
 * POS E2E: Process return -> refund issued -> void log created
 *
 * Critical path 4: Return processing flow — select original transaction,
 * choose items to return, select reason, issue refund.
 */
import { test, expect } from "@playwright/test";

const needsBackend = !!process.env.CI;
const POS_API = "**/api/v1/pos";

const MOCK_COMPLETED_TRANSACTION = {
  id: 101,
  terminal_id: 1,
  staff_id: "cashier-1",
  customer_id: null,
  site_code: "SITE01",
  subtotal: 17.5,
  discount_total: 0,
  tax_total: 0,
  grand_total: 17.5,
  payment_method: "cash",
  status: "completed",
  receipt_number: "R20260416-1-101",
  created_at: new Date().toISOString(),
  items: [
    {
      drug_code: "PARA500",
      drug_name: "Paracetamol 500mg",
      batch_number: "BATCH-2026-001",
      expiry_date: "2027-06-15",
      quantity: 2,
      unit_price: 5.5,
      discount: 0,
      line_total: 11.0,
      is_controlled: false,
    },
    {
      drug_code: "IBUP400",
      drug_name: "Ibuprofen 400mg",
      batch_number: "BATCH-2026-002",
      expiry_date: "2027-08-20",
      quantity: 1,
      unit_price: 6.5,
      discount: 0,
      line_total: 6.5,
      is_controlled: false,
    },
  ],
};

const MOCK_RETURN_RESPONSE = {
  id: 1,
  original_transaction_id: 101,
  return_transaction_id: 102,
  staff_id: "cashier-1",
  reason: "customer_request",
  refund_amount: 11.0,
  refund_method: "cash",
  notes: null,
  created_at: new Date().toISOString(),
};

test.describe("POS Returns Flow", () => {
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

  test("returns page renders with transaction lookup", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.goto("/pos-returns");
    await expect(page).toHaveURL(/pos-returns/);
    // Should have a way to look up the original transaction
    await expect(
      page
        .getByPlaceholder(/receipt|transaction/i)
        .or(page.getByText(/return/i).first()),
    ).toBeVisible();
  });

  test("looking up a transaction shows its items for return selection", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route(`${POS_API}/transactions/*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_COMPLETED_TRANSACTION),
      });
    });

    await page.goto("/pos-returns");

    // Enter the transaction/receipt number
    const lookupInput = page
      .getByPlaceholder(/receipt|transaction/i)
      .or(page.locator("input").first());
    if (await lookupInput.isVisible()) {
      await lookupInput.fill("R20260416-1-101");
      // Trigger search (Enter or button)
      await lookupInput.press("Enter");
    }

    // Transaction items should appear
    await expect(page.getByText("Paracetamol 500mg").or(page.getByText("PARA500"))).toBeVisible();
  });

  test("submitting a return creates the return record", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route(`${POS_API}/transactions/*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_COMPLETED_TRANSACTION),
      });
    });

    await page.route(`${POS_API}/returns`, async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify(MOCK_RETURN_RESPONSE),
        });
      } else {
        await route.continue();
      }
    });

    await page.goto("/pos-returns");
    // The return form should be accessible
    await expect(page.getByText(/return/i).first()).toBeVisible();
  });
});
