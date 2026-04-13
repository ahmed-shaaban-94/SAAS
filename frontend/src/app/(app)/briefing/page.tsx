"use client";

import { useEffect, useState } from "react";
import useSWR from "swr";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  Sparkles,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { PageTransition } from "@/components/layout/page-transition";
import { fetchAPI } from "@/lib/api-client";
import type { KPISummary, AISummary, TopMovers } from "@/types/api";

// Auto-refresh interval — 10 minutes
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

// ---------------------------------------------------------------------------
// KPI card
// ---------------------------------------------------------------------------
function BriefingKPI({
  label,
  value,
  subLabel,
  trend,
}: {
  label: string;
  value: string;
  subLabel?: string;
  trend?: "up" | "down" | "flat" | null;
}) {
  const TrendIcon =
    trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Minus;
  const trendColor =
    trend === "up"
      ? "text-emerald-400"
      : trend === "down"
        ? "text-rose-400"
        : "text-text-secondary";

  return (
    <div className="flex flex-col gap-1.5 rounded-xl border border-border bg-card p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
        {label}
      </p>
      <p className="text-3xl font-bold tabular-nums text-text-primary">{value}</p>
      <div className="flex items-center gap-1.5">
        <TrendIcon className={`h-3.5 w-3.5 ${trendColor}`} />
        <p className={`text-xs font-medium ${trendColor}`}>{subLabel ?? "—"}</p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Action item
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
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

  // Update last-refreshed timestamp when SWR auto-refreshes
  useEffect(() => {
    if (!kpiLoading) setLastRefreshed(new Date());
  }, [kpi, kpiLoading]);

  const isLoading = kpiLoading || aiLoading || moversLoading;

  // Build top 3 action items from movers
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

  return (
    <PageTransition>
      <div className="space-y-6 p-4 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <Header
              title="Executive Briefing"
              description="Daily snapshot for leadership — auto-refreshes every 10 minutes"
            />
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

        <section>
          <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
            Key Performance Indicators
          </p>
          {kpiLoading ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              {Array.from({ length: 5 }).map((_, i) => (
                <div
                  key={i}
                  className="viz-panel h-28 animate-pulse rounded-[1.5rem]"
                />
              ))}
            </div>
          ) : kpi ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              <BriefingKPI
                label="Period Revenue"
                value={`EGP ${fmt(kpi.period_gross, 0)}`}
                subLabel={
                  kpi.mom_growth_pct !== null
                    ? `${fmtPct(kpi.mom_growth_pct)} MoM`
                    : undefined
                }
                trend={
                  kpi.mom_growth_pct === null
                    ? "flat"
                    : kpi.mom_growth_pct > 0
                      ? "up"
                      : "down"
                }
              />
              <BriefingKPI
                label="MTD Revenue"
                value={`EGP ${fmt(kpi.mtd_gross, 0)}`}
                subLabel={
                  kpi.yoy_growth_pct !== null
                    ? `${fmtPct(kpi.yoy_growth_pct)} YoY`
                    : undefined
                }
                trend={
                  kpi.yoy_growth_pct === null
                    ? "flat"
                    : kpi.yoy_growth_pct > 0
                      ? "up"
                      : "down"
                }
              />
              <BriefingKPI
                label="Transactions"
                value={fmt(kpi.period_transactions)}
                subLabel="Selected period"
                trend="flat"
              />
              <BriefingKPI
                label="Customers"
                value={fmt(kpi.period_customers)}
                subLabel="Selected period"
                trend="flat"
              />
              <BriefingKPI
                label="Avg Basket"
                value={`EGP ${fmt(kpi.avg_basket_size, 0)}`}
                subLabel="Per transaction"
                trend="flat"
              />
            </div>
          ) : (
            <div className="viz-panel flex items-center gap-2 rounded-[1.5rem] p-4 text-sm text-text-secondary">
              <AlertTriangle className="h-4 w-4 text-chart-amber" />
              KPI data unavailable
            </div>
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
    </PageTransition>
  );
}
