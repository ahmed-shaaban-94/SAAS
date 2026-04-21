"use client";

import type { AttentionType } from "@/lib/attention-queue";

export type ChipFilter = "all" | "critical" | AttentionType;

interface Chip {
  key: ChipFilter;
  label: string;
  count: number;
}

interface Props {
  chips: Chip[];
  active: ChipFilter;
  onChange: (next: ChipFilter) => void;
}

export function AttentionChips({ chips, active, onChange }: Props) {
  return (
    <div
      role="tablist"
      aria-label="Attention filter"
      className="flex gap-2 flex-wrap overflow-x-auto md:flex-nowrap"
    >
      {chips.map((c) => (
        <button
          key={c.key}
          role="tab"
          aria-selected={active === c.key}
          onClick={() => onChange(c.key)}
          className={[
            "px-3 py-1.5 rounded-full text-xs inline-flex items-center gap-1.5",
            "border transition focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60",
            active === c.key
              ? "bg-elevated text-ink-primary border-accent/50"
              : "bg-card/80 text-ink-secondary border-border/40 hover:text-ink-primary",
          ].join(" ")}
        >
          <span>{c.label}</span>
          <span className="text-[10px] text-ink-secondary font-mono">{c.count}</span>
        </button>
      ))}
    </div>
  );
}
