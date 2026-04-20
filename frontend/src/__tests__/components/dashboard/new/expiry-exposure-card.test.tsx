import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/hooks/use-expiry-exposure", () => ({
  useExpiryExposure: vi.fn(),
}));

import { useExpiryExposure } from "@/hooks/use-expiry-exposure";
import { ExpiryExposureCard } from "@/components/dashboard/new/expiry-exposure-card";
import type { ExpiryExposureTier } from "@/types/api";

const mocked = useExpiryExposure as unknown as Mock;

const TIERS: ExpiryExposureTier[] = [
  { tier: "30d", label: "Within 30 days", total_egp: 48000, batch_count: 4, tone: "red" },
  { tier: "60d", label: "31-60 days", total_egp: 62000, batch_count: 5, tone: "amber" },
  { tier: "90d", label: "61-90 days", total_egp: 32000, batch_count: 3, tone: "green" },
];

describe("ExpiryExposureCard", () => {
  beforeEach(() => {
    mocked.mockReset();
  });

  it("renders loading placeholder during initial fetch", () => {
    mocked.mockReturnValue({ data: undefined, isLoading: true, error: null });
    render(<ExpiryExposureCard />);
    expect(screen.getByLabelText("Loading expiry exposure")).toBeInTheDocument();
  });

  it("renders three tiers with labels + compact EGP + batch counts", () => {
    mocked.mockReturnValue({ data: TIERS, isLoading: false, error: null });
    render(<ExpiryExposureCard />);
    expect(screen.getByText("Within 30 days")).toBeInTheDocument();
    expect(screen.getByText("31-60 days")).toBeInTheDocument();
    expect(screen.getByText("61-90 days")).toBeInTheDocument();
    expect(screen.getByText("EGP 48K")).toBeInTheDocument();
    expect(screen.getByText("EGP 62K")).toBeInTheDocument();
    expect(screen.getByText("EGP 32K")).toBeInTheDocument();
    expect(screen.getByText("4 batches")).toBeInTheDocument();
  });

  it("singular 'batch' for count=1", () => {
    mocked.mockReturnValue({
      data: [{ ...TIERS[0], batch_count: 1 }],
      isLoading: false,
      error: null,
    });
    render(<ExpiryExposureCard />);
    expect(screen.getByText("1 batch")).toBeInTheDocument();
  });

  it("renders zero-valued tiers when tenant has no near-expiry stock", () => {
    const empty = TIERS.map((t) => ({
      ...t,
      total_egp: 0,
      batch_count: 0,
    }));
    mocked.mockReturnValue({ data: empty, isLoading: false, error: null });
    render(<ExpiryExposureCard />);
    const zeros = screen.getAllByText("EGP 0");
    expect(zeros).toHaveLength(3);
  });

  it("lets explicit tiers prop override the hook", () => {
    mocked.mockReturnValue({
      data: [{ ...TIERS[0], total_egp: 1 }],
      isLoading: false,
      error: null,
    });
    render(<ExpiryExposureCard tiers={TIERS} />);
    expect(screen.getByText("EGP 48K")).toBeInTheDocument();
  });

  it("scales into millions correctly", () => {
    mocked.mockReturnValue({
      data: [{ ...TIERS[0], total_egp: 2_500_000 }],
      isLoading: false,
      error: null,
    });
    render(<ExpiryExposureCard />);
    expect(screen.getByText("EGP 2.5M")).toBeInTheDocument();
  });
});
