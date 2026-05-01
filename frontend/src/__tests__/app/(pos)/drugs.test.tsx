import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "../../mocks/server";
import { PosCartProvider } from "@pos/contexts/pos-cart-context";
import { usePosCart } from "@pos/hooks/use-pos-cart";
import { usePosCartStore } from "@pos/store/cart-store";
import { ToastProvider } from "@/components/ui/toast";
import PosDrugsPage from "@pos/pages/drugs";

// --- Fixtures ---

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

const CATALOG_ITEMS = [
  {
    drug_code: "AMOX-500",
    drug_name: "Amoxicillin 500mg",
    drug_brand: "PharmaCo",
    drug_category: "antibiotic",
    is_controlled: true,
    requires_pharmacist: true,
    unit_price: 25.5,
    updated_at: "2026-04-19T08:00:00Z",
  },
  {
    drug_code: "PARA-500",
    drug_name: "Paracetamol 500mg",
    drug_brand: "Generic",
    drug_category: "analgesic",
    is_controlled: false,
    requires_pharmacist: false,
    unit_price: 5.75,
    updated_at: "2026-04-19T08:00:00Z",
  },
  {
    drug_code: "IBU-200",
    drug_name: "Ibuprofen 200mg",
    drug_brand: "PharmaCo",
    drug_category: "analgesic",
    is_controlled: false,
    requires_pharmacist: false,
    unit_price: 8.0,
    updated_at: "2026-04-19T08:00:00Z",
  },
];

function primeHandlers() {
  server.use(
    http.get("*/api/v1/pos/catalog/products", () =>
      HttpResponse.json({ items: CATALOG_ITEMS, next_cursor: null }),
    ),
    http.get("*/api/v1/pos/products/search", ({ request }) => {
      const url = new URL(request.url);
      const q = (url.searchParams.get("q") ?? "").toLowerCase();
      return HttpResponse.json(
        CATALOG_ITEMS.filter(
          (p) => p.drug_name.toLowerCase().includes(q) || p.drug_code.toLowerCase().includes(q),
        ).map((p) => ({
          drug_code: p.drug_code,
          drug_name: p.drug_name,
          drug_brand: p.drug_brand,
          is_controlled: p.is_controlled,
          unit_price: p.unit_price,
          stock_available: 0,
        })),
      );
    }),
  );
}

// Capture cart state from within the provider tree.
let capturedCart: ReturnType<typeof usePosCart> | null = null;
function CartProbe() {
  capturedCart = usePosCart();
  return null;
}

function renderPage() {
  return render(
    <ToastProvider>
      <PosCartProvider>
        <CartProbe />
        <PosDrugsPage />
      </PosCartProvider>
    </ToastProvider>,
  );
}

describe("Drugs tab (#467)", () => {
  beforeEach(() => {
    // Reset Zustand store so cart state does not leak between tests
    usePosCartStore.setState({ items: [], appliedDiscount: null });
    localStorage.clear();
    localStorage.setItem("pos:active_terminal", JSON.stringify(TERMINAL));
    primeHandlers();
    capturedCart = null;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("lists the catalog on mount with no query", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("drug-row-AMOX-500")).toBeInTheDocument();
    });
    expect(screen.getByTestId("drug-row-PARA-500")).toBeInTheDocument();
    expect(screen.getByTestId("drug-row-IBU-200")).toBeInTheDocument();
  });

  it("filters to Rx-only when the Rx filter chip is pressed", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() =>
      expect(screen.getByTestId("drug-row-PARA-500")).toBeInTheDocument(),
    );

    await user.click(screen.getByTestId("chip-rx-rx"));

    await waitFor(() => {
      expect(screen.queryByTestId("drug-row-PARA-500")).not.toBeInTheDocument();
    });
    expect(screen.getByTestId("drug-row-AMOX-500")).toBeInTheDocument();
  });

  it("adds a drug to the cart context when Add is clicked", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() =>
      expect(screen.getByTestId("drug-row-PARA-500")).toBeInTheDocument(),
    );

    await user.click(screen.getByTestId("add-button-PARA-500"));

    await waitFor(() => {
      expect(capturedCart?.items.length).toBe(1);
    });
    expect(capturedCart?.items[0]?.drug_code).toBe("PARA-500");
    expect(capturedCart?.items[0]?.quantity).toBe(1);
  });

  it("pressing Enter inside the search input adds the top filtered row", async () => {
    const user = userEvent.setup();
    renderPage();

    const input = await screen.findByTestId("drugs-search-input");
    await user.click(input);
    await user.type(input, "ibup");

    await waitFor(() =>
      expect(screen.getByTestId("drug-row-IBU-200")).toBeInTheDocument(),
    );

    await user.keyboard("{Enter}");

    await waitFor(() => {
      expect(capturedCart?.items.some((i) => i.drug_code === "IBU-200")).toBe(true);
    });
  });

  it("F6 opens the stocktaking worksheet modal", async () => {
    renderPage();

    await waitFor(() =>
      expect(screen.getByTestId("drug-row-AMOX-500")).toBeInTheDocument(),
    );

    expect(screen.queryByTestId("pos-stocktaking-modal")).not.toBeInTheDocument();

    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "F6" }));
    });

    await waitFor(() => {
      expect(screen.getByTestId("pos-stocktaking-modal")).toBeInTheDocument();
    });
    expect(screen.getByText("Stocktaking Worksheet")).toBeInTheDocument();
  });

  it("'/' focuses the search input from outside an input", async () => {
    renderPage();

    await waitFor(() =>
      expect(screen.getByTestId("drug-row-AMOX-500")).toBeInTheDocument(),
    );

    const input = screen.getByTestId("drugs-search-input");
    input.blur();

    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "/" }));
    });

    await waitFor(() => {
      expect(document.activeElement).toBe(input);
    });
  });
});
