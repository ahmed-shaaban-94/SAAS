import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("swr", () => ({
  default: vi.fn(() => ({ data: undefined, error: null, isLoading: true })),
}));

import { KpiRow } from "@/components/dashboard/new/kpi-row";
import type { KPISummary } from "@/types/api";

const SUMMARY: KPISummary = {
  today_gross: 100000,
  mtd_gross: 4280000,
  ytd_gross: 12000000,
  period_gross: 4280000,
  period_transactions: 5200,
  period_customers: 1800,
  today_discount: 0,
  mom_growth_pct: 12.5,
  yoy_growth_pct: 8.1,
  daily_quantity: 0,
  daily_transactions: 5200,
  daily_customers: 1800,
  avg_basket_size: 0,
  daily_returns: 0,
  mtd_transactions: 5200,
  ytd_transactions: 15000,
  stock_risk_count: 3,
  stock_risk_delta: -1,
  expiry_exposure_egp: 142000,
  expiry_batch_count: 12,
  sparklines: [
    {
      metric: "revenue",
      points: [
        { period: "2026-04-10", value: 100000 },
        { period: "2026-04-11", value: 150000 },
      ],
    },
  ],
};

describe("KpiRow", () => {
  it("renders null when no data is available (hook still loading)", () => {
    const { container } = render(<KpiRow />);
    expect(container.firstChild).toBeNull();
  });

  it("renders all four KPI cards from an explicit summary", () => {
    render(<KpiRow summary={SUMMARY} />);
    expect(screen.getByText("Revenue")).toBeInTheDocument();
    expect(screen.getByText("Orders")).toBeInTheDocument();
    expect(screen.getByText("Stock Risk")).toBeInTheDocument();
    expect(screen.getByText("Expiry Exposure")).toBeInTheDocument();
  });

  it("formats MTD revenue compactly as EGP ?M", () => {
    render(<KpiRow summary={SUMMARY} />);
    expect(screen.getByText("EGP 4.28M")).toBeInTheDocument();
  });

  it("renders MoM growth as the Revenue card delta badge", () => {
    render(<KpiRow summary={SUMMARY} />);
    expect(screen.getByText("+12.5%")).toBeInTheDocument();
  });

  it("renders stock-risk delta as a negative percent", () => {
    render(<KpiRow summary={SUMMARY} />);
    expect(screen.getByText("-1.0%")).toBeInTheDocument();
  });

  it("pluralises batches when count != 1", () => {
    render(<KpiRow summary={SUMMARY} />);
    expect(screen.getByText("12 batches")).toBeInTheDocument();
  });

  it("uses singular 'batch' when count == 1", () => {
    render(<KpiRow summary={{ ...SUMMARY, expiry_batch_count: 1 }} />);
    expect(screen.getByText("1 batch")).toBeInTheDocument();
  });

  it("defaults missing optional fields to 0 (no crash, zero values)", () => {
    const minimal: KPISummary = {
      ...SUMMARY,
      stock_risk_count: undefined,
      stock_risk_delta: undefined,
      expiry_exposure_egp: undefined,
      expiry_batch_count: undefined,
      sparklines: undefined,
    };
    render(<KpiRow summary={minimal} />);
    // Stock Risk shows 0; Expiry Exposure shows EGP 0
    expect(screen.getByText("EGP 0")).toBeInTheDocument();
    expect(screen.getByText("0 batches")).toBeInTheDocument();
  });
});
