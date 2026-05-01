import { HeartPulse } from "lucide-react";
import { cn } from "@shared/lib/utils";

/**
 * D1 placeholder for the Clinical / AI panel (v9 handoff §1.3 column 3).
 *
 * Shows a lightweight empty state when no SKU is active. The handoff
 * calls for this exact treatment — "mono eyebrow SELECT AN ITEM + short
 * Arabic hint. Do not show ghost stats." — so we don't fabricate
 * numbers before D2 wires real data.
 *
 * D2 replaces this file with the real `ClinicalPanel` that binds to the
 * active cart item and surfaces counseling tip, live stock, nearest
 * expiry, shelf location, margin, AI cross-sell, and generic
 * alternatives.
 *
 * Props are intentionally minimal — D1 just proves the 3-column
 * skeleton works end-to-end. `activeDrugCode` is accepted now so the
 * terminal page can already pass the selected item through even though
 * we don't consume it yet (zero-churn swap when D2 lands).
 */
interface ClinicalPanelSkeletonProps {
  activeDrugCode?: string | null;
  className?: string;
}

export function ClinicalPanelSkeleton({
  activeDrugCode,
  className,
}: ClinicalPanelSkeletonProps) {
  return (
    <section
      aria-label="Clinical and AI panel"
      data-testid="clinical-panel-skeleton"
      className={cn(
        "flex min-h-0 flex-col overflow-hidden rounded-3xl",
        "border border-[var(--pos-line)] bg-[var(--pos-panel)]/40",
        className,
      )}
    >
      {/* Pane head — mirrors the cart/catalog pane heads so all three
          columns read as a single typographic family. D6 will polish. */}
      <header
        className={cn(
          "flex items-center justify-between border-b border-[var(--pos-line)]",
          "bg-[var(--pos-card)] px-4 py-3",
        )}
      >
        <div className="flex items-center gap-2">
          <HeartPulse
            className="h-5 w-5 text-[var(--pos-accent)]"
            aria-hidden="true"
          />
          <h3 className="text-sm font-bold text-[var(--pos-ink)]">
            التثقيف والدعم السريري
          </h3>
        </div>
        <span className="pos-eyebrow" data-testid="clinical-panel-status">
          {activeDrugCode ? "LOADING" : "SELECT AN ITEM"}
        </span>
      </header>

      {/* Body — empty state per handoff "Empty / Loading / Error States"
          section. D2 replaces this body wholesale. */}
      <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
        <HeartPulse
          className="h-14 w-14 text-[var(--pos-ink-4)] opacity-50"
          aria-hidden="true"
        />
        <p className="pos-eyebrow">
          {activeDrugCode ? "Fetching clinical data…" : "Select an item"}
        </p>
        <p
          className="max-w-[220px] font-arabic text-xs leading-relaxed text-[var(--pos-ink-3)]"
          dir="rtl"
        >
          {activeDrugCode
            ? "جاري تحميل النصائح السريرية والبدائل المتاحة..."
            : "اختر صنفًا من السلة أو الأصناف السريعة لعرض النصائح السريرية."}
        </p>
      </div>
    </section>
  );
}
