"use client";

import { Fragment } from "react";
import type { PipelineHealth as PipelineHealthData } from "@/types/api";

interface PipelineHealthProps {
  data?: PipelineHealthData;
  loading?: boolean;
}

const DOT_CLS: Record<string, string> = {
  ok: "bg-growth-green",
  running: "bg-chart-amber animate-pulse",
  pending: "bg-ink-tertiary",
  failed: "bg-growth-red",
};

const BORDER_CLS: Record<string, string> = {
  ok: "border-border/40 bg-elevated/40",
  running: "border-chart-amber/40 bg-chart-amber/[0.06]",
  pending: "border-border/40 bg-elevated/40",
  failed: "border-growth-red/40 bg-growth-red/[0.06]",
};

function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return "—";
  const minutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  if (minutes <= 0) return `${secs}s`;
  return `${minutes}m ${String(secs).padStart(2, "0")}s`;
}

function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function barHeight(seconds: number | null): number {
  if (seconds == null) return 10;
  // Max-scale to 600s (10 min). Bigger = worse in bar-height intuition,
  // so we invert: fast run = tall green bar.
  const pct = Math.max(10, 100 - Math.min(100, (seconds / 600) * 100));
  return pct;
}

export function PipelineHealthCard({ data, loading }: PipelineHealthProps) {
  if (loading || !data) {
    return (
      <div className="rounded-[14px] bg-card border border-border/40 p-6">
        <header className="flex items-center gap-3 mb-3">
          <h3 className="text-[15px] font-semibold">Pipeline health</h3>
          <span className="font-mono text-[11px] text-ink-tertiary">medallion · last run</span>
        </header>
        <div className="h-48 bg-elevated/30 rounded animate-pulse" aria-busy="true" />
      </div>
    );
  }

  const { nodes, last_run, next_run_at, gates, tests, history_7d } = data;

  return (
    <div className="rounded-[14px] bg-card border border-border/40 p-6">
      <header className="flex items-center gap-3 mb-3">
        <h3 className="text-[15px] font-semibold">Pipeline health</h3>
        <span className="font-mono text-[11px] text-ink-tertiary">medallion · last run</span>
      </header>

      <div className="flex items-stretch gap-2">
        {nodes.map((node, i) => (
          <Fragment key={node.label}>
            <div
              className={[
                "flex-1 rounded-xl border px-3 py-2.5 relative",
                BORDER_CLS[node.status] ?? BORDER_CLS.ok,
              ].join(" ")}
            >
              <div className="text-[10.5px] uppercase tracking-[0.18em] text-ink-tertiary">
                {node.label}
              </div>
              <div className="text-[13px] font-semibold mt-0.5">{node.value}</div>
              <span
                className={`absolute top-2.5 right-2.5 w-2 h-2 rounded-full ${
                  DOT_CLS[node.status] ?? DOT_CLS.pending
                }`}
                aria-label={`Status: ${node.status}`}
              />
            </div>
            {i < nodes.length - 1 && (
              <div className="self-center text-ink-tertiary" aria-hidden>
                →
              </div>
            )}
          </Fragment>
        ))}
      </div>

      <div className="mt-4 flex flex-col gap-3 text-[12.5px]">
        <Row
          label="Last full run"
          value={
            last_run
              ? `${formatTime(last_run.at)} · ${formatDuration(last_run.duration_seconds)}`
              : "—"
          }
        />
        <Row
          label="Quality gates passed"
          value={`${gates.passed} / ${gates.total}`}
          tone={gates.passed === gates.total ? "green" : "amber"}
        />
        <Row
          label="dbt tests"
          value={`${tests.passed} / ${tests.total}`}
          tone={tests.passed === tests.total ? "green" : "amber"}
        />
        <Row label="Next scheduled run" value={formatTime(next_run_at)} />
      </div>

      <div className="mt-4">
        <div className="text-[10.5px] tracking-[0.18em] uppercase text-ink-tertiary mb-2.5">
          Run history · 7d
        </div>
        <div className="flex items-end gap-1 h-12" aria-label="Run history last 7 days">
          {history_7d.map((point) => {
            const warn = point.status === "warning" || point.status === "fail";
            const height = barHeight(point.duration_seconds);
            return (
              <div
                key={point.date}
                className="flex-1 rounded-[3px]"
                style={{
                  height: `${height}%`,
                  background: warn
                    ? "linear-gradient(180deg, var(--chart-amber), rgba(255,171,61,0.3))"
                    : "linear-gradient(180deg, var(--growth-green), rgba(29,212,139,0.3))",
                }}
                title={`${point.date} · ${point.status}${point.duration_seconds != null ? ` · ${formatDuration(point.duration_seconds)}` : ""}`}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}

function Row({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "green" | "amber";
}) {
  const toneCls =
    tone === "green"
      ? "text-growth-green"
      : tone === "amber"
        ? "text-chart-amber"
        : "text-ink-primary";
  return (
    <div className="flex justify-between">
      <span className="text-ink-secondary">{label}</span>
      <span className={`tabular-nums font-semibold ${toneCls}`}>{value}</span>
    </div>
  );
}
