"use client";

import { memo, Suspense } from "react";
import { HeartPulse, Plus, Stethoscope, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  usePosDrugClinical,
  type CrossSellItem,
  type AlternativeItem,
} from "@/hooks/use-pos-drug-clinical";
import { ClinicalPanelSkeleton } from "./ClinicalPanelSkeleton";

// ── Panel content meta-badges ────────────────────────────────────────────────
// Honest, discrete indicators about the *panel content*, not the drug:
//   - hasCounseling: was a counseling tip available for this SKU?
//   - hasAlternatives: did the alternatives endpoint return anything?
// A previous version of this file also rendered an "is controlled" badge
// derived from substring-matching English keywords against drug_category.
// That was removed because false-negatives on Arabic categories
// ("أدوية مراقبة", "مخدرات") would silently hide a regulatory-sounding
// claim. If a real controlled-substance signal is needed, surface it from
// the backend (e.g. `DrugDetail.is_controlled: boolean`) and re-introduce
// the badge keyed off that field.

interface ContentBadgesProps {
  hasCounseling: boolean;
  hasAlternatives: boolean;
}

function ContentBadges({ hasCounseling, hasAlternatives }: ContentBadgesProps) {
  return (
    <div
      className="flex shrink-0 flex-col items-end gap-1"
      data-testid="clinical-content-badges"
    >
      <span
        data-testid="badge-counseling"
        className={cn(
          "rounded-full border px-1.5 py-0.5 font-mono text-[8.5px] uppercase tracking-[0.15em]",
          hasCounseling
            ? "border-cyan-400/30 bg-cyan-400/10 text-cyan-300"
            : "border-white/10 bg-white/[0.04] text-[var(--pos-ink-3)]",
        )}
      >
        {hasCounseling ? "✓ نصيحة" : "— لا نصيحة"}
      </span>
      <span
        data-testid="badge-alternatives"
        className={cn(
          "rounded-full border px-1.5 py-0.5 font-mono text-[8.5px] uppercase tracking-[0.15em]",
          hasAlternatives
            ? "border-violet-400/30 bg-violet-400/10 text-violet-300"
            : "border-white/10 bg-white/[0.04] text-[var(--pos-ink-3)]",
        )}
      >
        {hasAlternatives ? "✓ بدائل" : "— لا بدائل"}
      </span>
    </div>
  );
}

// ── helpers ───────────────────────────────────────────────────────────────────

