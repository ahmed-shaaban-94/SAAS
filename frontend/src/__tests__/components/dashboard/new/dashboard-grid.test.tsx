import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

// Stub every leaf widget so this test focuses on composition only.
// Each stub renders a unique test-id we can assert against.
vi.mock("@/components/dashboard/new/alert-banner", () => ({
  AlertBanner: () => <div data-testid="alert-banner" />,
}));
vi.mock("@/components/dashboard/new/anomaly-feed", () => ({
  AnomalyFeed: () => <div data-testid="anomaly-feed" />,
}));
vi.mock("@/components/dashboard/new/branch-list", () => ({
  BranchList: () => <div data-testid="branch-list" />,
}));
vi.mock("@/components/dashboard/new/channel-donut", () => ({
  ChannelDonut: () => <div data-testid="channel-donut" />,
}));
vi.mock("@/components/dashboard/new/expiry-exposure-card", () => ({
  ExpiryExposureCard: () => <div data-testid="expiry-exposure-card" />,
}));
vi.mock("@/components/dashboard/new/expiry-heatmap", () => ({
  ExpiryHeatmap: () => <div data-testid="expiry-heatmap" />,
}));
vi.mock("@/components/dashboard/new/inventory-table", () => ({
  InventoryTable: () => <div data-testid="inventory-table" />,
}));
vi.mock("@/components/dashboard/new/kpi-row", () => ({
  KpiRow: () => <div data-testid="kpi-row" />,
}));
vi.mock("@/components/dashboard/new/pipeline-health-card", () => ({
  PipelineHealthCard: () => <div data-testid="pipeline-health-card" />,
}));
vi.mock("@/components/dashboard/new/revenue-chart", () => ({
  RevenueChart: () => <div data-testid="revenue-chart" />,
}));

import { DashboardGrid } from "@/components/dashboard/new/dashboard-grid";

describe("DashboardGrid", () => {
  it("mounts all ten widgets exactly once", () => {
    render(<DashboardGrid />);
    for (const id of [
      "alert-banner",
      "kpi-row",
      "revenue-chart",
      "channel-donut",
      "anomaly-feed",
      "inventory-table",
      "branch-list",
      "pipeline-health-card",
      "expiry-exposure-card",
      "expiry-heatmap",
    ]) {
      expect(screen.getByTestId(id)).toBeInTheDocument();
    }
  });

  it("mounts once (identity check — prevents accidental duplicate renders)", () => {
    render(<DashboardGrid />);
    expect(screen.getAllByTestId("revenue-chart")).toHaveLength(1);
    expect(screen.getAllByTestId("kpi-row")).toHaveLength(1);
  });

  it("exposes a stable test id on the outer container", () => {
    render(<DashboardGrid />);
    expect(screen.getByTestId("dashboard-grid-new")).toBeInTheDocument();
  });
});
