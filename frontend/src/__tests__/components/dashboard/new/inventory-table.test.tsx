import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/hooks/use-reorder-watchlist", () => ({
  useReorderWatchlist: vi.fn(),
}));

import { useReorderWatchlist } from "@/hooks/use-reorder-watchlist";
import { InventoryTable } from "@/components/dashboard/new/inventory-table";
import type { ReorderWatchlistItem } from "@/types/api";

const mocked = useReorderWatchlist as unknown as Mock;

const ITEMS: ReorderWatchlistItem[] = [
  {
    product_key: 1,
    site_key: 1,
    drug_code: "AMOX500",
    drug_name: "Amoxicillin 500mg",
    site_code: "CAI-01",
    current_quantity: 8,
    reorder_point: 20,
    reorder_quantity: 100,
    daily_velocity: 4,
    days_of_stock: 2,
    status: "critical",
  },
  {
    product_key: 2,
    site_key: 1,
    drug_code: "PARA",
    drug_name: "Paracetamol 500mg",
    site_code: "CAI-01",
    current_quantity: 12,
    reorder_point: 20,
    reorder_quantity: 50,
    daily_velocity: 2,
    days_of_stock: 6,
    status: "low",
  },
  {
    product_key: 3,
    site_key: 1,
    drug_code: "IBU",
    drug_name: "Ibuprofen 200mg",
    site_code: "CAI-01",
    current_quantity: 100,
    reorder_point: 50,
    reorder_quantity: 100,
    daily_velocity: 0,
    days_of_stock: null,
    status: "low",
  },
];

describe("InventoryTable", () => {
  beforeEach(() => {
    mocked.mockReset();
  });

  it("renders loading placeholder during initial fetch", () => {
    mocked.mockReturnValue({ data: undefined, isLoading: true, error: null });
    render(<InventoryTable />);
    expect(screen.getByLabelText("Loading reorder watchlist")).toBeInTheDocument();
  });

  it("renders empty-state message when no items", () => {
    mocked.mockReturnValue({ data: [], isLoading: false, error: null });
    render(<InventoryTable />);
    expect(
      screen.getByText(/No items below reorder point/i),
    ).toBeInTheDocument();
  });

  it("renders one row per item with drug name + SKU + on-hand", () => {
    mocked.mockReturnValue({ data: ITEMS, isLoading: false, error: null });
    render(<InventoryTable />);
    expect(screen.getByText("Amoxicillin 500mg")).toBeInTheDocument();
    expect(screen.getByText("AMOX500")).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument();
  });

  it("renders em-dash when days_of_stock is null (zero velocity)", () => {
    mocked.mockReturnValue({ data: ITEMS, isLoading: false, error: null });
    render(<InventoryTable />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("renders '<1d' for sub-one-day of stock", () => {
    mocked.mockReturnValue({
      data: [{ ...ITEMS[0], days_of_stock: 0.5 }],
      isLoading: false,
      error: null,
    });
    render(<InventoryTable />);
    expect(screen.getByText("<1d")).toBeInTheDocument();
  });

  it("renders status badges with correct labels", () => {
    mocked.mockReturnValue({ data: ITEMS, isLoading: false, error: null });
    render(<InventoryTable />);
    expect(screen.getByText("critical")).toBeInTheDocument();
    // Both row 2 and row 3 are 'low' — use getAllByText.
    expect(screen.getAllByText("low")).toHaveLength(2);
  });

  it("formats zero velocity as 0/day", () => {
    mocked.mockReturnValue({ data: ITEMS, isLoading: false, error: null });
    render(<InventoryTable />);
    expect(screen.getByText("0/day")).toBeInTheDocument();
  });

  it("lets explicit items prop override the hook", () => {
    mocked.mockReturnValue({
      data: [{ ...ITEMS[0], drug_name: "From hook" }],
      isLoading: false,
      error: null,
    });
    render(<InventoryTable items={ITEMS} />);
    expect(screen.getByText("Amoxicillin 500mg")).toBeInTheDocument();
    expect(screen.queryByText("From hook")).toBeNull();
  });
});
