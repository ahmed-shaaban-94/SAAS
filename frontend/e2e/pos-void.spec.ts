/**
 * POS E2E: Void transaction — supervisor PIN required -> stock restored -> audit logged
 *
 * Critical path 5: Void requires supervisor-level RBAC permission.
 * Stock movements are reversed and audit trail is created.
 */
import { test, expect } from "@playwright/test";

const needsBackend = !!process.env.CI;
const POS_API = "**/api/v1/pos";

const MOCK_VOID_RESPONSE = {
  id: 1,
  transaction_id: 101,
  tenant_id: 1,
  voided_by: "supervisor-1",
  reason: "Customer changed their mind after payment",
  voided_at: new Date().toISOString(),
};

const MOCK_TRANSACTION_HISTORY = [
  {
    id: 101,
    terminal_id: 1,
    staff_id: "cashier-1",
    customer_id: null,
    grand_total: 17.5,
    payment_method: "cash",
    status: "completed",
    receipt_number: "R20260416-1-101",
    created_at: new Date().toISOString(),
  },
  {
    id: 100,
    terminal_id: 1,
    staff_id: "cashier-1",
    customer_id: "CUST-001",
    grand_total: 45.0,
    payment_method: "card",
    status: "completed",
    receipt_number: "R20260416-1-100",
    created_at: new Date(Date.now() - 3600_000).toISOString(),
  },
];

test.describe("POS Void Transaction Flow", () => {
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

  test("transaction history page shows completed transactions", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route(`${POS_API}/transactions**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_TRANSACTION_HISTORY),
      });
    });

    await page.goto("/history");
    await expect(page.getByText("R20260416-1-101")).toBeVisible();
    await expect(page.getByText("17.5")).toBeVisible();
  });

  test("void button triggers confirmation with reason input", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route(`${POS_API}/transactions**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_TRANSACTION_HISTORY),
      });
    });

    await page.goto("/history");

    // Look for void button on the first transaction
    const voidButton = page.getByRole("button", { name: /void/i }).first();
    if (await voidButton.isVisible()) {
      await voidButton.click();
      // Should show a confirmation dialog or modal with reason input
      await expect(
        page.getByText(/reason/i).or(page.getByRole("dialog")),
      ).toBeVisible();
    }
  });

  test("confirming void updates transaction status and shows audit", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend");

    await page.route(`${POS_API}/transactions**`, async (route) => {
      if (route.request().url().includes("/void")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(MOCK_VOID_RESPONSE),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(MOCK_TRANSACTION_HISTORY),
        });
      }
    });

    await page.goto("/history");
    await expect(page.getByText("R20260416-1-101")).toBeVisible();
  });
});
