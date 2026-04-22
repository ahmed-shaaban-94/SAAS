import { cn } from "@/lib/utils";
import { TONE_CLASSES } from "./reason-tags";

interface LegendChipProps {
  tone: keyof typeof TONE_CLASSES;
  label: string;
  kbd?: string;
}

function LegendChip({ tone, label, kbd }: LegendChipProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider",
        TONE_CLASSES[tone].chip,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", TONE_CLASSES[tone].dot)} />
      {label}
      {kbd && (
        <kbd className="ms-1 inline-flex h-4 min-w-[14px] items-center justify-center rounded border border-current/30 px-1 text-[9px] opacity-80">
          {kbd}
        </kbd>
      )}
    </span>
  );
}

export function LegendBar() {
  return (
    <div
      className="flex flex-wrap items-center gap-2 rounded-xl border border-border bg-surface-raised/40 px-3 py-2"
      data-testid="sync-legend"
    >
      <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-secondary">
        Legend
      </span>
      <LegendChip tone="amber" label="Price / voucher" />
      <LegendChip tone="red" label="Stock / insurer" />
      <LegendChip tone="purple" label="Duplicate" />
      <span className="ms-auto flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-text-secondary">
        <kbd className="inline-flex h-4 min-w-[14px] items-center justify-center rounded border border-border px-1 font-mono text-[9px]">
          ↑↓
        </kbd>
        Navigate
        <kbd className="inline-flex h-4 min-w-[14px] items-center justify-center rounded border border-border px-1 font-mono text-[9px]">
          O
        </kbd>
        Override
        <kbd className="inline-flex h-4 min-w-[14px] items-center justify-center rounded border border-border px-1 font-mono text-[9px]">
          L
        </kbd>
        Loss
        <kbd className="inline-flex h-4 min-w-[14px] items-center justify-center rounded border border-border px-1 font-mono text-[9px]">
          R
        </kbd>
        Void
      </span>
    </div>
  );
}
