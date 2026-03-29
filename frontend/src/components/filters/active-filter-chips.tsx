"use client";

import { useFilters } from "@/contexts/filter-context";
import { X } from "lucide-react";

export function ActiveFilterChips() {
  const { filters, updateFilter } = useFilters();

  const chips: { key: string; label: string; onRemove: () => void }[] = [];

  if (filters.start_date && filters.end_date) {
    chips.push({
      key: "date",
      label: `${filters.start_date} — ${filters.end_date}`,
      onRemove: () => {
        updateFilter({ start_date: undefined, end_date: undefined });
      },
    });
  }
  if (filters.category) {
    chips.push({
      key: "category",
      label: `Category: ${filters.category}`,
      onRemove: () => updateFilter("category", undefined),
    });
  }
  if (filters.brand) {
    chips.push({
      key: "brand",
      label: `Brand: ${filters.brand}`,
      onRemove: () => updateFilter("brand", undefined),
    });
  }
  if (filters.site_key !== undefined) {
    chips.push({
      key: "site",
      label: `Site ID: ${filters.site_key}`,
      onRemove: () => updateFilter("site_key", undefined),
    });
  }
  if (filters.staff_key !== undefined) {
    chips.push({
      key: "staff",
      label: `Staff ID: ${filters.staff_key}`,
      onRemove: () => updateFilter("staff_key", undefined),
    });
  }

  if (chips.length === 0) return null;

  return (
    <div className="mb-3 flex flex-wrap gap-1.5">
      {chips.map((chip) => (
        <span
          key={chip.key}
          className="inline-flex items-center gap-1 rounded-full border border-accent/30 bg-accent/5 px-2.5 py-1 text-xs font-medium text-accent"
        >
          {chip.label}
          <button
            type="button"
            onClick={chip.onRemove}
            className="ml-0.5 rounded-full p-0.5 transition-colors hover:bg-accent/20"
          >
            <X className="h-3 w-3" />
          </button>
        </span>
      ))}
    </div>
  );
}
