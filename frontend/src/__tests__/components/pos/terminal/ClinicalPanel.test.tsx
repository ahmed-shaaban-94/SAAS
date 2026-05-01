import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { useCallback } from "react";
import { ClinicalPanel } from "@pos/components/terminal/ClinicalPanel";
import { usePosDrugClinical } from "@pos/hooks/use-pos-drug-clinical";

// Mock the hook so the inner panel renders without an API call.
vi.mock("@pos/hooks/use-pos-drug-clinical", () => ({
  usePosDrugClinical: vi.fn(() => ({
    detail: null,
    crossSell: [],
    alternatives: [],
    isLoading: false,
  })),
}));

// Render Suspense children synchronously — jsdom doesn't need async Suspense.
vi.mock("react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react")>();
  return {
    ...actual,
    Suspense: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

describe("ClinicalPanel memo", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * Verifies that a parent re-render with an unrelated prop change does NOT
   * cause ClinicalPanel to re-render. We measure this by counting how many
   * times the inner hook is called — a memo skip means zero extra calls.
   *
   * The onAddToCart callback is stabilised with useCallback so its reference
   * stays the same across parent re-renders, which is the invariant the
   * areClinicalPanelPropsEqual comparator relies on.
   */
  it("does not re-render when an unrelated parent prop changes", () => {
    function Parent({ unrelated }: { unrelated: number }) {
      // Stable ref — comparator checks onAddToCart identity.
      const handleAdd = useCallback((_code: string) => {}, []);
      return (
        <div data-unrelated={unrelated}>
          <ClinicalPanel activeDrugCode={null} onAddToCart={handleAdd} />
        </div>
      );
    }

    const { rerender } = render(<Parent unrelated={1} />);

    // Hook was called once on mount.
    expect(usePosDrugClinical).toHaveBeenCalledTimes(1);

    // Re-render parent with a different unrelated prop — activeDrugCode and
    // onAddToCart are identical, so the comparator returns true → memo skips.
    rerender(<Parent unrelated={2} />);

    // Still exactly one call — the inner component did NOT re-render.
    expect(usePosDrugClinical).toHaveBeenCalledTimes(1);
  });

  it("re-renders when activeDrugCode changes", () => {
    const { rerender } = render(<ClinicalPanel activeDrugCode={null} />);
    expect(usePosDrugClinical).toHaveBeenCalledTimes(1);

    // Changing activeDrugCode must force a re-render.
    rerender(<ClinicalPanel activeDrugCode="MED-001" />);
    expect(usePosDrugClinical).toHaveBeenCalledTimes(2);
  });

  it("shows SELECT AN ITEM status when no activeDrugCode is provided", () => {
    render(<ClinicalPanel activeDrugCode={null} />);
    expect(screen.getByTestId("clinical-panel")).toBeInTheDocument();
    expect(screen.getByTestId("clinical-panel-status")).toHaveTextContent("SELECT AN ITEM");
  });

  describe("content meta-badges (Gemini POV follow-up)", () => {
    it("shows the counseling badge as truthy when counseling_text is present", () => {
      vi.mocked(usePosDrugClinical).mockReturnValue({
        detail: {
          drug_code: "MED-002",
          drug_name: "Vitamin C",
          drug_brand: null,
          drug_cluster: null,
          drug_category: "vitamins",
          unit_price: 10,
          counseling_text: "Take with water",
          active_ingredient: "ascorbic acid",
        },
        crossSell: [],
        alternatives: [],
        isLoading: false,
        error: null,
      });
      render(<ClinicalPanel activeDrugCode="MED-002" />);
      expect(screen.getByTestId("badge-counseling")).toHaveTextContent(/نصيحة/);
    });

    it("shows the alternatives badge as falsy when alternatives is empty", () => {
      vi.mocked(usePosDrugClinical).mockReturnValue({
        detail: {
          drug_code: "MED-004",
          drug_name: "Test",
          drug_brand: null,
          drug_cluster: null,
          drug_category: "general",
          unit_price: 10,
          counseling_text: null,
          active_ingredient: null,
        },
        crossSell: [],
        alternatives: [],
        isLoading: false,
        error: null,
      });
      render(<ClinicalPanel activeDrugCode="MED-004" />);
      expect(screen.getByTestId("badge-alternatives")).toHaveTextContent(
        /لا بدائل/,
      );
    });

    it("renders the dark gradient header card with the drug name (Gemini POV port)", () => {
      vi.mocked(usePosDrugClinical).mockReturnValue({
        detail: {
          drug_code: "MED-005",
          drug_name: "أوجمنتين",
          drug_brand: null,
          drug_cluster: null,
          drug_category: "antibiotic",
          unit_price: 95.5,
          counseling_text: null,
          active_ingredient: "Amoxicillin",
        },
        crossSell: [],
        alternatives: [],
        isLoading: false,
        error: null,
      });
      render(<ClinicalPanel activeDrugCode="MED-005" />);
      const header = screen.getByTestId("clinical-header-card");
      expect(header).toBeInTheDocument();
      expect(header).toHaveTextContent("أوجمنتين");
      // The new header card MUST NOT introduce a safety-score-gauge or
      // badge-controlled — guardrail still holds inside the new layout.
      expect(screen.queryByTestId("safety-score-gauge")).not.toBeInTheDocument();
      expect(screen.queryByTestId("badge-controlled")).not.toBeInTheDocument();
    });

    it("does not display any aggregate 0-100 number, controlled-substance claim, or other invented clinical signal", () => {
      vi.mocked(usePosDrugClinical).mockReturnValue({
        detail: {
          drug_code: "MED-003",
          drug_name: "Test",
          drug_brand: null,
          drug_cluster: null,
          // Even when category contains the English word "narcotic", the
          // component must NOT render a regulatory-sounding badge —
          // substring matching on a free-text Arabic-language category
          // field would produce false-negatives ("أدوية مراقبة" wouldn't
          // match) and is unsafe to surface as a regulatory claim.
          drug_category: "narcotic",
          unit_price: 10,
          counseling_text: null,
          active_ingredient: null,
        },
        crossSell: [],
        alternatives: [],
        isLoading: false,
        error: null,
      });
      render(<ClinicalPanel activeDrugCode="MED-003" />);
      // Guardrails — three artifacts that previous versions of this file
      // rendered. None of them should ever come back without a real
      // backend-sourced field and an explicit design review.
      expect(screen.queryByTestId("safety-score-gauge")).not.toBeInTheDocument();
      expect(screen.queryByTestId("badge-controlled")).not.toBeInTheDocument();
    });
  });
});