function fmtEgp(n: number): string {
  return n.toLocaleString("ar-EG", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

const EYEBROW =
  "font-mono text-[9.5px] font-bold uppercase tracking-[0.2em] text-[var(--pos-ink-3)]";

// ── SelectedSkuHeader ─────────────────────────────────────────────────────────

interface SelectedSkuHeaderProps {
  drugName: string;
  activeIngredient: string | null;
  drugCategory: string | null;
  badges?: ContentBadgesProps;
}

function SelectedSkuHeader({
  drugName,
  activeIngredient,
  drugCategory,
  badges,
}: SelectedSkuHeaderProps) {
  // Gemini POV port (2026-04-30): wrap header in a dark gradient card with
  // a subtle stethoscope watermark. Drug name is honest; no synthetic
  // safety-score or controlled-substance signals are derived here. The
  // existing ContentBadges (counseling / alternatives) remain as the
  // single source of clinical-content metadata.
  return (
    <div
      data-testid="clinical-header-card"
      className={cn(
        "relative overflow-hidden border-b border-[var(--pos-line)]",
        "bg-gradient-to-br from-slate-900 to-slate-800",
        "dark:from-black dark:to-slate-900",
        "px-4 py-4",
      )}
    >
      <Stethoscope
        aria-hidden="true"
        size={120}
        className="pointer-events-none absolute -bottom-6 start-2 rotate-12 text-white/[0.05]"
      />
      <div className="relative z-10 flex items-start gap-3">
        <div className="flex min-w-0 flex-1 flex-col gap-1.5">
          <p
            dir="rtl"
            className="truncate text-base font-black leading-snug text-white"
            title={drugName}
          >
            {drugName}
          </p>
          <div className="flex flex-wrap items-center gap-1.5">
            {activeIngredient && (
              <span className="rounded bg-[var(--pos-accent-fg)]/15 px-1.5 py-0.5 font-mono text-[8.5px] font-bold uppercase tracking-[0.15em] text-[var(--pos-accent-fg)]">
                {activeIngredient}
              </span>
            )}
            {drugCategory && (
              <span className="rounded bg-white/[0.08] px-1.5 py-0.5 font-mono text-[8.5px] uppercase tracking-[0.15em] text-white/70">
                {drugCategory}
              </span>
            )}
          </div>
        </div>
        {badges && <ContentBadges {...badges} />}
      </div>
    </div>
  );
}

// ── CounselingTipBox ──────────────────────────────────────────────────────────

function CounselingTipBox({ text }: { text: string }) {
  return (
    <div
      data-testid="counseling-tip-box"
      className={cn(
        "relative mx-3 mt-3 rounded-2xl px-4 py-3",
        "border border-[var(--pos-accent)]/25 bg-[var(--pos-accent)]/8",
      )}
    >
      {/* speech-bubble pointer */}
      <div className="absolute -top-[5px] start-5 h-2.5 w-2.5 rotate-45 border-s border-t border-[var(--pos-accent)]/25 bg-[var(--pos-accent)]/8" />
      <p
        dir="rtl"
        className="text-[12px] font-medium leading-relaxed text-[var(--pos-ink)]"
        style={{ fontFamily: "var(--font-plex-arabic, sans-serif)" }}
      >
        {text}
      </p>
    </div>
  );
}

// ── CrossSellList ─────────────────────────────────────────────────────────────

const REASON_TAG_COLORS: Record<string, string> = {
  ROUTE: "bg-purple-500/15 text-purple-300",
  PROTECT: "bg-blue-500/15 text-blue-300",
  PAIR: "bg-orange-500/15 text-orange-300",
};

interface CrossSellListProps {
  items: CrossSellItem[];
  onAdd?: (code: string) => void;
}

function CrossSellList({ items, onAdd }: CrossSellListProps) {
  if (items.length === 0) return null;
  return (
    <div data-testid="cross-sell-list" className="mx-3 mt-3">
      <p className={cn(EYEBROW, "mb-1.5")}>يُقترح معه</p>
      <div className="space-y-1">
        {items.map((item) => {
          const tagCls = REASON_TAG_COLORS[item.reason_tag] ?? "bg-white/[0.06] text-[var(--pos-ink-3)]";
          return (
            <div
              key={item.drug_code}
              className="flex items-center justify-between gap-2 rounded-lg border border-yellow-400/15 bg-yellow-400/[0.04] px-3 py-1.5"
            >
              <div className="flex min-w-0 flex-col gap-0.5">
                <span className="truncate text-[11.5px] font-semibold text-[var(--pos-ink)]">
                  {item.drug_name}
                </span>
                <span className={cn("rounded px-1 py-[1px] font-mono text-[8px] uppercase tracking-[0.15em] w-fit", tagCls)}>
                  {item.reason_tag}
                </span>
              </div>
              <div className="flex shrink-0 items-center gap-1.5">
                <span className="font-mono text-[11px] tabular-nums text-[var(--pos-ink-2)]">
                  {fmtEgp(item.unit_price)}
                </span>
                {onAdd && (
                  <button
                    type="button"
                    onClick={() => onAdd(item.drug_code)}
                    aria-label={`Add ${item.drug_name} to cart`}
                    className={cn(
                      "flex h-6 w-6 items-center justify-center rounded-md",
                      "bg-yellow-400/15 text-yellow-300 hover:bg-yellow-400/25",
                    )}
                  >
                    <Plus className="h-3 w-3" />
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── GenericAlternativesList ───────────────────────────────────────────────────

interface GenericAlternativesListProps {
  items: AlternativeItem[];
  onAdd?: (code: string) => void;
}

function GenericAlternativesList({ items, onAdd }: GenericAlternativesListProps) {
  if (items.length === 0) return null;
  return (
    <div data-testid="alternatives-list" className="mx-3 mt-3">
      <p className={cn(EYEBROW, "mb-1.5")}>بدائل جنيسة</p>
      <div className="space-y-1">
        {items.map((item) => (
          <div
            key={item.drug_code}
            className="flex items-center justify-between gap-2 rounded-lg border border-[var(--pos-line)] px-3 py-1.5"
          >
            <span
              className="truncate text-[11.5px] font-semibold text-[var(--pos-ink)]"
              dir="rtl"
            >
              {item.drug_name}
            </span>
            <div className="flex shrink-0 items-center gap-1.5">
              {item.savings_egp > 0 && (
                <span className="rounded-full bg-green-500/15 px-1.5 py-0.5 font-mono text-[8.5px] text-green-400">
                  -{fmtEgp(item.savings_egp)}
                </span>
              )}
              <span className="rounded bg-[var(--pos-accent)]/15 px-1.5 py-0.5 font-mono text-[10px] font-bold tabular-nums text-[var(--pos-accent)]">
                {fmtEgp(item.unit_price)}
              </span>
              {onAdd && (
                <button
                  type="button"
                  onClick={() => onAdd(item.drug_code)}
                  aria-label={`Add ${item.drug_name} to cart`}
                  className={cn(
                    "flex h-6 w-6 items-center justify-center rounded-md",
                    "bg-[var(--pos-accent)]/15 text-[var(--pos-accent)] hover:bg-[var(--pos-accent)]/25",
                  )}
                >
                  <Plus className="h-3 w-3" />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── ClinicalPanel ─────────────────────────────────────────────────────────────

interface ClinicalPanelProps {
  activeDrugCode?: string | null;
  onAddToCart?: (drugCode: string) => void;
  className?: string;
}

function ClinicalPanelInner({ activeDrugCode, onAddToCart, className }: ClinicalPanelProps) {
  const { detail, crossSell, alternatives, isLoading } = usePosDrugClinical(activeDrugCode);

  const statusLabel = !activeDrugCode
    ? "SELECT AN ITEM"
    : isLoading
      ? "LOADING…"
      : "CLINICAL";

  return (
    <section
      aria-label="Clinical and AI panel"
      data-testid="clinical-panel"
      className={cn(
        "flex min-h-0 flex-col overflow-hidden rounded-3xl",
        "border border-[var(--pos-line)] bg-[var(--pos-panel)]/40",
        className,
      )}
    >
      {/* Header */}
      <header className="flex items-center justify-between border-b border-[var(--pos-line)] bg-[var(--pos-card)] px-4 py-3">
        <div className="flex items-center gap-2">
          <HeartPulse className="h-5 w-5 text-[var(--pos-accent)]" aria-hidden="true" />
          <h3 className="text-sm font-bold text-[var(--pos-ink)]">التثقيف والدعم السريري</h3>
        </div>
        <span className={EYEBROW} data-testid="clinical-panel-status">
          {statusLabel}
        </span>
      </header>

      {/* Empty state */}
      {!activeDrugCode && (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
          <HeartPulse className="h-14 w-14 text-[var(--pos-ink-4)] opacity-50" aria-hidden="true" />
          <p className={EYEBROW}>Select an item</p>
          <p
            dir="rtl"
            className="max-w-[220px] text-xs leading-relaxed text-[var(--pos-ink-3)]"
            style={{ fontFamily: "var(--font-plex-arabic, sans-serif)" }}
          >
            اختر صنفًا من السلة أو الأصناف السريعة لعرض النصائح السريرية.
          </p>
        </div>
      )}

      {/* Loading skeleton */}
      {activeDrugCode && isLoading && (
        <div className="flex flex-1 flex-col gap-3 p-4 animate-pulse">
          <div className="h-4 w-3/4 rounded bg-white/[0.06]" />
          <div className="h-3 w-1/2 rounded bg-white/[0.04]" />
          <div className="mt-2 h-20 rounded-2xl bg-[var(--pos-accent)]/5" />
          <div className="h-3 w-2/3 rounded bg-white/[0.04]" />
          <div className="h-12 rounded-lg bg-white/[0.03]" />
        </div>
      )}

      {/* Content */}
      {activeDrugCode && !isLoading && detail && (
        <div className="flex flex-1 flex-col overflow-y-auto pb-3">
          <SelectedSkuHeader
            drugName={detail.drug_name}
            activeIngredient={detail.active_ingredient}
            drugCategory={detail.drug_category}
            badges={{
              hasCounseling: !!detail.counseling_text,
              hasAlternatives: alternatives.length > 0,
            }}
          />

          {detail.counseling_text ? (
            <CounselingTipBox text={detail.counseling_text} />
          ) : (
            <div className="mx-3 mt-3 flex items-center gap-2 rounded-xl border border-[var(--pos-line)] px-3 py-2.5">
              <Zap className="h-3.5 w-3.5 shrink-0 text-[var(--pos-ink-4)]" aria-hidden="true" />
              <p className="text-[11px] text-[var(--pos-ink-3)]">لا توجد نصائح سريرية لهذا الصنف.</p>
            </div>
          )}

          <CrossSellList items={crossSell} onAdd={onAddToCart} />
          <GenericAlternativesList items={alternatives} onAdd={onAddToCart} />
        </div>
      )}

      {/* Drug not found after loading */}
      {activeDrugCode && !isLoading && !detail && (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
          <p className={EYEBROW}>Not found</p>
          <p className="text-xs text-[var(--pos-ink-3)]" dir="rtl">
            تعذّر تحميل بيانات هذا الصنف.
          </p>
        </div>
      )}
    </section>
  );
}

function ClinicalPanelWrapper(props: ClinicalPanelProps) {
  return (
    <Suspense fallback={<ClinicalPanelSkeleton activeDrugCode={props.activeDrugCode} className={props.className} />}>
      <ClinicalPanelInner {...props} />
    </Suspense>
  );
}

function areClinicalPanelPropsEqual(prev: ClinicalPanelProps, next: ClinicalPanelProps): boolean {
  return (
    prev.activeDrugCode === next.activeDrugCode &&
    prev.className === next.className &&
    prev.onAddToCart === next.onAddToCart
  );
}

/**
 * Public export: wraps ClinicalPanelInner in a Suspense boundary so the rest
 * of the terminal layout never stalls on the clinical data fetch.
 * Memoized with an explicit comparator over the three props this component reads.
 */
export const ClinicalPanel = memo(ClinicalPanelWrapper, areClinicalPanelPropsEqual);
