"use client";

import { useState } from "react";
import {
  Hash,
  Calendar,
  ToggleLeft,
  Type,
  TrendingUp,
  ChevronDown,
  ChevronRight,
  Plus,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ExploreDimension, ExploreMetric, ExploreModel } from "@/types/api";

interface FieldPickerProps {
  model: ExploreModel;
  selectedDimensions: string[];
  selectedMetrics: string[];
  onToggleDimension: (name: string) => void;
  onToggleMetric: (name: string) => void;
}

const dimTypeIcon: Record<string, React.ComponentType<{ className?: string }>> = {
  string: Type,
  number: Hash,
  date: Calendar,
  boolean: ToggleLeft,
};

export function FieldPicker({
  model,
  selectedDimensions,
  selectedMetrics,
  onToggleDimension,
  onToggleMetric,
}: FieldPickerProps) {
  const [dimsOpen, setDimsOpen] = useState(true);
  const [metricsOpen, setMetricsOpen] = useState(true);

  return (
    <div className="space-y-1">
      {/* Dimensions section */}
      <button
        onClick={() => setDimsOpen(!dimsOpen)}
        className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-xs font-semibold uppercase tracking-wider text-text-secondary hover:text-text-primary"
      >
        {dimsOpen ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
        Group By ({model.dimensions.length})
      </button>

      {dimsOpen && (
        <div className="space-y-0.5 pl-2">
          {model.dimensions.map((dim) => {
            const isSelected = selectedDimensions.includes(dim.name);
            const Icon = dimTypeIcon[dim.dimension_type] || Type;
            return (
              <button
                key={dim.name}
                onClick={() => onToggleDimension(dim.name)}
                title={dim.description || dim.label}
                className={cn(
                  "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors",
                  isSelected
                    ? "bg-blue-500/10 text-blue-400"
                    : "text-text-secondary hover:bg-divider hover:text-text-primary",
                )}
              >
                <Icon className="h-3.5 w-3.5 flex-shrink-0" />
                <span className="truncate">{dim.label}</span>
                {isSelected ? (
                  <X className="ml-auto h-3 w-3 flex-shrink-0" />
                ) : (
                  <Plus className="ml-auto h-3 w-3 flex-shrink-0 opacity-0 group-hover:opacity-100" />
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Metrics section */}
      <button
        onClick={() => setMetricsOpen(!metricsOpen)}
        className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-xs font-semibold uppercase tracking-wider text-text-secondary hover:text-text-primary"
      >
        {metricsOpen ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
        Values ({model.metrics.length})
      </button>

      {metricsOpen && (
        <div className="space-y-0.5 pl-2">
          {model.metrics.map((metric) => {
            const isSelected = selectedMetrics.includes(metric.name);
            return (
              <button
                key={metric.name}
                onClick={() => onToggleMetric(metric.name)}
                title={`${metric.metric_type}(${metric.column})`}
                className={cn(
                  "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors",
                  isSelected
                    ? "bg-orange-500/10 text-orange-400"
                    : "text-text-secondary hover:bg-divider hover:text-text-primary",
                )}
              >
                <TrendingUp className="h-3.5 w-3.5 flex-shrink-0" />
                <span className="truncate">{metric.label}</span>
                {isSelected ? (
                  <X className="ml-auto h-3 w-3 flex-shrink-0" />
                ) : (
                  <Plus className="ml-auto h-3 w-3 flex-shrink-0 opacity-0 group-hover:opacity-100" />
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
