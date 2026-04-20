import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/hooks/use-sites", () => ({
  useSites: vi.fn(),
}));

import { useSites } from "@/hooks/use-sites";
import { BranchList } from "@/components/dashboard/new/branch-list";
import type { RankingItem } from "@/types/api";

const mocked = useSites as unknown as Mock;

const ITEMS: RankingItem[] = [
  {
    rank: 1,
    key: 1,
    name: "Cairo Main",
    value: 1_200_000,
    pct_of_total: 55,
    staff_count: 12,
  },
  {
    rank: 2,
    key: 2,
    name: "Alexandria",
    value: 600_000,
    pct_of_total: 28,
    staff_count: 5,
  },
  {
    rank: 3,
    key: 3,
    name: "Giza",
    value: 375_000,
    pct_of_total: 17,
    // staff_count intentionally omitted
  },
];

describe("BranchList", () => {
  beforeEach(() => {
    mocked.mockReset();
  });

  it("renders loading placeholder during initial fetch", () => {
    mocked.mockReturnValue({ data: undefined, isLoading: true, error: null });
    render(<BranchList />);
    expect(screen.getByLabelText("Loading branches")).toBeInTheDocument();
  });

  it("renders empty state when no branches", () => {
    mocked.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      error: null,
    });
    render(<BranchList />);
    expect(
      screen.getByText(/No branches found/i),
    ).toBeInTheDocument();
  });

  it("renders one row per branch with rank + name + revenue", () => {
    mocked.mockReturnValue({
      data: { items: ITEMS, total: 2_175_000 },
      isLoading: false,
      error: null,
    });
    render(<BranchList />);
    expect(screen.getByText("Cairo Main")).toBeInTheDocument();
    expect(screen.getByText("EGP 1.20M")).toBeInTheDocument();
    expect(screen.getByText("55.0%")).toBeInTheDocument();
  });

  it("renders staff count when present and hides it when absent", () => {
    mocked.mockReturnValue({
      data: { items: ITEMS, total: 2_175_000 },
      isLoading: false,
      error: null,
    });
    render(<BranchList />);
    expect(screen.getByText("12 staff")).toBeInTheDocument();
    expect(screen.getByText("5 staff")).toBeInTheDocument();
    // Giza row: no staff_count → no 'staff' text for it.
    expect(screen.queryByText("3 staff")).toBeNull();
  });

  it("exposes share bar as a progressbar with aria-valuenow", () => {
    mocked.mockReturnValue({
      data: { items: [ITEMS[0]], total: 1_200_000 },
      isLoading: false,
      error: null,
    });
    render(<BranchList />);
    const bar = screen.getByRole("progressbar", { name: /Cairo Main share/i });
    expect(bar).toHaveAttribute("aria-valuenow", "55");
  });

  it("lets explicit items prop override the hook", () => {
    mocked.mockReturnValue({
      data: { items: [{ ...ITEMS[0], name: "From hook" }], total: 0 },
      isLoading: false,
      error: null,
    });
    render(<BranchList items={ITEMS} />);
    expect(screen.getByText("Cairo Main")).toBeInTheDocument();
    expect(screen.queryByText("From hook")).toBeNull();
  });
});
