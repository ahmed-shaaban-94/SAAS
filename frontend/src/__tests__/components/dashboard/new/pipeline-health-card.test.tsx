import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/hooks/use-pipeline-health", () => ({
  usePipelineHealth: vi.fn(),
}));

import { usePipelineHealth } from "@/hooks/use-pipeline-health";
import { PipelineHealthCard } from "@/components/dashboard/new/pipeline-health-card";
import type { PipelineHealth } from "@/types/api";

const mocked = usePipelineHealth as unknown as Mock;

const SAMPLE: PipelineHealth = {
  nodes: [
    { label: "Bronze", value: "1.13M rows", status: "ok" },
    { label: "Silver", value: "Running...", status: "running" },
    { label: "Gold", value: "47 rows", status: "pending" },
  ],
  last_run: { at: "2026-04-20T04:12:00Z", duration_seconds: 522 },
  next_run_at: null,
  gates: { passed: 47, total: 47 },
  tests: { passed: 154, total: 154 },
  history_7d: [
    { date: "2026-04-14", duration_seconds: 380, status: "ok" },
    { date: "2026-04-15", duration_seconds: 420, status: "ok" },
    { date: "2026-04-16", duration_seconds: 900, status: "warning" },
    { date: "2026-04-17", duration_seconds: null, status: "fail" },
    { date: "2026-04-18", duration_seconds: null, status: "none" },
    { date: "2026-04-19", duration_seconds: 450, status: "ok" },
    { date: "2026-04-20", duration_seconds: 522, status: "ok" },
  ],
};

describe("PipelineHealthCard", () => {
  beforeEach(() => {
    mocked.mockReset();
  });

  it("renders loading placeholder during initial fetch", () => {
    mocked.mockReturnValue({ data: undefined, isLoading: true, error: null });
    render(<PipelineHealthCard />);
    expect(screen.getByLabelText("Loading pipeline health")).toBeInTheDocument();
  });

  it("renders three medallion nodes in Bronze → Silver → Gold order", () => {
    mocked.mockReturnValue({ data: SAMPLE, isLoading: false, error: null });
    render(<PipelineHealthCard />);
    expect(screen.getByText("Bronze")).toBeInTheDocument();
    expect(screen.getByText("Silver")).toBeInTheDocument();
    expect(screen.getByText("Gold")).toBeInTheDocument();
    expect(screen.getByText("1.13M rows")).toBeInTheDocument();
    expect(screen.getByText("Running...")).toBeInTheDocument();
  });

  it("renders gates + tests counters", () => {
    mocked.mockReturnValue({ data: SAMPLE, isLoading: false, error: null });
    render(<PipelineHealthCard />);
    expect(screen.getByText("47 / 47")).toBeInTheDocument();
    expect(screen.getByText("154 / 154")).toBeInTheDocument();
  });

  it("renders em-dash for next_run_at when null", () => {
    mocked.mockReturnValue({ data: SAMPLE, isLoading: false, error: null });
    render(<PipelineHealthCard />);
    const nextRunSection = screen.getByText("Next run").parentElement;
    expect(nextRunSection).toHaveTextContent("—");
  });

  it("renders 7-day history bar chart with aria label", () => {
    mocked.mockReturnValue({ data: SAMPLE, isLoading: false, error: null });
    render(<PipelineHealthCard />);
    const chart = screen.getByLabelText(
      "Pipeline run history for the last 7 days",
    );
    expect(chart).toBeInTheDocument();
  });

  it("lets explicit health prop override the hook", () => {
    mocked.mockReturnValue({
      data: { ...SAMPLE, gates: { passed: 0, total: 0 } },
      isLoading: false,
      error: null,
    });
    render(<PipelineHealthCard health={SAMPLE} />);
    expect(screen.getByText("47 / 47")).toBeInTheDocument();
  });
});
