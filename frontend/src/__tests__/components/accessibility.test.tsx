import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProgressBar } from "@/components/shared/progress-bar";
import { ChartCard } from "@/components/shared/chart-card";

describe("ProgressBar accessibility", () => {
  it("has progressbar role with correct aria attributes", () => {
    render(<ProgressBar value={65} label="65%" />);
    const bar = screen.getByRole("progressbar");
    expect(bar).toBeInTheDocument();
    expect(bar).toHaveAttribute("aria-valuenow", "65");
    expect(bar).toHaveAttribute("aria-valuemin", "0");
    expect(bar).toHaveAttribute("aria-valuemax", "100");
  });

  it("clamps value between 0 and 100", () => {
    const { rerender } = render(<ProgressBar value={150} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");

    rerender(<ProgressBar value={-20} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "0");
  });

  it("includes label in aria-label when provided", () => {
    render(<ProgressBar value={42} label="42%" />);
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-label",
      "42% progress",
    );
  });

  it("uses generic label when no label prop", () => {
    render(<ProgressBar value={50} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-label",
      "Progress",
    );
  });
});

describe("ChartCard accessibility", () => {
  it("renders as a section landmark with aria-label", () => {
    render(
      <ChartCard title="Monthly Revenue">
        <div>Chart content</div>
      </ChartCard>,
    );
    const section = screen.getByRole("region", { name: "Monthly Revenue" });
    expect(section).toBeInTheDocument();
  });

  it("renders title in heading element", () => {
    render(
      <ChartCard title="Sales Breakdown">
        <div>Content</div>
      </ChartCard>,
    );
    expect(screen.getByText("Sales Breakdown")).toBeInTheDocument();
  });

  it("renders subtitle as KPI value", () => {
    render(
      <ChartCard title="Revenue" subtitle="1,234 EGP">
        <div>Content</div>
      </ChartCard>,
    );
    const section = screen.getByRole("region");
    expect(within(section).getByText("1,234 EGP")).toBeInTheDocument();
  });
});
