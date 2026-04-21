"use client";

/**
 * /briefing — Executive Briefing on the v2 shell.
 *
 * Ops Surfaces batch (Apr 2026): migrated from `(app)/briefing/page.tsx`
 * and replaced the inline `BriefingKPI` component with the canonical
 * lean `KpiCard` from the design-handoff kit. Uses 5 tiles (one extra
 * vs the standard 4) because executive briefings traditionally surface
 * basket size alongside the 4 standard headline metrics.
 *
 * AI narrative + Action Items sections unchanged. Auto-refresh still
 * fires every 10 minutes via SWR `refreshInterval`.
 */

import { useEffect, useState } from "react";
import useSWR from "swr";
import {
  RefreshCw,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  Sparkles,
  Wallet,
  Calendar,
  Users,
  ShoppingBag,
  Percent,
} from "lucide-react";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { KpiCard, type KpiColor, type KpiDir } from "@/components/dashboard/new";
import { LoadingCard } from "@/components/loading-card";
import { fetchAPI } from "@/lib/api-client";
import type { KPISummary, AISummary, TopMovers } from "@/types/api";

const REFRESH_INTERVAL_MS = 10 * 60 * 1000;

function fmt(n: number, decimals = 0): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toFixed(decimals);
}

function fmtPct(n: number | null): string {
  if (n === null || n === undefined) return "—";
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toFixed(1)}%`;
}

function ActionItem({
  index,
  label,
  delta,
  positive,
}: {
  index: number;
  label: string;
  delta: string;
  positive: boolean;
}) {
  const Icon = positive ? ArrowUpRight : ArrowDownRight;
  const color = positive ? "text-emerald-400" : "text-rose-400";
  const bg = positive ? "bg-emerald-500/10" : "bg-rose-500/10";

  return (
    <div className="flex items-start gap-3 rounded-lg border border-border bg-card/50 px-4 py-3">
      <div
        className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold ${bg} ${color}`}
      >
        {index}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-text-primary">{label}</p>
      </div>
      <div className={`flex items-center gap-1 text-sm font-semibold tabular-nums ${color}`}>
        <Icon className="h-4 w-4" />
        {delta}
      </div>
    </div>
  );
}

