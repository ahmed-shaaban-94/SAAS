"use client";

import { memo } from "react";
import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAISummary } from "@/hooks/use-ai-summary";
import { useDashboardData } from "@/contexts/dashboard-data-context";
import { formatCurrency, formatNumber, formatPercent } from "@/lib/formatters";

interface NarrativeSummaryCardProps {
  variant?: "default" | "print";
  className?: string;
}

function getTimeGreeting(): string | null {
  const now = new Date();
  const hour = now.getHours();
  const day = now.getDate();
  const lastDayOfMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();

  if (day === 1) return "New month:";
  if (day > lastDayOfMonth - 5) return "End of month snapshot:";
  if (hour >= 6 && hour < 12) return "This morning:";
  if (hour >= 12 && hour < 18) return "This afternoon:";
  return null;
}

function buildFallbackNarrative(kpi: {
  today_gross: number;
  mom_growth_pct: number | null;
  daily_transactions: number;
  daily_returns: number;
}): string {
  const direction = kpi.mom_growth_pct !== null
    ? kpi.mom_growth_pct > 0 ? "up" : kpi.mom_growth_pct < 0 ? "down" : "flat"
    : null;

  const parts: string[] = [];

  if (direction && kpi.mom_growth_pct !== null) {
    parts.push(`Revenue is ${direction} ${formatPercent(Math.abs(kpi.mom_growth_pct))} compared to the prior period`);
  } else {
    parts.push(`Revenue stands at ${formatCurrency(kpi.today_gross)} for the selected period`);
  }

  parts.push(`with ${formatNumber(kpi.daily_transactions)} completed transactions`);

  if (kpi.daily_returns > 0) {
    const returnRate = (kpi.daily_returns / (kpi.daily_transactions + kpi.daily_returns)) * 100;
    if (returnRate > 5) {
      parts.push(`Returns are elevated at ${returnRate.toFixed(1)}% of total activity`);
    } else {
      parts.push("Returns remain stable");
    }
  }

  return parts.join(". ") + ".";
}

export const NarrativeSummaryCard = memo(function NarrativeSummaryCard({
  variant = "default",
  className,
}: NarrativeSummaryCardProps) {
  const { data: aiData, isLoading: aiLoading } = useAISummary();
  const { data: dashboardData } = useDashboardData();
  const kpi = dashboardData?.kpi;

  // Nothing to show yet
  if (aiLoading && !kpi) return null;

  const greeting = getTimeGreeting();
  const narrative = aiData?.narrative ?? (kpi ? buildFallbackNarrative(kpi) : null);

  if (!narrative) return null;

  const isPrint = variant === "print";

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[1.6rem] p-4 sm:p-6",
        isPrint
          ? "border border-border bg-white print:bg-white"
          : "viz-panel border border-border/80",
        className,
      )}
    >
      <div className="absolute inset-x-6 top-0 h-1 rounded-b-full bg-gradient-to-r from-chart-purple via-accent to-chart-blue" />
      <div className="mb-3 flex items-center gap-2">
        <div className="viz-panel-soft rounded-xl p-2">
          <Sparkles className="h-4 w-4 text-accent" />
        </div>
        <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
          {aiData ? "AI Summary" : "Business Summary"}
        </span>
      </div>

      <p className="text-sm leading-7 text-text-primary">
        {greeting && (
          <span className="font-semibold text-accent mr-1">{greeting}</span>
        )}
        {narrative}
      </p>

      {aiData?.highlights && aiData.highlights.length > 0 && (
        <ul className="mt-4 space-y-2">
          {aiData.highlights.map((h, i) => (
            <li key={i} className="viz-panel-soft flex items-start gap-2 rounded-2xl px-3 py-2 text-xs text-text-secondary">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
              {h}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
});
