import { describe, it, expect, vi, type Mock } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/hooks/use-pipeline-runs", () => ({
  usePipelineRuns: vi.fn(),
}));

import { usePipelineRuns } from "@/hooks/use-pipeline-runs";
import { SourceHealthBadge } from "@/components/dashboard/source-health-badge";

const mockHook = usePipelineRuns as unknown as Mock;

describe("SourceHealthBadge", () => {
  it("shows a shimmer placeholder while loading", () => {
    mockHook.mockReturnValue({ runs: [], isLoading: true, error: null });
    const { container } = render(<SourceHealthBadge />);
    expect(container.querySelector(".animate-pulse")).toBeInTheDocument();
  });

  it("shows 'No data yet' when no runs exist", () => {
    mockHook.mockReturnValue({ runs: [], isLoading: false, error: null });
    render(<SourceHealthBadge />);
    expect(screen.getByText(/no data yet/i)).toBeInTheDocument();
  });

  it("shows a green badge when last run succeeded", () => {
    mockHook.mockReturnValue({
      runs: [
        {
          id: "1",
          status: "success",
          finished_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
          started_at: new Date().toISOString(),
        },
      ],
      isLoading: false,
      error: null,
    });
    render(<SourceHealthBadge />);
    const el = screen.getByTitle(/data is current/i);
    expect(el).toBeInTheDocument();
  });

  it("shows a red badge when last run failed", () => {
    mockHook.mockReturnValue({
      runs: [
        {
          id: "2",
          status: "failed",
          finished_at: new Date().toISOString(),
          started_at: new Date().toISOString(),
        },
      ],
      isLoading: false,
      error: null,
    });
    render(<SourceHealthBadge />);
    const el = screen.getByTitle(/last run failed/i);
    expect(el).toBeInTheDocument();
  });
});
