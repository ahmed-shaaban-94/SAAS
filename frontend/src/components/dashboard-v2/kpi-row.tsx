"use client";

/**
 * KPI row for dashboard v2 — four stat cards with Fraunces serif values.
 *
 * Real data: driven by useSummary() and useExpirySummary().
 * Each card's value is wrapped in <WhyChangedTrigger> so the user can
 * click any number to see what drove it.
 */

import { useMemo } from "react";
import { useSummary } from "@/hooks/use-summary";
import { useExpirySummary } from "@/hooks/use-expiry-summary";
import { WhyChangedTrigger } from "@/components/why-changed/why-changed-trigger";
import type { WhyChangedData } from "@/components/why-changed/why-changed";
import {
  buildMtdRevenueWhy,
  buildExpiryExposureWhy,
  buildAvgBasketWhy,
} from "@/components/why-changed/why-changed-data";

interface Kpi {
  label: string;
  value: string;
  delta?: { text: string; tone: "up" | "dn" };
  why?: WhyChangedData;
}

function fmtEGP(v: number): string {
  if (v >= 1_000_000) return `EGP ${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000) return `EGP ${(v / 1_000).toFixed(0)}K`;
  return `EGP ${Math.round(v)}`;
}

function fmtPct(v: number | null | undefined, suffix = "%"): string {
  if (v == null) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(1)}${suffix}`;
}

const MOCK_KPIS: Kpi[] = [
  {
    label: "Revenue · month-to-date",
    value: "EGP 4.72M",
    delta: { text: "+5% vs plan", tone: "up" },
    why: buildMtdRevenueWhy(4_720_000, 5.0),
  },
  { label: "Transactions · MTD", value: "12,347", delta: { text: "+8% MoM", tone: "up" } },
  {
    label: "Avg basket size",
    value: "3.2 items",
    delta: { text: "−0.1 vs last 30d", tone: "dn" },
    why: buildAvgBasketWhy(3.2),
  },
  {
    label: "Expiry exposure · 30d",
    value: "EGP 142K",
    delta: { text: "+EGP 38K WoW", tone: "dn" },
    why: buildExpiryExposureWhy(142_000),
  },
];

export function KpiRow() {
  const { data: summary } = useSummary();
  const { data: expirySummary } = useExpirySummary();

  const kpis: Kpi[] = useMemo(() => {
    if (!summary) return MOCK_KPIS;

    const expiryExposure =
      expirySummary?.reduce((s, r) => s + r.total_expired_value, 0) ?? 0;

    const momTone: "up" | "dn" = (summary.mom_growth_pct ?? 0) >= 0 ? "up" : "dn";

    return [
      {
        label: "Revenue · month-to-date",
        value: fmtEGP(summary.mtd_gross),
        delta:
          summary.mom_growth_pct != null
            ? { text: `${fmtPct(summary.mom_growth_pct)} MoM`, tone: momTone }
            : undefined,
        why: buildMtdRevenueWhy(summary.mtd_gross, summary.mom_growth_pct),
      },
      {
        label: "Transactions · MTD",
        value: summary.mtd_transactions.toLocaleString(),
      },
      {
        label: "Avg basket size",
        value: `${summary.avg_basket_size.toFixed(1)} items`,
        why: buildAvgBasketWhy(summary.avg_basket_size),
      },
      {
        label: "Expiry exposure",
        value: expiryExposure > 0 ? fmtEGP(expiryExposure) : "—",
        delta:
          expiryExposure > 0
            ? { text: `across ${expirySummary?.length ?? 0} sites`, tone: "dn" }
            : undefined,
        why: expiryExposure > 0 ? buildExpiryExposureWhy(expiryExposure) : undefined,
      },
    ];
  }, [summary, expirySummary]);

  return (
    <div className="kpi-row">
      {kpis.map((k) => (
        <div key={k.label} className="kpi">
          <div className="label">{k.label}</div>
          <div className="value tabular">
            {k.why ? (
              <WhyChangedTrigger data={k.why} inline>
                {k.value}
              </WhyChangedTrigger>
            ) : (
              k.value
            )}
          </div>
          {k.delta && (
            <div className={`delta ${k.delta.tone}`}>
              {k.delta.tone === "up" ? "▲" : "▼"} {k.delta.text}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
