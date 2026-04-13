import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ComparisonPanel } from "@/components/comparison/comparison-panel";

// Pin the contract: comparison-panel must read period totals (period_gross /
// period_transactions), NOT mtd_* fields. This test would have caught the
// original bug where "Revenue" displayed $0 when backend zeroed mtd_gross.
// Legacy fields (today_gross/daily_*) remain populated for AI Light + mobile.
vi.mock("@/hooks/use-comparison", () => ({
  useComparison: () => ({
    current: {
      kpi: {
        today_gross: 1_500_000,
        period_gross: 1_500_000,
        mtd_gross: 0,
        ytd_gross: 0,
        daily_transactions: 2_400,
        period_transactions: 2_400,
        mtd_transactions: 0,
        ytd_transactions: 0,
        daily_customers: 820,
        period_customers: 820,
        avg_basket_size: 625,
        daily_quantity: 0,
        daily_returns: 0,
        today_discount: 0,
        mom_growth_pct: null,
        yoy_growth_pct: null,
      },
      daily_trend: { points: [] },
    },
    previous: {
      kpi: {
        today_gross: 1_200_000,
        period_gross: 1_200_000,
        mtd_gross: 0,
        ytd_gross: 0,
        daily_transactions: 2_000,
        period_transactions: 2_000,
        mtd_transactions: 0,
        ytd_transactions: 0,
        daily_customers: 710,
        period_customers: 710,
        avg_basket_size: 600,
        daily_quantity: 0,
        daily_returns: 0,
        today_discount: 0,
        mom_growth_pct: null,
        yoy_growth_pct: null,
      },
      daily_trend: { points: [] },
    },
    isLoading: false,
    error: null,
  }),
}));

// ComparisonChart depends on Recharts responsive container behavior; stub it
// out so the panel test stays focused on KPI field selection.
vi.mock("@/components/comparison/comparison-chart", () => ({
  ComparisonChart: () => <div data-testid="comparison-chart-stub" />,
}));

describe("ComparisonPanel", () => {
  it("reads period totals (period_gross / period_transactions), not mtd_* fields", () => {
    render(<ComparisonPanel onClose={() => {}} />);

    // Revenue must come from period_gross (1,500,000), not mtd_gross (0).
    // formatCurrency renders numbers like "1,500,000" somewhere in the node.
    const revenueCell = screen.getByText("Revenue").closest("div");
    expect(revenueCell).not.toBeNull();
    expect(revenueCell!.textContent).toMatch(/1[,.\s]?500[,.\s]?000/);

    // Transactions must come from period_transactions (2,400), not
    // mtd_transactions (0).
    const txnCell = screen.getByText("Transactions").closest("div");
    expect(txnCell).not.toBeNull();
    expect(txnCell!.textContent).toMatch(/2[,.\s]?400/);
  });

  it("does NOT render zero when mtd_gross is zero but period_gross has data", () => {
    render(<ComparisonPanel onClose={() => {}} />);
    const revenueCell = screen.getByText("Revenue").closest("div");
    // Must not display only zeros — if the component regressed to reading
    // mtd_gross, the Revenue cell would show "0 vs 0".
    expect(revenueCell!.textContent).not.toMatch(/^Revenue0.*vs.*0$/);
  });
});
