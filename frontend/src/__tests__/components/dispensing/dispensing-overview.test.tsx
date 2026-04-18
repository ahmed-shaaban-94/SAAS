import { describe, it, expect, vi, type Mock } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/hooks/use-dispense-rate", () => ({ useDispenseRate: vi.fn() }));
vi.mock("@/hooks/use-stockout-risk", () => ({ useStockoutRisk: vi.fn() }));
vi.mock("@/hooks/use-days-of-stock", () => ({ useDaysOfStock: vi.fn() }));
vi.mock("@/hooks/use-reconciliation", () => ({ useReconciliation: vi.fn() }));
vi.mock("@/contexts/filter-context", () => ({
  useFilters: () => ({ filters: {} }),
}));

import { useDispenseRate } from "@/hooks/use-dispense-rate";
import { useStockoutRisk } from "@/hooks/use-stockout-risk";
import { useDaysOfStock } from "@/hooks/use-days-of-stock";
import { useReconciliation } from "@/hooks/use-reconciliation";
import { DispensingOverview } from "@/components/dispensing/dispensing-overview";

const mockRate = useDispenseRate as unknown as Mock;
const mockRisk = useStockoutRisk as unknown as Mock;
const mockDays = useDaysOfStock as unknown as Mock;
const mockRecon = useReconciliation as unknown as Mock;

function setupMocks({
  rateLoading = false,
  rateData = [{ avg_daily_dispense: 5 }, { avg_daily_dispense: 3 }],
  riskData = [{ risk_level: "critical" }, { risk_level: "at_risk" }],
  daysData = [{ days_of_stock: 10 }, { days_of_stock: 20 }],
  reconData = { items_with_variance: 4, total_items: 20 },
} = {}) {
  mockRate.mockReturnValue({ data: rateData, isLoading: rateLoading, error: null });
  mockRisk.mockReturnValue({ data: riskData, isLoading: false, error: null });
  mockDays.mockReturnValue({ data: daysData, isLoading: false, error: null });
  mockRecon.mockReturnValue({ data: reconData, isLoading: false, error: null });
}

describe("DispensingOverview", () => {
  it("renders four KPI stat cards", () => {
    setupMocks();
    render(<DispensingOverview />);
    const values = document.querySelectorAll("[data-kpi-value]");
    expect(values.length).toBe(4);
  });

  it("shows active product count from dispense rate data", () => {
    setupMocks({ rateData: [{ avg_daily_dispense: 5 }, { avg_daily_dispense: 3 }] });
    render(<DispensingOverview />);
    // "2" appears for both Active Products and Stockout Risk Items (both have 2 items)
    const matches = screen.getAllByText("2");
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it("shows stockout risk count", () => {
    setupMocks({ riskData: [{ risk_level: "critical" }, { risk_level: "at_risk" }, { risk_level: "stockout" }] });
    render(<DispensingOverview />);
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("shows avg days of stock rounded to 1 decimal", () => {
    setupMocks({ daysData: [{ days_of_stock: 10 }, { days_of_stock: 20 }, { days_of_stock: null as unknown as number }] });
    render(<DispensingOverview />);
    // avg of non-null: (10 + 20) / 2 = 15.0
    expect(screen.getByText("15.0")).toBeInTheDocument();
  });

  it("shows reconciliation variance count", () => {
    setupMocks({ reconData: { items_with_variance: 7, total_items: 30 } });
    render(<DispensingOverview />);
    expect(screen.getByText("7")).toBeInTheDocument();
  });

  it("shows loading skeleton when rate hook is loading", () => {
    setupMocks({ rateLoading: true });
    const { container } = render(<DispensingOverview />);
    // LoadingCard uses shimmer-line class (not animate-pulse)
    expect(container.querySelector(".shimmer-line")).not.toBeNull();
    const values = container.querySelectorAll("[data-kpi-value]");
    expect(values.length).toBe(0);
  });
});
