"use client";

import { useFilters } from "@/contexts/filter-context";
import { getDatePresets, formatDateParam } from "@/lib/date-utils";
import { cn } from "@/lib/utils";
import { X } from "lucide-react";

export function FilterBar() {
  const { filters, setFilters, clearFilters } = useFilters();
  const presets = getDatePresets();

  const hasFilters = Object.keys(filters).length > 0;

  const handlePreset = (preset: { startDate: Date; endDate: Date }) => {
    setFilters({
      ...filters,
      start_date: formatDateParam(preset.startDate),
      end_date: formatDateParam(preset.endDate),
    });
  };

  const isActivePreset = (preset: { startDate: Date; endDate: Date }) => {
    return (
      filters.start_date === formatDateParam(preset.startDate) &&
      filters.end_date === formatDateParam(preset.endDate)
    );
  };

  return (
    <div className="mb-6 flex flex-wrap items-center gap-2">
      {presets.map((preset) => (
        <button
          key={preset.label}
          onClick={() => handlePreset(preset)}
          className={cn(
            "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
            isActivePreset(preset)
              ? "bg-accent text-page"
              : "bg-divider text-text-secondary hover:bg-border hover:text-text-primary",
          )}
        >
          {preset.label}
        </button>
      ))}
      {hasFilters && (
        <button
          onClick={clearFilters}
          className="flex items-center gap-1 rounded-md px-3 py-1.5 text-sm font-medium text-text-secondary transition-colors hover:bg-growth-red/10 hover:text-growth-red"
        >
          <X className="h-3.5 w-3.5" />
          Clear
        </button>
      )}
    </div>
  );
}
