"use client";

import Link from "next/link";
import {
  AlertTriangle,
  PackageMinus,
  Activity,
  Database,
  ArrowUpRight,
} from "lucide-react";
import type {
  AttentionAlert,
  AttentionSeverity,
  AttentionType,
} from "@/lib/attention-queue";

const TYPE_ICON: Record<AttentionType, typeof AlertTriangle> = {
  expiry: AlertTriangle,
  stock: PackageMinus,
  anomaly: Activity,
  pipeline: Database,
};

const DOT_COLOR: Record<AttentionSeverity, string> = {
  red: "bg-red-500",
  amber: "bg-amber-400",
  blue: "bg-sky-400",
};

const DOT_LABEL: Record<AttentionSeverity, string> = {
  red: "critical",
  amber: "warning",
  blue: "info",
};

function formatEgp(value: number): string {
  if (value >= 1_000_000) return `EGP ${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `EGP ${(value / 1_000).toFixed(0)}K`;
  return `EGP ${value.toFixed(0)}`;
}

export function AttentionRow({ alert }: { alert: AttentionAlert }) {
  const Icon = TYPE_ICON[alert.type];
  const impactText =
    alert.impactEgp !== undefined
      ? formatEgp(alert.impactEgp)
      : alert.impactCount !== undefined
      ? `${alert.impactCount} SKUs`
      : "";

  return (
    <li
      data-alert-id={alert.id}
      className="flex items-center gap-3 px-4 py-2 hover:bg-elevated/40 rounded-md"
    >
      <span
        className={`w-2 h-2 rounded-full shrink-0 ${DOT_COLOR[alert.severity]}`}
        role="img"
        aria-label={DOT_LABEL[alert.severity]}
      />
      <Icon className="w-3.5 h-3.5 text-ink-secondary shrink-0" aria-hidden />
      <span className="flex-1 text-sm text-ink-primary truncate">{alert.title}</span>
      {impactText && (
        <span className="text-xs text-ink-secondary font-mono shrink-0">{impactText}</span>
      )}
      {alert.where && (
        <span className="text-xs text-ink-secondary shrink-0">{alert.where}</span>
      )}
      {alert.drillHref && (
        <Link
          href={alert.drillHref}
          className="inline-flex items-center gap-1 text-xs text-accent-strong hover:underline shrink-0
                     focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded"
          aria-label={`Drill into ${alert.title}`}
        >
          <ArrowUpRight className="w-3 h-3" aria-hidden />
          Drill
        </Link>
      )}
    </li>
  );
}