export default function BriefingPage() {
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  const {
    data: kpi,
    isLoading: kpiLoading,
    mutate: refreshKpi,
  } = useSWR<KPISummary>(
    "/api/v1/analytics/summary",
    () => fetchAPI<KPISummary>("/api/v1/analytics/summary"),
    { refreshInterval: REFRESH_INTERVAL_MS },
  );

  const {
    data: aiSummary,
    isLoading: aiLoading,
    mutate: refreshAI,
  } = useSWR<AISummary>(
    "/api/v1/ai-light/summary",
    () => fetchAPI<AISummary>("/api/v1/ai-light/summary"),
    { refreshInterval: REFRESH_INTERVAL_MS },
  );

  const {
    data: movers,
    isLoading: moversLoading,
    mutate: refreshMovers,
  } = useSWR<TopMovers>(
    ["/api/v1/analytics/top-movers", "product"],
    () =>
      fetchAPI<TopMovers>("/api/v1/analytics/top-movers", {
        entity_type: "product",
      }),
    { refreshInterval: REFRESH_INTERVAL_MS },
  );

  function refreshAll() {
    refreshKpi();
    refreshAI();
    refreshMovers();
    setLastRefreshed(new Date());
  }

  useEffect(() => {
    if (!kpiLoading) setLastRefreshed(new Date());
  }, [kpi, kpiLoading]);

  const isLoading = kpiLoading || aiLoading || moversLoading;

  const topGainers = movers?.gainers?.slice(0, 2) ?? [];
  const topLoser = movers?.losers?.[0];
  const actionItems = [
    ...topGainers.map((g) => ({
      label: `Capitalise on ${g.name} momentum`,
      delta: fmtPct(g.change_pct ?? null),
      positive: true,
    })),
    ...(topLoser
      ? [
          {
            label: `Investigate ${topLoser.name} decline`,
            delta: fmtPct(topLoser.change_pct ?? null),
            positive: false,
          },
        ]
      : []),
  ].slice(0, 3);

  const momDir: KpiDir = (kpi?.mom_growth_pct ?? 0) >= 0 ? "up" : "down";
  const yoyDir: KpiDir = (kpi?.yoy_growth_pct ?? 0) >= 0 ? "up" : "down";

  return (
    <DashboardShell
      activeHref="/briefing"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Executive" },
        { label: "Briefing" },
      ]}
    >
      <div className="page">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="page-title">Executive briefing.</h1>
            <p className="page-sub">
              Daily snapshot for leadership — auto-refreshes every 10 minutes.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-text-secondary">
              Refreshed{" "}
              {lastRefreshed.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
            <button
              onClick={refreshAll}
              disabled={isLoading}
              className="viz-panel-soft flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-text-secondary transition-colors hover:text-accent disabled:opacity-50"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`}
              />
              Refresh
            </button>
          </div>
        </div>

        <section
          className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-5"
          aria-label="Executive KPIs"
        >
          {kpiLoading || !kpi ? (
            Array.from({ length: 5 }).map((_, i) => (
              <LoadingCard key={i} lines={3} className="h-[168px]" />
            ))
          ) : (
            <>
              <KpiCard
                label="Period Revenue"
                value={`EGP ${fmt(kpi.period_gross, 0)}`}
                delta={{
                  dir: momDir,
                  text: kpi.mom_growth_pct !== null ? fmtPct(kpi.mom_growth_pct) : "—",
                }}
                sub="selected period, MoM change"
                color="accent"
                icon={Wallet}
                sparkline={[]}
              />
              <KpiCard
                label="MTD Revenue"
                value={`EGP ${fmt(kpi.mtd_gross, 0)}`}
                delta={{
                  dir: yoyDir,
                  text: kpi.yoy_growth_pct !== null ? fmtPct(kpi.yoy_growth_pct) : "—",
                }}
                sub="month-to-date vs same period last year"
                color="purple"
                icon={Calendar}
                sparkline={[]}
              />
              <KpiCard
                label="Transactions"
                value={fmt(kpi.period_transactions)}
                delta={{ dir: "up", text: "selected period" }}
                sub="unique sales transactions"
                color="amber"
                icon={ShoppingBag}
                sparkline={[]}
              />
              <KpiCard
                label="Customers"
                value={fmt(kpi.period_customers)}
                delta={{ dir: "up", text: "distinct buyers" }}
                sub="in the selected period"
                color="red"
                icon={Users}
                sparkline={[]}
              />
              <KpiCard
                label="Avg Basket"
                value={`EGP ${fmt(kpi.avg_basket_size, 0)}`}
                delta={{ dir: "up", text: "per transaction" }}
                sub="average order value"
                color="accent"
                icon={Percent}
                sparkline={[]}
              />
            </>
          )}
        </section>

        <div className="grid gap-4 lg:grid-cols-2">
          <section className="viz-panel flex flex-col gap-3 rounded-[1.75rem] p-5">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-accent" />
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
                AI Narrative Summary
              </p>
            </div>
            {aiLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div
                    key={i}
                    className="h-3 animate-pulse rounded bg-divider"
                    style={{ width: `${85 - i * 12}%` }}
                  />
                ))}
              </div>
            ) : aiSummary?.narrative ? (
              <>
                <p className="text-sm leading-relaxed text-text-secondary">
                  {aiSummary.narrative}
                </p>
                {aiSummary.highlights?.length > 0 && (
                  <ul className="mt-1 space-y-1.5">
                    {aiSummary.highlights.map((h, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-text-secondary">
                        <span className="mt-0.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-accent" />
                        {h}
                      </li>
                    ))}
                  </ul>
                )}
              </>
            ) : (
              <p className="text-sm text-text-secondary">
                AI summary not available — ensure the AI-Light service is
                running.
              </p>
            )}
          </section>

          <section className="viz-panel flex flex-col gap-3 rounded-[1.75rem] p-5">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-chart-amber" />
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
                Top Action Items
              </p>
            </div>
            {moversLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="h-12 animate-pulse rounded-lg bg-divider" />
                ))}
              </div>
            ) : actionItems.length > 0 ? (
              <div className="space-y-2">
                {actionItems.map((item, idx) => (
                  <ActionItem
                    key={idx}
                    index={idx + 1}
                    label={item.label}
                    delta={item.delta}
                    positive={item.positive}
                  />
                ))}
              </div>
            ) : (
              <p className="text-sm text-text-secondary">
                No significant movers detected in the current period.
              </p>
            )}
          </section>
        </div>
      </div>
    </DashboardShell>
  );
}
