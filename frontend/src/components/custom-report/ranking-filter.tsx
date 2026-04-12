"use client";

import { cn } from "@/lib/utils";
import { ArrowDownAZ, ArrowUpAZ, Hash } from "lucide-react";
import { friendlyMetricLabel } from "./report-config";

export const RANK_PRESETS = [
  { label: "All", value: 0 },
  { label: "Top 10", value: 10 },
  { label: "Top 25", value: 25 },
  { label: "Top 50", value: 50 },
  { label: "Top 100", value: 100 },
] as const;

interface RankingFilterProps {
  selectedMetrics: string[];
  rankLimit: number;
  sortField: string | null;
  sortDirection: "asc" | "desc";
  onRankLimitChange: (limit: number) => void;
  onSortFieldChange: (field: string | null) => void;
  onSortDirectionChange: (dir: "asc" | "desc") => void;
}

export function RankingFilter({
  selectedMetrics,
  rankLimit,
  sortField,
  sortDirection,
  onRankLimitChange,
  onSortFieldChange,
  onSortDirectionChange,
}: RankingFilterProps) {
  return (
    <div className="space-y-3">
      {/* Limit selector */}
      <div>
        <h4 className="mb-2 text-sm font-semibold text-text-primary flex items-center gap-1.5">
          <Hash className="h-3.5 w-3.5 text-accent" />
          Ranking{" "}
          <span className="font-normal text-text-secondary text-xs">
            (limit results)
          </span>
        </h4>
        <div className="flex flex-wrap gap-2">
          {RANK_PRESETS.map((preset) => (
            <button
              key={preset.value}
              onClick={() => onRankLimitChange(preset.value)}
              className={cn(
                "rounded-full px-3 py-1.5 text-xs font-medium transition-all",
                rankLimit === preset.value
                  ? "bg-accent text-white"
                  : "bg-card border border-border text-text-secondary hover:border-border-hover hover:text-text-primary",
              )}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* Sort field + direction (only show when metrics are selected) */}
      {selectedMetrics.length > 0 && (
        <div>
          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-text-secondary/60">
            Sort by
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {selectedMetrics.map((metric) => (
              <button
                key={metric}
                onClick={() =>
                  onSortFieldChange(sortField === metric ? null : metric)
                }
                className={cn(
                  "rounded-full px-3 py-1.5 text-xs font-medium transition-all",
                  sortField === metric
                    ? "bg-chart-blue text-white"
                    : "bg-card border border-border text-text-secondary hover:border-border-hover hover:text-text-primary",
                )}
              >
                {friendlyMetricLabel(metric)}
              </button>
            ))}

            {/* Direction toggle */}
            {sortField && (
              <button
                onClick={() =>
                  onSortDirectionChange(sortDirection === "desc" ? "asc" : "desc")
                }
                className="flex items-center gap-1 rounded-full border border-border px-2.5 py-1.5 text-xs font-medium text-text-secondary hover:border-border-hover hover:text-text-primary transition-colors"
                title={sortDirection === "desc" ? "Descending (highest first)" : "Ascending (lowest first)"}
              >
                {sortDirection === "desc" ? (
                  <ArrowDownAZ className="h-3.5 w-3.5" />
                ) : (
                  <ArrowUpAZ className="h-3.5 w-3.5" />
                )}
                {sortDirection === "desc" ? "High to Low" : "Low to High"}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
