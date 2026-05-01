import { cn } from "@shared/lib/utils";

interface Props {
  totalSkus: number;
  totalUnits: number;
  stockValue: number;
  lowCount: number;
  outCount: number;
}

export function InventorySummary({
  totalSkus,
  totalUnits,
  stockValue,
  lowCount,
  outCount,
}: Props) {
  return (
    <div
      className={cn(
        "rounded-2xl px-4 py-3.5",
        "border border-cyan-400/35 bg-gradient-to-b from-cyan-400/10 to-[rgba(22,52,82,0.4)]",
        "shadow-[0_0_0_1px_rgba(0,199,242,0.12),0_0_28px_rgba(0,199,242,0.1)]",
      )}
      data-testid="inventory-summary"
    >
      <div className="mb-2.5 font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-cyan-300">
        ● Stock snapshot
      </div>
      <div
        className={cn(
          "font-serif text-3xl italic leading-none tracking-tight",
          "text-text-primary tabular-nums drop-shadow-[0_0_24px_rgba(0,199,242,0.35)]",
        )}
      >
        {formatEGP(stockValue)}
      </div>
      <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.16em] text-text-secondary">
        On-hand value
      </div>
      <div className="mt-3.5 grid grid-cols-2 gap-2">
        <Stat label="SKUs" value={totalSkus} />
        <Stat label="Units" value={totalUnits} />
        <Stat label="Low" value={lowCount} tone="amber" />
        <Stat label="Out" value={outCount} tone="red" />
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: "amber" | "red";
}) {
  const toneClass =
    tone === "amber" ? "text-amber-300" : tone === "red" ? "text-red-300" : "text-text-primary";
  return (
    <div className="rounded-lg border border-border bg-[rgba(8,24,38,0.5)] px-2.5 py-2">
      <div className={cn("font-mono text-lg font-bold tabular-nums", toneClass)}>{value}</div>
      <div className="mt-0.5 font-mono text-[9px] uppercase tracking-[0.16em] text-text-secondary">
        {label}
      </div>
    </div>
  );
}

function formatEGP(value: number): string {
  return `EGP ${value.toFixed(2)}`;
}
