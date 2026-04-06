"use client";

import { useState, useEffect } from "react";
import { Calendar } from "lucide-react";
import * as Popover from "@radix-ui/react-popover";
import { DayPicker } from "react-day-picker";
import "react-day-picker/style.css";
import { format } from "date-fns";
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

const calendarClassNames = {
  root: "rdp-datapulse",
  month_caption: "text-sm font-medium text-text-primary mb-2",
  day_button:
    "h-8 w-8 rounded-md text-sm text-text-primary hover:bg-accent/10",
  selected: "bg-accent text-page font-medium",
  today: "font-bold text-accent",
  chevron: "text-text-secondary",
};

function DateButton({
  label,
  date,
  onSelect,
}: {
  label: string;
  date: Date | null;
  onSelect: (d: Date) => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          className={`flex items-center gap-1.5 rounded-md border border-border px-2 py-1 text-xs transition-colors ${
            date
              ? "bg-accent/10 font-medium text-accent"
              : "text-text-secondary hover:bg-divider"
          }`}
        >
          <Calendar className="h-3 w-3" />
          {date ? format(date, "MMM d, yyyy") : label}
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          className="z-50 rounded-lg border border-border bg-card p-3 shadow-xl"
          sideOffset={8}
          align="start"
        >
          <DayPicker
            mode="single"
            selected={date ?? undefined}
            onSelect={(d) => {
              if (d) {
                onSelect(d);
                setOpen(false);
              }
            }}
            classNames={calendarClassNames}
          />
          <Popover.Arrow className="fill-border" />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

export function PeriodPicker({
  label,
  period,
  onChange,
  accentColor = "text-accent",
}: PeriodPickerProps) {
  const fmt = (d: Date) => d.toISOString().split("T")[0];

  const [customStart, setCustomStart] = useState<Date | null>(null);
  const [customEnd, setCustomEnd] = useState<Date | null>(null);

  // Check if current period matches any preset
  const isCustom = !PRESETS.some((preset) => {
    const { start, end } = preset.getDates();
    return period.start_date === fmt(start) && period.end_date === fmt(end);
  });

  // When both custom dates are set, fire onChange
  useEffect(() => {
    if (customStart && customEnd) {
      const start = customStart <= customEnd ? customStart : customEnd;
      const end = customStart <= customEnd ? customEnd : customStart;
      onChange({
        start_date: fmt(start),
        end_date: fmt(end),
        label: "Custom",
      });
    }
  }, [customStart, customEnd]); // eslint-disable-line react-hooks/exhaustive-deps

  const handlePreset = (preset: (typeof PRESETS)[number]) => {
    const { start, end } = preset.getDates();
    setCustomStart(null);
    setCustomEnd(null);
    onChange({
      start_date: fmt(start),
      end_date: fmt(end),
      label: preset.label,
    });
  };

  return (
    <div className="rounded-lg border border-border p-3">
      <div className="mb-2 flex items-center gap-1.5">
        <Calendar className={`h-3.5 w-3.5 ${accentColor}`} />
        <span className="text-xs font-semibold text-text-secondary">
          {label}
        </span>
      </div>

      {/* Preset buttons */}
      <div className="flex flex-wrap gap-1.5">
        {PRESETS.map((preset) => {
          const { start, end } = preset.getDates();
          const isActive =
            period.start_date === fmt(start) && period.end_date === fmt(end);
          return (
            <button
              key={preset.label}
              onClick={() => handlePreset(preset)}
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

      {/* Custom date buttons */}
      <div className="mt-2 flex items-center gap-2">
        <DateButton
          label="Start date"
          date={isCustom ? customStart : null}
          onSelect={setCustomStart}
        />
        <span className="text-xs text-text-secondary">&rarr;</span>
        <DateButton
          label="End date"
          date={isCustom ? customEnd : null}
          onSelect={setCustomEnd}
        />
      </div>

      <p className="mt-2 text-[10px] text-text-secondary">
        {period.start_date} &rarr; {period.end_date}
      </p>
    </div>
  );
}
