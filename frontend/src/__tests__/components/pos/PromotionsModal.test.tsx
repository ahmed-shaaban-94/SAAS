import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { EligiblePromotion, EligiblePromotionsResponse } from "@/types/promotions";

const mockHookState: {
  data: EligiblePromotionsResponse | null;
  error: string | null;
  isLoading: boolean;
} = { data: null, error: null, isLoading: false };

vi.mock("@/hooks/use-eligible-promotions", () => ({
  useEligiblePromotions: () => mockHookState,
}));

const applyDiscount = vi.fn();

vi.mock("@/contexts/pos-cart-context", async () => {
  const actual = await vi.importActual<
    typeof import("@/contexts/pos-cart-context")
  >("@/contexts/pos-cart-context");
  return {
    ...actual,
    usePosCart: () => ({
      items: [
        {
          drug_code: "MED-001",
          drug_name: "Paracetamol",
          batch_number: null,
          expiry_date: null,
          quantity: 2,
          unit_price: 50,
          discount: 0,
          line_total: 100,
          is_controlled: false,
        },
      ],
      subtotal: 100,
      applyDiscount,
      appliedDiscount: null,
    }),
  };
});

import { PromotionsModal } from "@/components/pos/PromotionsModal";

function promo(overrides: Partial<EligiblePromotion> = {}): EligiblePromotion {
  return {
    id: 1,
    name: "Ramadan 2026",
    description: "10% off all items",
    discount_type: "percent",
    value: 10,
    scope: "all",
    min_purchase: null,
    max_discount: null,
    ends_at: "2026-05-01T00:00:00Z",
    preview_discount: 10,
    ...overrides,
  };
}

describe("PromotionsModal (PR 6 redesign)", () => {
  beforeEach(() => {
    applyDiscount.mockReset();
    mockHookState.data = null;
    mockHookState.error = null;
    mockHookState.isLoading = false;
  });

  it("renders nothing when closed", () => {
    render(<PromotionsModal open={false} onClose={vi.fn()} />);
    expect(screen.queryByTestId("pos-promotions-modal")).not.toBeInTheDocument();
  });

  it("shows the PROMOTIONS badge and empty state when no promotions", () => {
    mockHookState.data = { promotions: [] };
    render(<PromotionsModal open onClose={vi.fn()} />);
    expect(screen.getByTestId("pos-promotions-modal")).toBeInTheDocument();
    expect(screen.getByText("PROMOTIONS")).toBeInTheDocument();
    expect(screen.getByTestId("pos-promotions-empty")).toHaveTextContent(
      /No active promotions/i,
    );
  });

  it("renders one row per promotion with savings amount", () => {
    mockHookState.data = {
      promotions: [promo({ id: 1, preview_discount: 15 }), promo({ id: 2, name: "New Patient", preview_discount: 5 })],
    };
    render(<PromotionsModal open onClose={vi.fn()} />);
    expect(screen.getByTestId("pos-promotion-row-1")).toBeInTheDocument();
    expect(screen.getByTestId("pos-promotion-row-2")).toBeInTheDocument();
    expect(screen.getByText(/−EGP 15\.00/)).toBeInTheDocument();
    expect(screen.getByText(/−EGP 5\.00/)).toBeInTheDocument();
  });

  it("Apply button applies the highlighted promotion (first by default) and closes", async () => {
    mockHookState.data = { promotions: [promo({ id: 7, preview_discount: 12 })] };
    const onClose = vi.fn();
    render(<PromotionsModal open onClose={onClose} />);
    await userEvent.click(screen.getByTestId("pos-promotions-apply"));
    expect(applyDiscount).toHaveBeenCalledWith(
      expect.objectContaining({ source: "promotion", ref: "7", discountAmount: 12 }),
    );
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("ArrowDown + Enter applies the second promotion via keyboard", async () => {
    mockHookState.data = {
      promotions: [
        promo({ id: 1, preview_discount: 8 }),
        promo({ id: 2, name: "Loyalty", preview_discount: 20 }),
      ],
    };
    const onClose = vi.fn();
    render(<PromotionsModal open onClose={onClose} />);
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown" }));
    });
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    });
    expect(applyDiscount).toHaveBeenCalledWith(
      expect.objectContaining({ ref: "2", discountAmount: 20 }),
    );
    expect(onClose).toHaveBeenCalled();
  });

  it("numeric keys jump selection to that index", async () => {
    mockHookState.data = {
      promotions: [
        promo({ id: 10, preview_discount: 1 }),
        promo({ id: 20, preview_discount: 2 }),
        promo({ id: 30, preview_discount: 3 }),
      ],
    };
    render(<PromotionsModal open onClose={vi.fn()} />);
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "3" }));
    });
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    });
    expect(applyDiscount).toHaveBeenCalledWith(
      expect.objectContaining({ ref: "30", discountAmount: 3 }),
    );
  });

  it("shows loading state while fetching", () => {
    mockHookState.isLoading = true;
    render(<PromotionsModal open onClose={vi.fn()} />);
    expect(screen.getByRole("status")).toHaveTextContent(/Checking eligibility/i);
  });

  it("shows error state on fetch failure", () => {
    mockHookState.error = "boom";
    render(<PromotionsModal open onClose={vi.fn()} />);
    expect(screen.getByRole("alert")).toHaveTextContent(/Could not load promotions/i);
  });
});
