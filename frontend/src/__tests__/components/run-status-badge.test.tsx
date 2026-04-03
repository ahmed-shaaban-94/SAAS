import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { RunStatusBadge } from "@/components/pipeline/run-status-badge";

describe("RunStatusBadge", () => {
  it.each([
    ["pending", "Pending"],
    ["running", "Running"],
    ["bronze_complete", "Bronze Done"],
    ["silver_complete", "Silver Done"],
    ["gold_complete", "Gold Done"],
    ["success", "Success"],
    ["failed", "Failed"],
  ])("renders '%s' status as '%s'", (status, label) => {
    render(<RunStatusBadge status={status} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("renders unknown status as raw text", () => {
    render(<RunStatusBadge status="custom_status" />);
    expect(screen.getByText("custom_status")).toBeInTheDocument();
  });

  it("applies correct color classes for success", () => {
    const { container } = render(<RunStatusBadge status="success" />);
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("emerald");
  });

  it("applies correct color classes for failed", () => {
    const { container } = render(<RunStatusBadge status="failed" />);
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("red");
  });
});
