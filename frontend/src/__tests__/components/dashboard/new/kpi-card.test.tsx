import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { KpiCard } from "@/components/dashboard/new/kpi-card";
import type { TimeSeriesPoint } from "@/types/api";

const POINTS: TimeSeriesPoint[] = [
  { period: "2026-04-10", value: 100 },
  { period: "2026-04-11", value: 150 },
  { period: "2026-04-12", value: 120 },
];

describe("KpiCard", () => {
  it("renders label + value + sublabel", () => {
    render(
      <KpiCard label="Revenue" value="EGP 4.28M" sublabel="MTD" sparkline={POINTS} />,
    );
    expect(screen.getByText("Revenue")).toBeInTheDocument();
    expect(screen.getByText("EGP 4.28M")).toBeInTheDocument();
    expect(screen.getByText("MTD")).toBeInTheDocument();
  });

  it("hides delta badge when deltaPct is null or undefined", () => {
    render(<KpiCard label="Orders" value="5K" sparkline={POINTS} />);
    expect(screen.queryByText(/%$/)).toBeNull();
  });

  it("renders positive delta with + prefix", () => {
    render(
      <KpiCard label="Revenue" value="EGP 10K" deltaPct={12.5} sparkline={POINTS} />,
    );
    expect(screen.getByText("+12.5%")).toBeInTheDocument();
  });

  it("renders negative delta with sign from Number.toFixed", () => {
    render(
      <KpiCard label="Revenue" value="EGP 10K" deltaPct={-3.2} sparkline={POINTS} />,
    );
    expect(screen.getByText("-3.2%")).toBeInTheDocument();
  });

  it("renders zero delta without +/- sign", () => {
    render(
      <KpiCard label="Orders" value="5K" deltaPct={0} sparkline={POINTS} />,
    );
    expect(screen.getByText("0.0%")).toBeInTheDocument();
  });

  it("renders sparkline as SVG with aria label", () => {
    render(
      <KpiCard
        label="Revenue"
        value="EGP 10K"
        sparkline={POINTS}
        sparklineLabel="Revenue trend"
      />,
    );
    expect(screen.getByRole("img", { name: "Revenue trend" })).toBeInTheDocument();
  });

  it("falls back to '{label} trend' aria label when not provided", () => {
    render(<KpiCard label="Orders" value="5K" sparkline={POINTS} />);
    expect(screen.getByRole("img", { name: "Orders trend" })).toBeInTheDocument();
  });

  it("renders an empty placeholder when sparkline is empty", () => {
    const { container } = render(<KpiCard label="Revenue" value="EGP 10K" />);
    expect(container.querySelector("svg")).toBeNull();
  });
});
