import { cn } from "@shared/lib/utils";
import type { StockTag } from "./types";

interface Props {
  qty: number;
  tag: StockTag;
}

const PALETTE: Record<StockTag, { label: string; container: string; value: string }> = {
  out: {
    label: "Out",
    container: "border-red-400/40 bg-red-400/15",
    value: "text-red-300",
  },
  low: {
    label: "Low",
    container: "border-amber-400/40 bg-amber-400/15",
    value: "text-amber-300",
  },
  watch: {
    label: "Watch",
    container: "border-yellow-300/30 bg-yellow-300/10",
    value: "text-yellow-200",
  },
  ok: {
    label: "OK",
    container: "border-emerald-400/30 bg-emerald-400/10",
    value: "text-emerald-300",
  },
  unknown: {
    label: "—",
    container: "border-border bg-surface-raised/60",
    value: "text-text-secondary",
  },
};

export function StockPill({ qty, tag }: Props) {
  const palette = PALETTE[tag];
  return (
    <div
      className={cn(
        "inline-flex min-w-[78px] items-baseline gap-1.5 rounded-md border px-2 py-1",
        palette.container,
      )}
      data-testid={`stock-pill-${tag}`}
    >
      <span className={cn("font-mono text-sm font-bold tabular-nums", palette.value)}>
        {tag === "unknown" ? "—" : qty}
      </span>
      <span
        className={cn(
          "font-mono text-[9px] font-bold uppercase tracking-[0.15em]",
          palette.value,
        )}
      >
        {palette.label}
      </span>
    </div>
  );
}
