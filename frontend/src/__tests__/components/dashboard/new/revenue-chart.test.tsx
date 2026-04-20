import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("@/hooks/use-revenue-forecast", () => ({
  useRevenueForecast: vi.fn(),
}));

// ResponsiveContainer → fixed-size div so Recharts lays out under jsdom.
vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div style={{ width: 600, height: 200 }}>{children}</div>
    ),
  };
});

import { useRevenueForecast } from "@/hooks/use-revenue-forecast";
import { RevenueChart } from "@/components/dashboard/new/revenue-chart";
import type { RevenueForecast } from "@/types/api";

const mocked = useRevenueForecast as unknown as Mock;

const SAMPLE: RevenueForecast = {
  actual: [
    { period: "2026-04-18", value: 100000 },
    { period: "2026-04-19", value: 110000 },
    { period: "2026-04-20", value: 120000 },
  ],
  forecast: [
    { date: "2026-04-21", value: 130000, ci_low: 120000, ci_high: 140000 },
    { date: "2026-04-22", value: 140000, ci_low: 125000, ci_high: 155000 },
  ],
  target: {
    period_end: "2026-12-31",
    value: 1_000_000,
    status: "on_track",
  },
  today: "2026-04-20",
  period: "month",
  stats: {
    this_period_egp: 330_000,
    delta_pct: 12.5,
    confidence: 90,
  },
};

describe("RevenueChart", () => {
  beforeEach(() => {
    mocked.mockReset();
    mocked.mockReturnValue({ data: undefined, isLoading: true, error: null });
  });

  it("renders loading placeholder during initial fetch", () => {
    render(<RevenueChart />);
    expect(screen.getByLabelText("Loading revenue chart")).toBeInTheDocument();
  });

  it("renders stats header with compact total + delta + confidence", () => {
    mocked.mockReturnValue({ data: SAMPLE, isLoading: false, error: null });
    render(<RevenueChart />);
    expect(screen.getByText("EGP 330K")).toBeInTheDocument();
    expect(screen.getByText("+12.5%")).toBeInTheDocument();
    expect(screen.getByText(/90% confidence/)).toBeInTheDocument();
  });

  it("renders negative delta with minus sign (no extra '+')", () => {
    mocked.mockReturnValue({
      data: { ...SAMPLE, stats: { ...SAMPLE.stats, delta_pct: -3.2 } },
      isLoading: false,
      error: null,
    });
    render(<RevenueChart />);
    expect(screen.getByText("-3.2%")).toBeInTheDocument();
    expect(screen.queryByText("+-3.2%")).toBeNull();
  });

  it("omits confidence line when null", () => {
    mocked.mockReturnValue({
      data: { ...SAMPLE, stats: { ...SAMPLE.stats, confidence: null } },
      isLoading: false,
      error: null,
    });
    render(<RevenueChart />);
    expect(screen.queryByText(/confidence/i)).toBeNull();
  });

  it("renders the segmented period control with five options", () => {
    mocked.mockReturnValue({ data: SAMPLE, isLoading: false, error: null });
    render(<RevenueChart />);
    expect(screen.getByRole("button", { name: "Day" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Week" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Month" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Quarter" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "YTD" })).toBeInTheDocument();
  });

  it("marks the initial period as pressed and updates on click", async () => {
    mocked.mockReturnValue({ data: SAMPLE, isLoading: false, error: null });
    const user = userEvent.setup();
    render(<RevenueChart period="week" />);
    expect(screen.getByRole("button", { name: "Week" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await user.click(screen.getByRole("button", { name: "Quarter" }));
    expect(screen.getByRole("button", { name: "Quarter" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("hides the segmented control when an explicit data prop is supplied", () => {
    render(<RevenueChart data={SAMPLE} />);
    expect(screen.queryByRole("group", { name: /Revenue period/i })).toBeNull();
  });

  it("shows target status footer with humanised label", () => {
    mocked.mockReturnValue({ data: SAMPLE, isLoading: false, error: null });
    render(<RevenueChart />);
    expect(screen.getByText(/Target status:/i)).toBeInTheDocument();
    expect(screen.getByText("on track")).toBeInTheDocument();
  });

  it("hides target status footer when target is null", () => {
    mocked.mockReturnValue({
      data: { ...SAMPLE, target: null },
      isLoading: false,
      error: null,
    });
    render(<RevenueChart />);
    expect(screen.queryByText(/Target status:/i)).toBeNull();
  });

  it("renders chart container with img role + aria label", () => {
    mocked.mockReturnValue({ data: SAMPLE, isLoading: false, error: null });
    render(<RevenueChart />);
    expect(
      screen.getByRole("img", { name: /Revenue actual and forecast chart/i }),
    ).toBeInTheDocument();
  });

  it("lets explicit data prop override the hook", () => {
    mocked.mockReturnValue({
      data: {
        ...SAMPLE,
        stats: { ...SAMPLE.stats, this_period_egp: 0 },
      },
      isLoading: false,
      error: null,
    });
    render(<RevenueChart data={SAMPLE} />);
    expect(screen.getByText("EGP 330K")).toBeInTheDocument();
  });
});
