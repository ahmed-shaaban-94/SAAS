"use client";

import { useState } from "react";
import { Download, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PeriodId } from "./types";

const PERIODS: PeriodId[] = ["Day", "Week", "Month", "Quarter", "YTD"];

export function PageActions({
  defaultPeriod = "Month",
  onPeriodChange,
}: {
  defaultPeriod?: PeriodId;
  onPeriodChange?: (p: PeriodId) => void;
}) {
  const [period, setPeriod] = useState<PeriodId>(defaultPeriod);

  const handleSelect = (p: PeriodId) => {
    setPeriod(p);
    onPeriodChange?.(p);
  };

  return (
    <div className="ml-auto flex items-center gap-3">
      <div
        role="tablist"
        aria-label="Period"
        className="inline-flex rounded-full border border-border/40 bg-card/80 p-1"
      >
        {PERIODS.map((p) => {
          const active = period === p;
          return (
            <button
              key={p}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => handleSelect(p)}
              className={cn(
                "rounded-full px-3.5 py-1.5 text-[13px] transition",
                active
                  ? "bg-elevated text-text-primary"
                  : "text-text-secondary hover:text-text-primary",
              )}
              style={
                active
                  ? { boxShadow: "inset 0 0 0 1px rgba(0,199,242,0.3)" }
                  : undefined
              }
            >
              {p}
            </button>
          );
        })}
      </div>
      <button
        type="button"
        className="inline-flex items-center gap-2 rounded-lg border border-border/60 px-3.5 py-2 text-[13px] hover:bg-elevated/60"
      >
        <Download className="h-3.5 w-3.5" aria-hidden />
        Export
      </button>
      <button
        type="button"
        className="inline-flex items-center gap-2 rounded-lg bg-accent px-3.5 py-2 text-[13px] font-semibold text-page hover:bg-accent-strong"
      >
        <Plus className="h-3.5 w-3.5" aria-hidden />
        New report
      </button>
    </div>
  );
}
