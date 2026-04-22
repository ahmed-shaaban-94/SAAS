import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "../../mocks/server";
import { PosCartProvider } from "@/contexts/pos-cart-context";
import PosTerminalPage from "@/app/(pos)/terminal/page";
import type { PosProductResult } from "@/types/pos";

// --- Test fixtures ---

const TERMINAL = {
  id: 42,
  tenant_id: 1,
  site_code: "ALEX-001",
  staff_id: "staff-1",
  terminal_name: "Alex Counter 1",
  status: "open" as const,
  opened_at: "2026-04-19T08:00:00Z",
  closed_at: null,
  opening_cash: 500,
  closing_cash: null,
};

const PRODUCTS: PosProductResult[] = Array.from({ length: 9 }, (_, i) => ({
  drug_code: `SKU-${i + 1}`,
  drug_name: `Product ${i + 1}`,
  drug_brand: null,
  is_controlled: false,
  unit_price: (i + 1) * 10,
  stock_available: 100,
}));

function primeHandlers() {
  server.use(
    http.get("*/api/v1/pos/products/search", () => HttpResponse.json(PRODUCTS)),
    http.post("*/api/v1/pos/transactions", () =>
      HttpResponse.json({
        id: 1001,
        tenant_id: 1,
        terminal_id: 42,
        staff_id: "staff-1",
        pharmacist_id: null,
        customer_id: null,
        site_code: "ALEX-001",
        subtotal: 0,
        discount_total: 0,
        tax_total: 0,
        grand_total: 0,
        payment_method: null,
        status: "draft",
        receipt_number: null,
        created_at: "2026-04-19T09:00:00Z",
      }),
    ),
    http.post("*/api/v1/pos/vouchers/validate", async ({ request }) => {
      const body = (await request.json()) as { code: string; cart_subtotal?: number };
      return HttpResponse.json({
        code: body.code,
        discount_type: "percent",
        value: 10,
        remaining_uses: 5,
        expires_at: null,
        min_purchase: null,
      });
    }),
  );
}

function renderPage() {
  return render(
    <PosCartProvider>
      <PosTerminalPage />
    </PosCartProvider>,
  );
}

