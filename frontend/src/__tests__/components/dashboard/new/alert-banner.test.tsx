import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/hooks/use-top-insight", () => ({
  useTopInsight: vi.fn(),
}));

import { useTopInsight } from "@/hooks/use-top-insight";
import { AlertBanner } from "@/components/dashboard/new/alert-banner";
import type { TopInsight } from "@/types/api";

const mocked = useTopInsight as unknown as Mock;

const SAMPLE: TopInsight = {
  title: "Maadi branch revenue down 18%",
  body: "Unusual drop vs forecast.",
  expected_impact_egp: 86000,
  action_label: "Investigate",
  action_target: "/dashboard/anomalies/142",
  confidence: "high",
  generated_at: "2026-04-20T04:14:00Z",
};

describe("AlertBanner", () => {
  beforeEach(() => {
    mocked.mockReset();
  });

  it("renders null when hook returns no insight (204 path)", () => {
    mocked.mockReturnValue({ data: null, isLoading: false, error: null });
    const { container } = render(<AlertBanner />);
    expect(container.firstChild).toBeNull();
  });

  it("renders null during initial load (no skeleton flash)", () => {
    mocked.mockReturnValue({ data: undefined, isLoading: true, error: null });
    const { container } = render(<AlertBanner />);
    expect(container.firstChild).toBeNull();
  });

  it("renders title + body + CTA when insight present", () => {
    mocked.mockReturnValue({ data: SAMPLE, isLoading: false, error: null });
    render(<AlertBanner />);
    expect(
      screen.getByText("Maadi branch revenue down 18%"),
    ).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /Investigate/i });
    expect(link).toHaveAttribute("href", "/dashboard/anomalies/142");
  });

  it("formats expected impact compactly (K / M)", () => {
    mocked.mockReturnValue({ data: SAMPLE, isLoading: false, error: null });
    render(<AlertBanner />);
    expect(screen.getByText(/EGP 86K/)).toBeInTheDocument();
  });

  it("hides impact line when expected_impact_egp is null", () => {
    mocked.mockReturnValue({
      data: { ...SAMPLE, expected_impact_egp: null },
      isLoading: false,
      error: null,
    });
    render(<AlertBanner />);
    expect(screen.queryByText(/Expected impact/)).toBeNull();
  });

  it("hides impact line when expected_impact_egp is 0", () => {
    mocked.mockReturnValue({
      data: { ...SAMPLE, expected_impact_egp: 0 },
      isLoading: false,
      error: null,
    });
    render(<AlertBanner />);
    expect(screen.queryByText(/Expected impact/)).toBeNull();
  });

  it("lets explicit insight prop override the hook", () => {
    mocked.mockReturnValue({
      data: { ...SAMPLE, title: "From hook" },
      isLoading: false,
      error: null,
    });
    render(<AlertBanner insight={{ ...SAMPLE, title: "From prop" }} />);
    expect(screen.getByText("From prop")).toBeInTheDocument();
    expect(screen.queryByText("From hook")).toBeNull();
  });

  it("prop insight=null hides the banner even when hook has data", () => {
    mocked.mockReturnValue({ data: SAMPLE, isLoading: false, error: null });
    const { container } = render(<AlertBanner insight={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("uses status role with descriptive aria-label", () => {
    mocked.mockReturnValue({ data: SAMPLE, isLoading: false, error: null });
    render(<AlertBanner />);
    const region = screen.getByRole("status");
    expect(region).toHaveAttribute(
      "aria-label",
      expect.stringContaining("Maadi branch revenue down 18%"),
    );
  });
});
