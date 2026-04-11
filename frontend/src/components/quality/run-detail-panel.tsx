"use client";

import { useState } from "react";
import { useQualityRunDetail, type QualityCheck } from "@/hooks/use-quality-run-detail";
import { LoadingCard } from "@/components/loading-card";
import { X, AlertTriangle, ShieldX, Filter } from "lucide-react";
import { cn } from "@/lib/utils";

const STAGE_ORDER = ["bronze", "silver", "gold"] as const;

const STAGE_COLORS: Record<string, { bg: string; text: string }> = {
  bronze: { bg: "bg-orange-500/10", text: "text-orange-500" },
  silver: { bg: "bg-blue-500/10", text: "text-blue-500" },
  gold: { bg: "bg-yellow-500/10", text: "text-yellow-500" },
};

type FilterMode = "all" | "failed" | "warned";

function CheckRow({ check }: { check: QualityCheck }) {
  const isFailed = !check.passed && check.severity === "error";
  const isWarned = !check.passed && check.severity === "warn";
  const isPassed = check.passed;

  return (
    <div
      className={cn(
        "rounded-lg border p-3 text-sm",
        isFailed && "border-red-500/20 bg-red-500/5",
        isWarned && "border-yellow-500/20 bg-yellow-500/5",
        isPassed && "border-border bg-card",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            {isFailed && <ShieldX className="h-3.5 w-3.5 text-red-500 shrink-0" />}
            {isWarned && <AlertTriangle className="h-3.5 w-3.5 text-yellow-500 shrink-0" />}
            <span className="font-medium text-text-primary">{check.check_name}</span>
          </div>
          <p className="mt-1 text-xs text-text-secondary">{check.message}</p>
        </div>
        <span
          className={cn(
            "shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase",
            isFailed && "bg-red-500/10 text-red-500",
            isWarned && "bg-yellow-500/10 text-yellow-500",
            isPassed && "bg-green-500/10 text-green-500",
          )}
        >
          {isPassed ? "pass" : check.severity}
        </span>
      </div>
    </div>
  );
}

interface RunDetailPanelProps {
  runId: string;
  onClose: () => void;
}

export function RunDetailPanel({ runId, onClose }: RunDetailPanelProps) {
  const { data, isLoading } = useQualityRunDetail(runId);
  const [filter, setFilter] = useState<FilterMode>("all");
  const [stageFilter, setStageFilter] = useState<string | null>(null);

  if (isLoading || !data) {
    return (
      <div className="rounded-xl border border-accent/30 bg-card p-5">
        <LoadingCard className="h-48" />
      </div>
    );
  }

  const filteredChecks = data.checks.filter((c) => {
    if (stageFilter && c.stage !== stageFilter) return false;
    if (filter === "failed") return !c.passed && c.severity === "error";
    if (filter === "warned") return !c.passed && c.severity === "warn";
    return true;
  });

  // Group by stage
  const grouped = STAGE_ORDER.reduce(
    (acc, stage) => {
      const stageChecks = filteredChecks.filter((c) => c.stage === stage);
      if (stageChecks.length > 0) acc[stage] = stageChecks;
      return acc;
    },
    {} as Record<string, QualityCheck[]>,
  );

  return (
    <div className="rounded-xl border border-accent/30 bg-card p-5 space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text-primary">
          Run Detail — {data.total_checks} checks
        </h3>
        <button onClick={onClose} className="text-text-secondary hover:text-text-primary">
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Summary pills */}
      <div className="flex gap-2 text-xs">
        <span className="rounded-full bg-green-500/10 px-2.5 py-1 text-green-500 font-medium">
          {data.passed} passed
        </span>
        <span className="rounded-full bg-red-500/10 px-2.5 py-1 text-red-500 font-medium">
          {data.failed} failed
        </span>
        <span className="rounded-full bg-yellow-500/10 px-2.5 py-1 text-yellow-500 font-medium">
          {data.warned} warned
        </span>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <div className="flex items-center gap-1 text-xs text-text-secondary">
          <Filter className="h-3 w-3" />
          <span>Show:</span>
        </div>
        {(["all", "failed", "warned"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={cn(
              "rounded-md px-2.5 py-1 text-xs font-medium transition-all",
              filter === f
                ? "bg-accent/20 text-accent"
                : "text-text-secondary hover:text-text-primary",
            )}
          >
            {f === "all" ? "All" : f === "failed" ? "Failed Only" : "Warnings Only"}
          </button>
        ))}

        <div className="ml-2 border-l border-border pl-2 flex gap-1">
          <button
            onClick={() => setStageFilter(null)}
            className={cn(
              "rounded-md px-2 py-1 text-xs font-medium",
              !stageFilter ? "bg-accent/20 text-accent" : "text-text-secondary",
            )}
          >
            All Stages
          </button>
          {STAGE_ORDER.map((s) => (
            <button
              key={s}
              onClick={() => setStageFilter(stageFilter === s ? null : s)}
              className={cn(
                "rounded-md px-2 py-1 text-xs font-medium capitalize",
                stageFilter === s
                  ? `${STAGE_COLORS[s].bg} ${STAGE_COLORS[s].text}`
                  : "text-text-secondary",
              )}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Grouped checks */}
      {Object.entries(grouped).length === 0 ? (
        <p className="text-xs text-text-secondary py-4 text-center">
          No checks match the current filter
        </p>
      ) : (
        <div className="space-y-4">
          {Object.entries(grouped).map(([stage, checks]) => {
            const colors = STAGE_COLORS[stage] ?? STAGE_COLORS.bronze;
            return (
              <div key={stage}>
                <h4 className={cn("text-xs font-semibold uppercase tracking-wider mb-2", colors.text)}>
                  {stage} ({checks.length})
                </h4>
                <div className="space-y-2">
                  {checks.map((check) => (
                    <CheckRow key={`${check.stage}-${check.check_name}`} check={check} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
