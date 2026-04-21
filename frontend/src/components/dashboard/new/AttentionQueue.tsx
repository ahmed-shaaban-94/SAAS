"use client";

import { useMemo, useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { AttentionRow } from "./AttentionRow";
import { AttentionChips, type ChipFilter } from "./AttentionChips";
import {
  mergeAttentionAlerts,
  type AttentionAlert,
  type MergeInputs,
} from "@/lib/attention-queue";
import { trackEvent } from "@/lib/analytics";

interface Props {
  inputs: MergeInputs;
  loading: boolean;
  syncedLabel?: string;
  maxVisible?: number;
}

export function AttentionQueue({ inputs, loading, syncedLabel, maxVisible = 8 }: Props) {
  const [active, setActive] = useState<ChipFilter>("all");

  const alerts = useMemo(() => mergeAttentionAlerts(inputs), [inputs]);

  const counts = useMemo(() => {
    return {
      all: alerts.length,
      critical: alerts.filter((a) => a.severity === "red").length,
      expiry: alerts.filter((a) => a.type === "expiry").length,
      stock: alerts.filter((a) => a.type === "stock").length,
      anomaly: alerts.filter((a) => a.type === "anomaly").length,
      pipeline: alerts.filter((a) => a.type === "pipeline").length,
    };
  }, [alerts]);

  const filtered = useMemo(() => {
    if (active === "all") return alerts;
    if (active === "critical") return alerts.filter((a) => a.severity === "red");
    return alerts.filter((a) => a.type === active);
  }, [alerts, active]);

  const chips = (
    [
      { key: "all" as const, label: "All", count: counts.all },
      { key: "critical" as const, label: "Critical", count: counts.critical },
      { key: "expiry" as const, label: "Expiry", count: counts.expiry },
      { key: "stock" as const, label: "Stock", count: counts.stock },
      { key: "anomaly" as const, label: "Anomaly", count: counts.anomaly },
      { key: "pipeline" as const, label: "Pipeline", count: counts.pipeline },
    ] satisfies Array<{ key: ChipFilter; label: string; count: number }>
  ).filter((c) => c.key === "all" || c.count > 0);

  if (loading) {
    return (
      <section
        role="region"
        aria-label="Attention queue"
        className="rounded-[14px] bg-card border border-border/40 p-5 h-[364px] animate-pulse"
        aria-busy="true"
      />
    );
  }

  if (alerts.length === 0) {
    return (
      <section
        role="region"
        aria-label="Attention queue"
        className="rounded-[14px] bg-card border border-border/40 p-5 h-[364px]
                   flex flex-col items-center justify-center text-center gap-2"
      >
        <CheckCircle2 className="w-7 h-7 text-accent-strong" aria-hidden />
        <h2 className="text-base font-semibold text-ink-primary">All clear</h2>
        <p className="text-sm text-ink-secondary">
          No attention needed right now{syncedLabel ? ` · ${syncedLabel}` : ""}.
        </p>
      </section>
    );
  }

  return (
    <section
      role="region"
      aria-label="Attention queue"
      className="rounded-[14px] bg-card border border-border/40 p-4"
    >
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-ink-primary">
          Needs your attention
        </h2>
        {syncedLabel && (
          <span className="text-[11px] text-ink-secondary">{syncedLabel}</span>
        )}
      </div>
      <AttentionChips chips={chips} active={active} onChange={setActive} />
      <ul
        className="mt-3 overflow-y-auto"
        style={{ maxHeight: `${maxVisible * 40}px` }}
        onClickCapture={(e) => {
          const anchor = (e.target as HTMLElement).closest("a[href]");
          if (!anchor) return;
          // Read alert-id from the enclosing <li data-alert-id>. Matching by
          // href would be wrong because many alerts share the same drillHref
          // (e.g. every stock row links to /inventory?filter=below-reorder).
          const row = (e.target as HTMLElement).closest("[data-alert-id]");
          const alertId = row?.getAttribute("data-alert-id");
          if (!alertId) return;
          const alert = filtered.find((a) => a.id === alertId);
          if (alert) {
            trackEvent("attention_queue_drill", {
              type: alert.type,
              severity: alert.severity,
              alert_id: alert.id,
            });
          }
        }}
      >
        {filtered.map((a: AttentionAlert) => (
          <AttentionRow key={a.id} alert={a} />
        ))}
      </ul>
    </section>
  );
}
