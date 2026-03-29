"use client";

import { useMemo, useState } from "react";
import { useFilters } from "@/contexts/filter-context";
import { useToast } from "@/components/ui/toast";
import { useDateRange } from "@/hooks/use-date-range";
import { getDatePresets, formatDateParam } from "@/lib/date-utils";
import { cn } from "@/lib/utils";
import { X, SlidersHorizontal, ChevronDown } from "lucide-react";
import { SlicerPanel } from "./slicer-panel";
import { ActiveFilterChips } from "./active-filter-chips";

export function FilterBar() {
  const { filters, setFilters, updateFilter, clearFilters } = useFilters();
  const { info } = useToast();
  const { data: dateRange } = useDateRange();

  const presets = useMemo(() => {
    if (dateRange?.max_date) {
      return getDatePresets(new Date(dateRange.max_date + "T00:00:00"));
    }
    return getDatePresets();
  }, [dateRange?.max_date]);

  const [expanded, setExpanded] = useState(false);

  const activeFilterCount = Object.values(filters).filter((v) => v !== undefined).length;
  const hasFilters = activeFilterCount > 0;

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
    <div className="mb-6 space-y-3">
      {/* Row 1: Date presets + toggle + clear */}
      <div className="flex flex-wrap items-center gap-2">
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

        {/* More Filters toggle */}
        <button
          onClick={() => setExpanded((prev) => !prev)}
          aria-expanded={expanded}
          aria-label="Toggle advanced filters"
          className={cn(
            "ml-auto flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
            expanded
              ? "bg-accent/10 text-accent"
              : "bg-divider text-text-secondary hover:bg-border hover:text-text-primary",
          )}
        >
          <SlidersHorizontal className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Filters</span>
          <ChevronDown
            className={cn(
              "h-3.5 w-3.5 transition-transform",
              expanded && "rotate-180",
            )}
          />
        </button>

        {/* Clear button with badge */}
        {hasFilters && (
          <button
            onClick={() => {
              clearFilters();
              info("All filters cleared");
            }}
            aria-label={`Clear all ${activeFilterCount} filters`}
            className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium text-text-secondary transition-colors hover:bg-growth-red/10 hover:text-growth-red"
          >
            <X className="h-3.5 w-3.5" />
            Clear
            <span className="ml-0.5 inline-flex h-5 w-5 items-center justify-center rounded-full bg-growth-red/15 text-xs font-semibold text-growth-red">
              {activeFilterCount}
            </span>
          </button>
        )}
      </div>

      {/* Active filter chips (always visible) */}
      {!expanded && <ActiveFilterChips />}

      {/* Row 2: Collapsible slicer panel + custom date range */}
      {expanded && (
        <div className="rounded-lg border border-divider bg-card/50 p-3">
          {/* Slicer dropdowns (Power BI style) */}
          <SlicerPanel />

          {/* Custom date range */}
          <div className="flex flex-wrap items-end gap-3 border-t border-divider pt-3">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                From
              </label>
              <input
                type="date"
                value={filters.start_date ?? ""}
                onChange={(e) =>
                  updateFilter("start_date", e.target.value || undefined)
                }
                className="h-9 rounded-lg border border-border bg-page px-3 text-sm text-text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                To
              </label>
              <input
                type="date"
                value={filters.end_date ?? ""}
                onChange={(e) =>
                  updateFilter("end_date", e.target.value || undefined)
                }
                className="h-9 rounded-lg border border-border bg-page px-3 text-sm text-text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
