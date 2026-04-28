"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ChevronDown, Database, Activity, FileText } from "lucide-react";
import type { ReactNode } from "react";

interface PipelineSummary {
  status: "success" | "failed" | "running" | string;
  lastRunAt?: string;
  checksTotal?: number;
  checksFailed?: number;
}

interface Props {
  pipeline: PipelineSummary | null;
  channelsSlot: ReactNode;
}

function relativeTime(iso?: string): string {
  if (!iso) return "just now";
  const d = new Date(iso).getTime();
  if (Number.isNaN(d)) return "just now";
  const diff = Math.max(0, Date.now() - d);
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function DashboardFooterBar({ pipeline, channelsSlot }: Props) {
  const [channelsOpen, setChannelsOpen] = useState(false);
  const channelsRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!channelsOpen) return;
    const onMouseDown = (e: MouseEvent) => {
      if (!channelsRef.current) return;
      if (!channelsRef.current.contains(e.target as Node)) setChannelsOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setChannelsOpen(false);
    };
    document.addEventListener("mousedown", onMouseDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onMouseDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [channelsOpen]);

  const pipeColor =
    pipeline?.status === "success"
      ? "bg-accent"
      : pipeline?.status === "failed"
      ? "bg-red-500"
      : "bg-amber-400";

  return (
    <footer className="flex flex-wrap items-center gap-3 py-3 text-xs text-ink-secondary">
      <span className="inline-flex items-center gap-2">
        <span className={`w-1.5 h-1.5 rounded-full ${pipeColor}`} aria-hidden />
        <Database className="w-3 h-3" aria-hidden />
        Pipeline {pipeline?.status ?? "unknown"} · last run {relativeTime(pipeline?.lastRunAt)}
        {typeof pipeline?.checksTotal === "number" && typeof pipeline?.checksFailed === "number" && (
          <span className="font-mono ml-1">
            {pipeline.checksTotal - pipeline.checksFailed}/{pipeline.checksTotal} checks
          </span>
        )}
      </span>

      <div className="relative" ref={channelsRef}>
        <button
          type="button"
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-border/40
                     hover:bg-elevated/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
          aria-expanded={channelsOpen}
          aria-controls="channels-popover"
          onClick={() => setChannelsOpen((v) => !v)}
        >
          Channels <ChevronDown className="w-3 h-3" aria-hidden />
        </button>
        {channelsOpen && (
          <div
            id="channels-popover"
            role="dialog"
            aria-label="Channels"
            className="absolute bottom-full mb-2 w-[360px] max-w-[90vw] rounded-xl border border-border/40
                       bg-card shadow-xl p-3 z-10"
          >
            {channelsSlot}
          </div>
        )}
      </div>

      <Link
        href="/alerts"
        className="inline-flex items-center gap-1.5 hover:text-ink-primary
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded"
      >
        <Activity className="w-3 h-3" aria-hidden />
        All anomalies →
      </Link>
      <Link
        href="/reports"
        className="inline-flex items-center gap-1.5 hover:text-ink-primary
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded"
      >
        <FileText className="w-3 h-3" aria-hidden />
        All reports →
      </Link>
    </footer>
  );
}
