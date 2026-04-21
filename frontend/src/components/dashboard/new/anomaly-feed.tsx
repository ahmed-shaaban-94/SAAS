"use client";

import { TrendingUp, TrendingDown, Info } from "lucide-react";
import type { ComponentType, SVGProps } from "react";
import type { AnomalyCard } from "@/types/api";

interface AnomalyFeedProps {
  data?: AnomalyCard[];
  loading?: boolean;
  limit?: number;
}

const KIND_META: Record<AnomalyCard["kind"], { icon: ComponentType<SVGProps<SVGSVGElement>>; cls: string }> = {
  up: { icon: TrendingUp, cls: "bg-growth-green/15 text-growth-green" },
  down: { icon: TrendingDown, cls: "bg-growth-red/15 text-growth-red" },
  info: { icon: Info, cls: "bg-chart-purple/15 text-chart-purple" },
};

export function AnomalyFeed({ data = [], loading, limit = 6 }: AnomalyFeedProps) {
  const items = data.slice(0, limit);

  return (
    <div className="rounded-[14px] bg-card border border-border/40 p-6">
      <header className="flex items-center gap-3 mb-3">
        <h3 className="text-[15px] font-semibold">Anomalies &amp; insights</h3>
        <span className="font-mono text-[11px] text-ink-tertiary">AI · last 24h</span>
      </header>

      {loading ? (
        <div className="h-48 bg-elevated/30 rounded animate-pulse" aria-busy="true" />
      ) : items.length === 0 ? (
        <p className="text-sm text-ink-tertiary py-4">No anomalies detected.</p>
      ) : (
        <ul className="flex flex-col gap-4" aria-label="Active anomalies">
          {items.map((anomaly) => {
            const meta = KIND_META[anomaly.kind];
            const Icon = meta.icon;
            return (
              <li key={anomaly.id} className="flex gap-3">
                <div
                  className={`w-7 h-7 rounded-lg grid place-items-center shrink-0 ${meta.cls}`}
                  aria-hidden
                >
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <h5 className="font-semibold text-[13.5px]">{anomaly.title}</h5>
                  <p className="text-[12.5px] text-ink-secondary mt-0.5 leading-snug">
                    {anomaly.body}
                  </p>
                  <div className="font-mono text-[10.5px] uppercase tracking-[0.18em] text-ink-tertiary mt-1.5">
                    {anomaly.time_ago} · {anomaly.confidence} confidence
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
