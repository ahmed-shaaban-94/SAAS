import { memo } from "react";
import { PlusCircle } from "lucide-react";
import { cn } from "@shared/lib/utils";
import { cleanDrugName } from "@pos/lib/format-drug-name";
import { fmtEgp, type QuickPickItem, type QuickPickSignal } from "./types";

interface QuickPickGridProps {
  items: QuickPickItem[];
  onPick: (item: QuickPickItem) => void;
  shiftLabel?: string;
  txnCount?: number;
  avgBasket?: number;
  /**
   * When true, render 8 shimmer placeholders instead of the catalog
   * tiles. Use while the catalog SWR is in flight on first paint.
   */
  loading?: boolean;
}

// ── Signal palette ─────────────────────────────────────────────────────────────
const SIGNAL_ACCENT: Record<QuickPickSignal, string> = {
  default:     "bg-cyan-400",
  low_stock:   "bg-amber-400",
  reorder:     "bg-red-500",
  bonus:       "bg-yellow-400",
  in_stock:    "bg-green-400",
  alternative: "bg-violet-400",
};

const SIGNAL_PRICE: Record<QuickPickSignal, string> = {
  default:     "text-green-300",
  low_stock:   "text-amber-300",
  reorder:     "text-red-400",
  bonus:       "text-yellow-300",
  in_stock:    "text-green-300",
  alternative: "text-violet-300",
};

const SIGNAL_STOCK: Record<QuickPickSignal, string> = {
  default:     "text-text-secondary/60",
  low_stock:   "text-amber-300",
  reorder:     "text-red-400",
  bonus:       "text-text-secondary/60",
  in_stock:    "text-green-400",
  alternative: "text-violet-300",
};

const SIGNAL_LABEL: Record<QuickPickSignal, string | null> = {
  default:     null,
  low_stock:   "كمية محدودة",
  reorder:     "إعادة طلب",
  bonus:       null,
  in_stock:    null,
  alternative: "بديل",
};