describe("Terminal v2 integration", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("pos:active_terminal", JSON.stringify(TERMINAL));
    primeHandlers();
  });

  it("scans a SKU into the cart and shows a confirmation toast", async () => {
    const user = userEvent.setup();
    renderPage();

    // Wait for products to load, then for one quick-pick tile to appear
    await waitFor(() => {
      expect(screen.getByTestId("quick-pick-1")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("quick-pick-1"));

    // Cart row + toast + row number
    await waitFor(() => {
      expect(screen.getByTestId("cart-row-SKU-1")).toBeInTheDocument();
    });
    expect(screen.getByTestId("scan-toast")).toHaveTextContent(/Product 1 added/);
  });

  it("adds the matching tile when 1-9 is pressed outside an input", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByTestId("quick-pick-3")).toBeInTheDocument());

    // Blur any auto-focused input first to make sure our keydown fires at
    // the body (isInput === false in the handler).
    const scanInput = screen.getByPlaceholderText(/scan a drug/i) as HTMLInputElement;
    scanInput.blur();

    await user.keyboard("5");

    await waitFor(() => {
      expect(screen.getByTestId("cart-row-SKU-5")).toBeInTheDocument();
    });
  });

  it("does NOT trigger Quick Pick 1-9 when typing in the scan bar", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => expect(screen.getByTestId("quick-pick-2")).toBeInTheDocument());

    const scanInput = screen.getByPlaceholderText(/scan a drug/i) as HTMLInputElement;
    scanInput.focus();
    // The input has data-pos-scanner-ignore, so "2" should land in the
    // input, NOT add Quick Pick #2 to the cart.
    await user.keyboard("2");

    expect(scanInput.value).toBe("2");
    expect(screen.queryByTestId("cart-row-SKU-2")).not.toBeInTheDocument();
  });

  it("F9 / F10 / F11 / F7 select the matching payment method", async () => {
    // D0 — PaymentTiles now live inside CheckoutConfirmModal. We add an
    // item + open the modal first so pay-tile-* are in the DOM. The F-key
    // handler still fires on window.keydown regardless of where the tiles
    // render, so the asserted behavior is unchanged.
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByTestId("quick-pick-1")).toBeInTheDocument());
    await user.click(screen.getByTestId("quick-pick-1"));
    await user.click(screen.getByTestId("start-checkout-button"));
    await waitFor(() => expect(screen.getByTestId("pay-tile-cash")).toBeInTheDocument());

    // Initial: cash active
    expect(screen.getByTestId("pay-tile-cash")).toHaveAttribute("aria-pressed", "true");

    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "F10" }));
    });
    await waitFor(() =>
      expect(screen.getByTestId("pay-tile-card")).toHaveAttribute("aria-pressed", "true"),
    );

    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "F11" }));
    });
    await waitFor(() =>
      expect(screen.getByTestId("pay-tile-insurance")).toHaveAttribute("aria-pressed", "true"),
    );

    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "F9" }));
    });
    await waitFor(() =>
      expect(screen.getByTestId("pay-tile-cash")).toHaveAttribute("aria-pressed", "true"),
    );
  });

  it("applies a voucher via the unified applied_discount slot and hands off a pending checkout", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => expect(screen.getByTestId("quick-pick-1")).toBeInTheDocument());

    // Add an item so the cart has a positive subtotal
    await user.click(screen.getByTestId("quick-pick-1"));
    await waitFor(() => expect(screen.getByTestId("cart-row-SKU-1")).toBeInTheDocument());

    // D0 — pay-tile-voucher is inside the checkout modal now; open it.
    await user.click(screen.getByTestId("start-checkout-button"));
    await waitFor(() =>
      expect(screen.getByTestId("checkout-confirm-modal")).toBeInTheDocument(),
    );
    // Open the voucher modal via the voucher tile
    await user.click(screen.getByTestId("pay-tile-voucher"));
    const codeInput = await screen.findByLabelText(/voucher code/i);
    await user.type(codeInput, "SAVE10");

    // Validate then confirm
    await user.click(screen.getByRole("button", { name: /validate code/i }));
    const applyBtn = await screen.findByRole("button", { name: /apply voucher/i });
    await user.click(applyBtn);

    // Voucher tile now shows the applied discount
    await waitFor(() => {
      expect(screen.getByTestId("pay-tile-voucher")).toHaveTextContent(/−EGP/);
    });

    // Switch back to cash so we can charge
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "F9" }));
    });

    // Click charge (inside the already-open checkout modal)
    await user.click(screen.getByTestId("charge-button"));

    // pending checkout in localStorage carries only the transaction + method.
    // The applied discount (voucher OR promotion) lives in the cart context
    // and is read from there by the /checkout page's applied_discount body.
    await waitFor(() => {
      const stored = localStorage.getItem("pos:pending_checkout");
      expect(stored).toBeTruthy();
      const parsed = JSON.parse(stored as string);
      expect(parsed.voucher_code).toBeUndefined();
      expect(parsed.transactionId).toBe(1001);
      expect(parsed.method).toBe("cash");
    });
  });

  it("keeps the Start Checkout button disabled while the cart is empty", async () => {
    // D0 — the right column shows start-checkout-button. The old
    // charge-button lives inside the modal, which cannot be opened
    // while the cart is empty.
    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId("start-checkout-button")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("start-checkout-button")).toBeDisabled();
    expect(screen.queryByTestId("checkout-confirm-modal")).not.toBeInTheDocument();
    expect(screen.queryByTestId("charge-button")).not.toBeInTheDocument();
  });

  it("opens CheckoutConfirmModal via Start Checkout and closes with Escape", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByTestId("quick-pick-1")).toBeInTheDocument());
    await user.click(screen.getByTestId("quick-pick-1"));

    // Modal not yet open
    expect(screen.queryByTestId("checkout-confirm-modal")).not.toBeInTheDocument();

    // Click CTA → modal opens, charge-button appears inside it
    await user.click(screen.getByTestId("start-checkout-button"));
    await waitFor(() =>
      expect(screen.getByTestId("checkout-confirm-modal")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("charge-button")).toBeInTheDocument();

    // Escape closes
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    });
    await waitFor(() =>
      expect(screen.queryByTestId("checkout-confirm-modal")).not.toBeInTheDocument(),
    );
  });

  it(
    "captures insurance_no via the modal and threads it through to the pending checkout",
    async () => {
      const user = userEvent.setup();
      renderPage();

      await waitFor(() => expect(screen.getByTestId("quick-pick-1")).toBeInTheDocument());
      await user.click(screen.getByTestId("quick-pick-1"));

      // D0 — open the checkout modal first so the InsuranceStrip's
      // "Configure…" button (which lives inside ActivePaymentStrip,
      // which lives inside the modal) is in the DOM. F11 still switches
      // activePayment state regardless of modal-open state.
      await user.click(screen.getByTestId("start-checkout-button"));
      await waitFor(() =>
        expect(screen.getByTestId("checkout-confirm-modal")).toBeInTheDocument(),
      );

      // Activate insurance payment strip (F11) and open the modal via Configure
      act(() => {
        window.dispatchEvent(new KeyboardEvent("keydown", { key: "F11" }));
      });
      await waitFor(() =>
        expect(screen.getByTestId("insurance-configure-button")).toBeInTheDocument(),
      );
      await user.click(screen.getByTestId("insurance-configure-button"));

      // Fill the modal
      await waitFor(() =>
        expect(screen.getByTestId("pos-insurance-modal")).toBeInTheDocument(),
      );
      await user.type(
        screen.getByTestId("pos-insurance-national-id"),
        "29901011234567",
      );
      await user.type(screen.getByTestId("pos-insurance-preauth"), "PA-9001");
      await user.click(screen.getByTestId("pos-insurance-apply"));

      // Modal closed, insurance state applied, charge enabled
      await waitFor(() =>
        expect(screen.queryByTestId("pos-insurance-modal")).not.toBeInTheDocument(),
      );

      // Click charge
      await user.click(screen.getByTestId("charge-button"));

      await waitFor(() => {
        const stored = localStorage.getItem("pos:pending_checkout");
        expect(stored).toBeTruthy();
        const parsed = JSON.parse(stored as string);
        expect(parsed.method).toBe("insurance");
        expect(parsed.insuranceNo).toBe("PA-9001");
      });
    },
  );
});
