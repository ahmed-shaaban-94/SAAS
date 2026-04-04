"use client";

import { useFilters } from "@/contexts/filter-context";
import { useFilterOptions } from "@/hooks/use-filter-options";
import { SlicerDropdown } from "./slicer-dropdown";
import { Building2, UserCog, Tag, Layers } from "lucide-react";

export function SlicerPanel() {
  const { filters, updateFilter } = useFilters();
  const { data: options, isLoading } = useFilterOptions();

  if (isLoading || !options) {
    return (
      <div className="mb-4 flex flex-wrap gap-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="shimmer-line h-9 w-36 rounded-lg"
          />
        ))}
      </div>
    );
  }

  const categoryOptions = options.categories.map((c) => ({ key: c, label: c }));
  const brandOptions = options.brands.map((b) => ({ key: b, label: b }));
  const siteOptions = options.sites.map((s) => ({
    key: String(s.key),
    label: s.label,
  }));
  const staffOptions = options.staff.map((s) => ({
    key: String(s.key),
    label: s.label,
  }));

  const activeCount = [
    filters.category,
    filters.brand,
    filters.site_key,
    filters.staff_key,
  ].filter((v) => v !== undefined).length;

  return (
    <div className="mb-4">
      <div className="mb-2 flex items-center gap-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
          Filters
        </span>
        {activeCount > 0 && (
          <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-accent px-1.5 text-[10px] font-bold text-page">
            {activeCount}
          </span>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        <SlicerDropdown
          label="Category"
          icon={Layers}
          options={categoryOptions}
          value={filters.category}
          onChange={(v) => updateFilter("category", v)}
          searchable={categoryOptions.length > 10}
        />
        <SlicerDropdown
          label="Brand"
          icon={Tag}
          options={brandOptions}
          value={filters.brand}
          onChange={(v) => updateFilter("brand", v)}
          searchable={brandOptions.length > 10}
        />
        <SlicerDropdown
          label="Site"
          icon={Building2}
          options={siteOptions}
          value={filters.site_key !== undefined ? String(filters.site_key) : undefined}
          onChange={(v) =>
            updateFilter("site_key", v !== undefined ? Number(v) : undefined)
          }
        />
        <SlicerDropdown
          label="Staff"
          icon={UserCog}
          options={staffOptions}
          value={filters.staff_key !== undefined ? String(filters.staff_key) : undefined}
          onChange={(v) =>
            updateFilter("staff_key", v !== undefined ? Number(v) : undefined)
          }
          searchable={staffOptions.length > 10}
        />
      </div>
    </div>
  );
}
