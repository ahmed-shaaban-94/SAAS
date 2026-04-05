"use client";

import { Calendar } from "lucide-react";
import type { ComparisonPeriod } from "@/hooks/use-comparison";

interface PeriodPickerProps {
  label: string;
  period: ComparisonPeriod;
  onChange: (period: ComparisonPeriod) => void;
  accentColor?: string;
}

const PRESETS = [
  {
    label: "This Month",
    getDates: () => {
      const n = new Date();
      return { start: new Date(n.getFullYear(), n.getMonth(), 1), end: n };
    },
  },
  {
    label: "Last Month",
    getDates: () => {
      const n = new Date();
      return {
        start: new Date(n.getFullYear(), n.getMonth() - 1, 1),
        end: new Date(n.getFullYear(), n.getMonth(), 0),
      };
    },
  },
  {
    label: "This Quarter",
    getDates: () => {
      const n = new Date();
      const q = Math.floor(n.getMonth() / 3) * 3;
      return { start: new Date(n.getFullYear(), q, 1), end: n };
    },
  },
  {
    label: "Last Quarter",
    getDates: () => {
      const n = new Date();
      const q = Math.floor(n.getMonth() / 3) * 3;
      return {
        start: new Date(n.getFullYear(), q - 3, 1),
        end: new Date(n.getFullYear(), q, 0),
      };
    },
  },
  {
    label: "YTD",
    getDates: () => {
      const n = new Date();
      return { start: new Date(n.getFullYear(), 0, 1), end: n };
    },
  },
  {
    label: "Last Year",
    getDates: () => {
      const n = new Date();
      return {
        start: new Date(n.getFullYear() - 1, 0, 1),
        end: new Date(n.getFullYear() - 1, 11, 31),
      };
    },
  },
];

export function PeriodPicker({
  label,
  period,
  onChange,
  accentColor = "text-accent",
}: PeriodPickerProps) {
  const fmt = (d: Date) => d.toISOString().split("T")[0];

  return (
    <div className="rounded-lg border border-border p-3">
      <div className="mb-2 flex items-center gap-1.5">
        <Calendar className={`h-3.5 w-3.5 ${accentColor}`} />
        <span className="text-xs font-semibold text-text-secondary">{label}</span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {PRESETS.map((preset) => {
          const { start, end } = preset.getDates();
          const isActive =
            period.start_date === fmt(start) && period.end_date === fmt(end);
          return (
            <button
              key={preset.label}
              onClick={() =>
                onChange({
                  start_date: fmt(start),
                  end_date: fmt(end),
                  label: preset.label,
                })
              }
              className={`rounded-md px-2 py-1 text-xs transition-colors ${
                isActive
                  ? "bg-accent/10 font-medium text-accent"
                  : "text-text-secondary hover:bg-divider"
              }`}
            >
              {preset.label}
            </button>
          );
        })}
      </div>
      <p className="mt-2 text-[10px] text-text-secondary">
        {period.start_date} &rarr; {period.end_date}
      </p>
    </div>
  );
}
