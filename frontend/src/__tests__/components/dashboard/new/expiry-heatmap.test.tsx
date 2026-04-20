import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/hooks/use-expiry-calendar", () => ({
  useExpiryCalendar: vi.fn(),
}));

import { useExpiryCalendar } from "@/hooks/use-expiry-calendar";
import { ExpiryHeatmap } from "@/components/dashboard/new/expiry-heatmap";
import type { ExpiryCalendarDay } from "@/types/expiry";

const mocked = useExpiryCalendar as unknown as Mock;

const DAYS: ExpiryCalendarDay[] = [
  { date: "2026-04-20", batch_count: 3, total_quantity: 40, alert_level: "critical" },
  { date: "2026-04-22", batch_count: 1, total_quantity: 10, alert_level: "safe" },
  { date: "2026-05-01", batch_count: 5, total_quantity: 60, alert_level: "warning" },
];

const ANCHOR = new Date("2026-04-20T00:00:00Z");

describe("ExpiryHeatmap", () => {
  beforeEach(() => {
    mocked.mockReset();
  });

  it("renders loading placeholder during initial fetch", () => {
    mocked.mockReturnValue({ data: undefined, isLoading: true, error: null });
    render(<ExpiryHeatmap today={ANCHOR} />);
    expect(screen.getByLabelText("Loading expiry heatmap")).toBeInTheDocument();
  });

  it("renders empty state when no expiries", () => {
    mocked.mockReturnValue({ data: [], isLoading: false, error: null });
    render(<ExpiryHeatmap today={ANCHOR} />);
    expect(
      screen.getByText(/No batches expiring in the next 98 days/i),
    ).toBeInTheDocument();
  });

  it("renders 98 cells by default in the heatmap grid", () => {
    mocked.mockReturnValue({ data: DAYS, isLoading: false, error: null });
    const { container } = render(<ExpiryHeatmap today={ANCHOR} />);
    // The grid renders exactly `horizon` cells — pick them via role=img grid.
    const grid = screen.getByRole("img", {
      name: /Expiry heatmap — next 98 days/i,
    });
    expect(grid.children).toHaveLength(98);
    // Double-check via CSS grid-template-column count = ceil(98/7) = 14.
    expect((grid as HTMLElement).style.gridTemplateColumns).toContain("14");
    // Suppress lint-unused-var for container.
    expect(container.firstChild).not.toBeNull();
  });

  it("respects a custom horizon prop", () => {
    mocked.mockReturnValue({ data: DAYS, isLoading: false, error: null });
    render(<ExpiryHeatmap today={ANCHOR} horizon={21} />);
    const grid = screen.getByRole("img", {
      name: /Expiry heatmap — next 21 days/i,
    });
    expect(grid.children).toHaveLength(21);
  });

  it("adds a descriptive title on data-backed cells", () => {
    mocked.mockReturnValue({ data: DAYS, isLoading: false, error: null });
    render(<ExpiryHeatmap today={ANCHOR} horizon={21} />);
    // Day 0 = 2026-04-20 has 3 critical batches.
    const hit = screen.getByTitle(/2026-04-20 — 3 batches \(critical\)/);
    expect(hit).toBeInTheDocument();
  });

  it("singular 'batch' for count=1", () => {
    mocked.mockReturnValue({
      data: [
        { ...DAYS[1], date: "2026-04-21", batch_count: 1 },
      ] as ExpiryCalendarDay[],
      isLoading: false,
      error: null,
    });
    render(<ExpiryHeatmap today={ANCHOR} horizon={7} />);
    expect(
      screen.getByTitle(/2026-04-21 — 1 batch \(safe\)/),
    ).toBeInTheDocument();
  });

  it("days with no backend data show 'no expiries' in title", () => {
    mocked.mockReturnValue({ data: DAYS, isLoading: false, error: null });
    render(<ExpiryHeatmap today={ANCHOR} horizon={7} />);
    // 2026-04-21 is not in DAYS — should read 'no expiries'.
    expect(
      screen.getByTitle(/2026-04-21 — no expiries/),
    ).toBeInTheDocument();
  });

  it("renders the legend footer", () => {
    mocked.mockReturnValue({ data: DAYS, isLoading: false, error: null });
    render(<ExpiryHeatmap today={ANCHOR} />);
    expect(screen.getByText("Less")).toBeInTheDocument();
    expect(screen.getByText("More")).toBeInTheDocument();
  });

  it("lets explicit days prop override the hook", () => {
    mocked.mockReturnValue({
      data: [{ ...DAYS[0], batch_count: 99 }],
      isLoading: false,
      error: null,
    });
    render(<ExpiryHeatmap days={DAYS} today={ANCHOR} horizon={21} />);
    // 'batch_count=3' from the prop wins over hook's 99.
    expect(
      screen.getByTitle(/2026-04-20 — 3 batches \(critical\)/),
    ).toBeInTheDocument();
  });
});
