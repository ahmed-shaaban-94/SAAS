import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/hooks/use-channels", () => ({
  useChannels: vi.fn(),
}));

// jsdom's ResizeObserver-less env makes ResponsiveContainer render width=0;
// stub it with a plain <div> so child charts mount with real dimensions.
vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div style={{ width: 200, height: 200 }}>{children}</div>
    ),
  };
});

import { useChannels } from "@/hooks/use-channels";
import { ChannelDonut } from "@/components/dashboard/new/channel-donut";
import type { ChannelsBreakdown } from "@/types/api";

const mocked = useChannels as unknown as Mock;

const FULL: ChannelsBreakdown = {
  items: [
    {
      channel: "retail",
      label: "Retail walk-in",
      value_egp: 800_000,
      pct_of_total: 80,
      source: "derived",
    },
    {
      channel: "wholesale",
      label: "Wholesale",
      value_egp: 0,
      pct_of_total: 0,
      source: "unavailable",
    },
    {
      channel: "institution",
      label: "Institution",
      value_egp: 200_000,
      pct_of_total: 20,
      source: "derived",
    },
    {
      channel: "online",
      label: "Online",
      value_egp: 0,
      pct_of_total: 0,
      source: "unavailable",
    },
  ],
  total_egp: 1_000_000,
  data_coverage: "partial",
};

const EMPTY: ChannelsBreakdown = {
  items: FULL.items.map((i) => ({ ...i, value_egp: 0, pct_of_total: 0 })),
  total_egp: 0,
  data_coverage: "partial",
};

describe("ChannelDonut", () => {
  beforeEach(() => {
    mocked.mockReset();
  });

  it("renders loading placeholder during initial fetch", () => {
    mocked.mockReturnValue({ data: undefined, isLoading: true, error: null });
    render(<ChannelDonut />);
    expect(screen.getByLabelText("Loading sales channels")).toBeInTheDocument();
  });

  it("renders all four channel labels in the legend", () => {
    mocked.mockReturnValue({ data: FULL, isLoading: false, error: null });
    render(<ChannelDonut />);
    expect(screen.getByText("Retail walk-in")).toBeInTheDocument();
    expect(screen.getByText("Wholesale")).toBeInTheDocument();
    expect(screen.getByText("Institution")).toBeInTheDocument();
    expect(screen.getByText("Online")).toBeInTheDocument();
  });

  it("marks unavailable channels with a 'no data' chip", () => {
    mocked.mockReturnValue({ data: FULL, isLoading: false, error: null });
    render(<ChannelDonut />);
    // two 'no data' chips — wholesale + online
    expect(screen.getAllByText("no data")).toHaveLength(2);
  });

  it("renders the total in the donut centre", () => {
    mocked.mockReturnValue({ data: FULL, isLoading: false, error: null });
    render(<ChannelDonut />);
    expect(screen.getByText("EGP 1.0M")).toBeInTheDocument();
  });

  it("shows a 'No revenue yet' placeholder when total is zero", () => {
    mocked.mockReturnValue({ data: EMPTY, isLoading: false, error: null });
    render(<ChannelDonut />);
    expect(screen.getByText("No revenue yet")).toBeInTheDocument();
  });

  it("surfaces partial-coverage footnote", () => {
    mocked.mockReturnValue({ data: FULL, isLoading: false, error: null });
    render(<ChannelDonut />);
    expect(
      screen.getByText(/Partial data/i),
    ).toBeInTheDocument();
  });

  it("hides the footnote when data_coverage is 'full'", () => {
    mocked.mockReturnValue({
      data: { ...FULL, data_coverage: "full" as const },
      isLoading: false,
      error: null,
    });
    render(<ChannelDonut />);
    expect(screen.queryByText(/Partial data/i)).toBeNull();
  });

  it("lets explicit breakdown prop override the hook", () => {
    mocked.mockReturnValue({
      data: { ...FULL, total_egp: 1 },
      isLoading: false,
      error: null,
    });
    render(<ChannelDonut breakdown={FULL} />);
    expect(screen.getByText("EGP 1.0M")).toBeInTheDocument();
  });
});