function QuickPickGridInner({
  items,
  onPick,
  shiftLabel,
  txnCount,
  avgBasket,
  loading = false,
}: QuickPickGridProps) {
  // Pad to 8 (2-col × 4 rows) so the grid keeps its shape.
  const tiles: (QuickPickItem | null)[] = loading
    ? Array.from({ length: 8 }, () => null)
    : (() => {
        const t: (QuickPickItem | null)[] = [...items.slice(0, 8)];
        while (t.length < 8) t.push(null);
        return t;
      })();

  const showStripe = shiftLabel || txnCount !== undefined || avgBasket !== undefined;

  return (
    <div className="flex flex-col gap-2">
      {/* 2-column grid */}
      <div
        role="grid"
        aria-label="Quick pick favorites"
        className="rounded-xl border border-[var(--pos-line)] bg-[rgba(8,24,38,0.35)] p-2"
      >
        <div className="mb-2 flex items-center justify-between px-1">
          <span className="font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-text-secondary">
            أصناف سريعة{" "}
            <span className="font-normal text-text-secondary/60">· اضغط 1–8</span>
          </span>
        </div>
        <div className="grid grid-cols-2 gap-1.5">
          {tiles.map((tile, idx) => {
            const n = idx + 1;
            if (!tile) {
              if (loading) {
                return (
                  <div
                    key={`shim-${n}`}
                    role="gridcell"
                    aria-busy="true"
                    data-testid={`quick-pick-shimmer-${n}`}
                    style={{ height: 120 }}
                    className={cn(
                      "relative flex flex-col gap-2 overflow-hidden rounded-lg p-2.5",
                      "border border-[var(--pos-line)] bg-[rgba(8,24,38,0.45)]",
                    )}
                  >
                    <span
                      aria-hidden="true"
                      className={cn(
                        "pointer-events-none absolute inset-0",
                        "bg-gradient-to-r from-transparent via-cyan-400/10 to-transparent",
                        "bg-[length:200%_100%] motion-safe:animate-[shimmer_1.6s_linear_infinite]",
                      )}
                    />
                    <span className="h-3 w-1/3 rounded bg-white/[0.08]" />
                    <span className="h-4 w-3/4 rounded bg-white/[0.06]" />
                    <span className="mt-auto h-2.5 w-1/2 rounded bg-white/[0.05]" />
                  </div>
                );
              }
              return (
                <div
                  key={`empty-${n}`}
                  role="gridcell"
                  style={{ height: 120 }}
                  className={cn(
                    "flex flex-col gap-1 rounded-lg p-2.5",
                    "border border-dashed border-[var(--pos-line)] opacity-30",
                  )}
                >
                  <span className="font-mono text-[10px] text-text-secondary">{n}</span>
                </div>
              );
            }

            const sig: QuickPickSignal = tile.signal ?? "default";
            const accentBar = SIGNAL_ACCENT[sig];
            const priceColor = SIGNAL_PRICE[sig];
            const stockColor = SIGNAL_STOCK[sig];
            const sigLabel = SIGNAL_LABEL[sig];
            const isBonus = sig === "bonus";
            const stockCritical = sig === "reorder" || sig === "low_stock";

            return (
              <button
                key={tile.drug_code}
                type="button"
                role="gridcell"
                onClick={() => onPick(tile)}
                aria-label={`Quick pick ${n}: ${cleanDrugName(tile.drug_name)} at EGP ${fmtEgp(tile.unit_price)}`}
                data-testid={`quick-pick-${n}`}
                style={{ height: 120 }}
                className={cn(
                  "group relative flex flex-col overflow-hidden rounded-lg p-2.5 text-start",
                  "border border-b-2 border-[var(--pos-line)] bg-[rgba(8,24,38,0.7)]",
                  "transition-[background-color,border-color,transform,box-shadow] duration-150",
                  "hover:border-cyan-400/50 hover:bg-cyan-400/5",
                  // Lift + soft glow on hover (Gemini POV upgrade); no layout shift
                  "motion-safe:hover:-translate-y-[1px] motion-safe:hover:shadow-[0_6px_18px_-8px_rgba(0,199,242,0.45)]",
                  "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-cyan-400/40",
                  // Tactile press animation — respects prefers-reduced-motion via CSS
                  "active-tactile",
                )}
              >
                {/* 2px signal accent bar at top */}
                <span
                  aria-hidden="true"
                  className={cn("absolute inset-x-0 top-0 h-[2px]", accentBar)}
                />

                {/* Row 1: shortcut kbd + price chip + bonus star */}
                <div className="flex items-center justify-between gap-1">
                  <kbd
                    className={cn(
                      "grid h-[18px] min-w-[18px] place-items-center rounded border border-border bg-surface-raised px-1",
                      "font-mono text-[10px] font-semibold text-text-primary",
                    )}
                  >
                    {n}
                  </kbd>
                  <div className="flex items-center gap-1">
                    {isBonus && (
                      <span className="text-[11px] text-yellow-400" aria-label="bonus SKU">
                        ★
                      </span>
                    )}
                    <span className={cn("font-mono text-[12px] font-bold tabular-nums", priceColor)}>
                      {fmtEgp(tile.unit_price)}
                    </span>
                  </div>
                </div>

                {/* Row 2: Arabic product name */}
                <span
                  dir="rtl"
                  style={{ fontFamily: "var(--font-plex-arabic, sans-serif)", fontWeight: 700, fontSize: 14 }}
                  className="mt-1 line-clamp-2 flex-1 leading-tight text-text-primary"
                >
                  {tile.drug_name_ar ?? cleanDrugName(tile.drug_name)}
                </span>

                {/* Foot: stock + expiry */}
                <div className="mt-auto flex items-center justify-between gap-1">
                  {tile.stock_count !== undefined && (
                    <span className={cn("font-mono text-[9px] tabular-nums", stockColor)}>
                      {tile.stock_count}
                      {stockCritical && sigLabel ? ` · ${sigLabel}` : ""}
                    </span>
                  )}
                  {tile.expiry_date && (
                    <span className="font-mono text-[9px] text-text-secondary/60" dir="ltr">
                      {tile.expiry_date}
                    </span>
                  )}
                </div>

                {/* Add-to-cart overlay — only visible while button is pressed.
                    CSS-only, no extra state. */}
                <span
                  aria-hidden="true"
                  className={cn(
                    "pointer-events-none absolute inset-0 z-10",
                    "grid place-items-center bg-cyan-500/85 backdrop-blur-[2px]",
                    "opacity-0 group-active:opacity-100 transition-opacity duration-75",
                  )}
                >
                  <PlusCircle className="h-7 w-7 text-white drop-shadow" />
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Editorial stripe */}
      {showStripe && (
        <p
          className="px-1 font-mono text-[9px] uppercase tracking-[0.18em] text-text-secondary/50"
          dir="ltr"
        >
          {[
            shiftLabel,
            txnCount !== undefined && `${txnCount} transactions`,
            avgBasket !== undefined && `avg basket ${fmtEgp(avgBasket)} EGP`,
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>
      )}
    </div>
  );
}

function areQuickPickEqual(
  prev: QuickPickGridProps,
  next: QuickPickGridProps,
): boolean {
  return (
    prev.items === next.items &&
    prev.shiftLabel === next.shiftLabel &&
    prev.txnCount === next.txnCount &&
    prev.avgBasket === next.avgBasket &&
    prev.loading === next.loading
  );
}

export const QuickPickGrid = memo(QuickPickGridInner, areQuickPickEqual);
