import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("@/hooks/use-first-insight", () => ({
  useFirstInsight: vi.fn(),
}));

const mockDismissFirstInsight = vi.fn().mockResolvedValue({});
vi.mock("@/hooks/use-onboarding", () => ({
  useOnboarding: () => ({
    data: null,
    dismissFirstInsight: mockDismissFirstInsight,
    updateGoldenPathProgress: vi.fn().mockResolvedValue({}),
  }),
}));

import { useFirstInsight } from "@/hooks/use-first-insight";
import { FirstInsightCard } from "@/components/dashboard/first-insight-card";
import type { FirstInsight } from "@/types/api";

const mockedHook = useFirstInsight as unknown as Mock;

const SAMPLE: FirstInsight = {
  kind: "top_seller",
  title: "Your top seller: Paracetamol 500mg Tab",
  body: "drove $12,000 in 30 days",
  action_href: "/products",
  confidence: 0.72,
};

describe("FirstInsightCard", () => {
  beforeEach(() => {
    mockedHook.mockReset();
    sessionStorage.clear();
    mockDismissFirstInsight.mockReset().mockResolvedValue({});
  });

  it("renders null when hook returns no insight", () => {
    mockedHook.mockReturnValue({
      insight: null,
      isLoading: false,
      error: null,
    });
    const { container } = render(<FirstInsightCard />);
    expect(container.firstChild).toBeNull();
  });

  it("renders null while loading (no skeleton flash)", () => {
    mockedHook.mockReturnValue({
      insight: null,
      isLoading: true,
      error: null,
    });
    const { container } = render(<FirstInsightCard />);
    expect(container.firstChild).toBeNull();
  });

  it("renders title + body + action link when insight is available", () => {
    mockedHook.mockReturnValue({
      insight: SAMPLE,
      isLoading: false,
      error: null,
    });
    render(<FirstInsightCard />);

    expect(screen.getByText(SAMPLE.title)).toBeInTheDocument();
    expect(screen.getByText(SAMPLE.body)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /view more insights/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/insights");
  });

  it("renders a dismiss button", () => {
    mockedHook.mockReturnValue({
      insight: SAMPLE,
      isLoading: false,
      error: null,
    });
    render(<FirstInsightCard />);
    expect(
      screen.getByRole("button", { name: /dismiss/i }),
    ).toBeInTheDocument();
  });

  it("dismissing removes the card and persists the state", async () => {
    mockedHook.mockReturnValue({
      insight: SAMPLE,
      isLoading: false,
      error: null,
    });
    const { container } = render(<FirstInsightCard />);
    await userEvent.click(screen.getByRole("button", { name: /dismiss/i }));

    expect(container.firstChild).toBeNull();
    expect(sessionStorage.getItem("ttfi_first_insight_dismissed")).toBe("1");
  });

  it("stays dismissed on remount if sessionStorage flag is set", () => {
    sessionStorage.setItem("ttfi_first_insight_dismissed", "1");
    mockedHook.mockReturnValue({
      insight: SAMPLE,
      isLoading: false,
      error: null,
    });
    const { container } = render(<FirstInsightCard />);
    expect(container.firstChild).toBeNull();
  });

  it("displays a confidence badge", () => {
    mockedHook.mockReturnValue({
      insight: SAMPLE,
      isLoading: false,
      error: null,
    });
    render(<FirstInsightCard />);
    // Confidence stored as 0-1; shown as a percentage.
    expect(screen.getByText(/72%|confidence/i)).toBeInTheDocument();
  });

  it("calls dismissFirstInsight backend endpoint when dismissed", async () => {
    mockedHook.mockReturnValue({
      insight: SAMPLE,
      isLoading: false,
      error: null,
    });
    render(<FirstInsightCard />);
    await userEvent.click(screen.getByRole("button", { name: /dismiss/i }));

    await waitFor(() => expect(mockDismissFirstInsight).toHaveBeenCalledOnce());
  });
});
