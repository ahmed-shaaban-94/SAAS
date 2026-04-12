import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { RankingFilter, RANK_PRESETS } from "@/components/custom-report/ranking-filter";

const defaultProps = {
  selectedMetrics: [],
  rankLimit: 0,
  sortField: null,
  sortDirection: "desc" as const,
  onRankLimitChange: vi.fn(),
  onSortFieldChange: vi.fn(),
  onSortDirectionChange: vi.fn(),
};

describe("RankingFilter", () => {
  it("renders all rank preset buttons", () => {
    render(<RankingFilter {...defaultProps} />);
    for (const preset of RANK_PRESETS) {
      expect(screen.getByText(preset.label)).toBeInTheDocument();
    }
  });

  it("highlights the active rank limit preset", () => {
    render(<RankingFilter {...defaultProps} rankLimit={10} />);
    const top10 = screen.getByText("Top 10");
    expect(top10).toHaveClass("bg-accent");
  });

  it("calls onRankLimitChange when a preset is clicked", () => {
    const onRankLimitChange = vi.fn();
    render(<RankingFilter {...defaultProps} onRankLimitChange={onRankLimitChange} />);
    fireEvent.click(screen.getByText("Top 25"));
    expect(onRankLimitChange).toHaveBeenCalledWith(25);
  });

  it("hides sort controls when no metrics selected", () => {
    render(<RankingFilter {...defaultProps} selectedMetrics={[]} />);
    expect(screen.queryByText(/sort by/i)).not.toBeInTheDocument();
  });

  it("shows sort controls when metrics are selected", () => {
    render(<RankingFilter {...defaultProps} selectedMetrics={["revenue", "transactions"]} />);
    expect(screen.getByText(/sort by/i)).toBeInTheDocument();
  });

  it("calls onSortFieldChange when a metric sort button is clicked", () => {
    const onSortFieldChange = vi.fn();
    render(
      <RankingFilter
        {...defaultProps}
        selectedMetrics={["revenue"]}
        onSortFieldChange={onSortFieldChange}
      />,
    );
    // Find the metric button (uses friendlyMetricLabel)
    const buttons = screen.getAllByRole("button");
    const metricBtn = buttons.find((b) => b.textContent?.match(/revenue/i));
    expect(metricBtn).toBeTruthy();
    fireEvent.click(metricBtn!);
    expect(onSortFieldChange).toHaveBeenCalledWith("revenue");
  });

  it("toggles sortField off when clicking the active sort field", () => {
    const onSortFieldChange = vi.fn();
    render(
      <RankingFilter
        {...defaultProps}
        selectedMetrics={["revenue"]}
        sortField="revenue"
        onSortFieldChange={onSortFieldChange}
      />,
    );
    const buttons = screen.getAllByRole("button");
    const metricBtn = buttons.find((b) => b.textContent?.match(/revenue/i));
    fireEvent.click(metricBtn!);
    expect(onSortFieldChange).toHaveBeenCalledWith(null);
  });

  it("shows direction toggle when a sort field is active", () => {
    render(
      <RankingFilter
        {...defaultProps}
        selectedMetrics={["revenue"]}
        sortField="revenue"
        sortDirection="desc"
      />,
    );
    expect(screen.getByText("High to Low")).toBeInTheDocument();
  });

  it("calls onSortDirectionChange when direction toggle is clicked", () => {
    const onSortDirectionChange = vi.fn();
    render(
      <RankingFilter
        {...defaultProps}
        selectedMetrics={["revenue"]}
        sortField="revenue"
        sortDirection="desc"
        onSortDirectionChange={onSortDirectionChange}
      />,
    );
    fireEvent.click(screen.getByText("High to Low"));
    expect(onSortDirectionChange).toHaveBeenCalledWith("asc");
  });

  it("shows Low to High label when direction is asc", () => {
    render(
      <RankingFilter
        {...defaultProps}
        selectedMetrics={["revenue"]}
        sortField="revenue"
        sortDirection="asc"
      />,
    );
    expect(screen.getByText("Low to High")).toBeInTheDocument();
  });
});
