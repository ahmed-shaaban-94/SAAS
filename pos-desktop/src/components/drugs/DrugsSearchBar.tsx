import { forwardRef } from "react";
import { Search, ClipboardList } from "lucide-react";
import { cn } from "@shared/lib/utils";
import type { StockFilter, RxFilter } from "./types";

interface Props {
  query: string;
  onQueryChange: (v: string) => void;
  stockFilter: StockFilter;
  onStockFilterChange: (v: StockFilter) => void;
  rxFilter: RxFilter;
  onRxFilterChange: (v: RxFilter) => void;
  resultCount: number;
  totalCount: number;
  onOpenStocktaking: () => void;
}

export const DrugsSearchBar = forwardRef<HTMLInputElement, Props>(function DrugsSearchBar(
  {
    query,
    onQueryChange,
    stockFilter,
    onStockFilterChange,
    rxFilter,
    onRxFilterChange,
    resultCount,
    totalCount,
    onOpenStocktaking,
  },
  ref,
) {
  return (
    <div
      className={cn(
        "flex flex-col gap-2.5 rounded-xl px-4 py-3.5",
        "border border-cyan-400/30 bg-[rgba(8,24,38,0.7)]",
        "shadow-[0_0_0_1px_rgba(0,199,242,0.08),0_0_24px_rgba(0,199,242,0.1)]",
      )}
    >
      <div className="flex items-center gap-2.5">
        <Search className="h-5 w-5 shrink-0 text-cyan-300" aria-hidden="true" />
        <input
          ref={ref}
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="Search by name, SKU, category, or manufacturer…"
          aria-label="Search drugs"
          data-testid="drugs-search-input"
          data-pos-scanner-ignore=""
          autoComplete="off"
          spellCheck={false}
          className={cn(
            "flex-1 bg-transparent text-base font-medium",
            "text-text-primary placeholder:text-text-secondary focus:outline-none",
          )}
        />
        <span
          className="font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-text-secondary"
          data-testid="drugs-result-count"
        >
          {resultCount}
          <span className="text-text-secondary">/{totalCount}</span>
        </span>
        <kbd
          className={cn(
            "hidden rounded border border-border bg-surface-raised px-1.5 py-0.5",
            "font-mono text-[10px] uppercase tracking-wider text-text-secondary sm:inline-flex",
          )}
        >
          /
        </kbd>
      </div>

      <div className="flex flex-wrap items-center gap-1.5">
        <FilterChip
          label="All"
          active={stockFilter === "all"}
          onClick={() => onStockFilterChange("all")}
          testid="chip-stock-all"
        />
        <FilterChip
          label="Low stock"
          color="amber"
          active={stockFilter === "low"}
          onClick={() => onStockFilterChange("low")}
          testid="chip-stock-low"
        />
        <FilterChip
          label="Out of stock"
          color="red"
          active={stockFilter === "out"}
          onClick={() => onStockFilterChange("out")}
          testid="chip-stock-out"
        />

        <span className="mx-1 h-5 w-px bg-border" aria-hidden="true" />

        <FilterChip
          label="Any"
          active={rxFilter === "all"}
          onClick={() => onRxFilterChange("all")}
          testid="chip-rx-all"
        />
        <FilterChip
          label="Rx only"
          color="purple"
          active={rxFilter === "rx"}
          onClick={() => onRxFilterChange("rx")}
          testid="chip-rx-rx"
        />
        <FilterChip
          label="OTC"
          color="cyan"
          active={rxFilter === "otc"}
          onClick={() => onRxFilterChange("otc")}
          testid="chip-rx-otc"
        />

        <button
          type="button"
          onClick={onOpenStocktaking}
          data-testid="stocktaking-button"
          className={cn(
            "ms-auto inline-flex items-center gap-1.5 rounded-full px-3 py-1.5",
            "border border-purple-500/50 bg-purple-500/10 text-purple-300",
            "text-[11px] font-bold uppercase tracking-wider",
            "hover:bg-purple-500/15",
          )}
        >
          <ClipboardList className="h-3.5 w-3.5" aria-hidden="true" />
          <span>Stocktaking sheet</span>
          <kbd className="rounded border border-purple-500/40 bg-purple-500/15 px-1 py-0.5 text-[9px] text-purple-300">
            F6
          </kbd>
        </button>
      </div>
    </div>
  );
});

interface ChipProps {
  label: string;
  active: boolean;
  onClick: () => void;
  color?: "amber" | "red" | "purple" | "cyan";
  testid?: string;
}

function FilterChip({ label, active, onClick, color, testid }: ChipProps) {
  const colorClasses = {
    amber: active
      ? "border-amber-400 bg-amber-400/15 text-amber-300"
      : "border-border text-text-secondary",
    red: active
      ? "border-red-400 bg-red-400/15 text-red-300"
      : "border-border text-text-secondary",
    purple: active
      ? "border-purple-400 bg-purple-400/15 text-purple-300"
      : "border-border text-text-secondary",
    cyan: active
      ? "border-cyan-400 bg-cyan-400/15 text-cyan-300"
      : "border-border text-text-secondary",
    default: active
      ? "border-cyan-400 bg-cyan-400/15 text-cyan-300"
      : "border-border text-text-secondary",
  };
  const cls = color ? colorClasses[color] : colorClasses.default;
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      data-testid={testid}
      className={cn(
        "rounded-full border px-2.5 py-1 text-[11px] font-semibold",
        "transition-colors hover:text-text-primary",
        cls,
      )}
    >
      {label}
    </button>
  );
}
