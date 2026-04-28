import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { useCallback } from "react";
import { ClinicalPanel } from "@/components/pos/terminal/ClinicalPanel";
import { usePosDrugClinical } from "@/hooks/use-pos-drug-clinical";

// Mock the hook so the inner panel renders without an API call.
vi.mock("@/hooks/use-pos-drug-clinical", () => ({
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
});
