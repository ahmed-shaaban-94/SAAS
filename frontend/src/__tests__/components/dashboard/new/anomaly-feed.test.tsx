import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/hooks/use-anomaly-cards", () => ({
  useAnomalyCards: vi.fn(),
}));

import { useAnomalyCards } from "@/hooks/use-anomaly-cards";
import { AnomalyFeed } from "@/components/dashboard/new/anomaly-feed";
import type { AnomalyCard } from "@/types/api";

const mocked = useAnomalyCards as unknown as Mock;

const CARDS: AnomalyCard[] = [
  {
    id: 1,
    kind: "down",
    title: "Revenue down -18%",
    body: "Revenue on 2026-04-18 was 82000 vs expected 100000.",
    time_ago: "2d ago",
    confidence: "high",
  },
  {
    id: 2,
    kind: "up",
    title: "Orders up +12%",
    body: "Orders on 2026-04-19 were 500 vs expected 450.",
    time_ago: "1d ago",
    confidence: "medium",
  },
  {
    id: 3,
    kind: "info",
    title: "Revenue flagged (suppressed)",
    body: "Suppressed on 2026-04-17 — Eid.",
    time_ago: "3d ago",
    confidence: "info",
  },
];

describe("AnomalyFeed", () => {
  beforeEach(() => {
    mocked.mockReset();
  });

  it("renders loading placeholder during initial fetch", () => {
    mocked.mockReturnValue({ data: undefined, isLoading: true, error: null });
    render(<AnomalyFeed />);
    expect(screen.getByLabelText("Loading anomalies")).toBeInTheDocument();
  });

  it("renders empty-state message when no anomalies", () => {
    mocked.mockReturnValue({ data: [], isLoading: false, error: null });
    render(<AnomalyFeed />);
    expect(
      screen.getByText(/No active anomalies/i),
    ).toBeInTheDocument();
  });

  it("renders one article per card with title, body, time_ago", () => {
    mocked.mockReturnValue({ data: CARDS, isLoading: false, error: null });
    render(<AnomalyFeed />);
    expect(screen.getByText("Revenue down -18%")).toBeInTheDocument();
    expect(screen.getByText("Orders up +12%")).toBeInTheDocument();
    expect(screen.getByText("Revenue flagged (suppressed)")).toBeInTheDocument();
    expect(screen.getByText("2d ago")).toBeInTheDocument();
  });

  it("shows confidence badge per card", () => {
    mocked.mockReturnValue({ data: CARDS, isLoading: false, error: null });
    render(<AnomalyFeed />);
    // 'high', 'medium', 'info' all rendered
    expect(screen.getByText("high")).toBeInTheDocument();
    expect(screen.getByText("medium")).toBeInTheDocument();
    expect(screen.getByText("info")).toBeInTheDocument();
  });

  it("lets explicit items prop override the hook", () => {
    mocked.mockReturnValue({
      data: [{ ...CARDS[0], title: "From hook" }],
      isLoading: false,
      error: null,
    });
    render(
      <AnomalyFeed items={[{ ...CARDS[0], title: "From prop" }]} />,
    );
    expect(screen.getByText("From prop")).toBeInTheDocument();
    expect(screen.queryByText("From hook")).toBeNull();
  });
});
