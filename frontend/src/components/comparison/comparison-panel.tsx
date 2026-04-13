"use client";

import { useState, useMemo } from "react";
import { ArrowLeftRight, X } from "lucide-react";
import { useComparison, type ComparisonPeriod } from "@/hooks/use-comparison";
import { ComparisonKPI } from "./comparison-kpi";
import { ComparisonChart } from "./comparison-chart";
import { PeriodPicker } from "./period-picker";
import { LoadingCard } from "@/components/loading-card";

interface ComparisonPanelProps {
  onClose: () => void;
}

function getDefaultPeriods(): {
  current: ComparisonPeriod;
  previous: ComparisonPeriod;
} {
  const now = new Date();
  const thisMonthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  const lastMonthStart = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const lastMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0);

  const fmt = (d: Date) => d.toISOString().split("T")[0];

  return {
    current: {
      start_date: fmt(thisMonthStart),
      end_date: fmt(now),
      label: "This Month",
    },
    previous: {
      start_date: fmt(lastMonthStart),
      end_date: fmt(lastMonthEnd),
      label: "Last Month",
    },
  };
}

export function ComparisonPanel({ onClose }: ComparisonPanelProps) {
  const defaults = useMemo(() => getDefaultPeriods(), []);
  const [currentPeriod, setCurrentPeriod] = useState<ComparisonPeriod>(
    defaults.current,
  );
  const [previousPeriod, setPreviousPeriod] = useState<ComparisonPeriod>(
    defaults.previous,
  );

  const { current, previous, isLoading } = useComparison(
    currentPeriod,
    previousPeriod,
  );

  return (
    <div className="mb-6 rounded-xl border border-accent/30 bg-card p-5">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ArrowLeftRight className="h-5 w-5 text-accent" />
          <h2 className="text-sm font-semibold text-text-primary">
            Compare Periods
          </h2>
        </div>
        <button
          onClick={onClose}
          className="rounded-md p-1 text-text-secondary hover:text-text-primary"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Period Selectors */}
      <div className="mb-6 grid gap-4 sm:grid-cols-2">
        <PeriodPicker
          label="Current Period"
          period={currentPeriod}
          onChange={setCurrentPeriod}
          accentColor="text-accent"
        />
        <PeriodPicker
          label="Previous Period"
          period={previousPeriod}
          onChange={setPreviousPeriod}
          accentColor="text-chart-blue"
        />
      </div>

      {isLoading ? (
        <LoadingCard lines={4} />
      ) : current && previous ? (
        <>
          {/* KPI Comparison
           * Uses period-total fields (today_gross / daily_transactions) — NOT mtd_*
           * fields. The backend range path stores the selected-range total in
           * today_gross; mtd_* hold "running MTD as of the range's end date",
           * which is the wrong question when comparing two arbitrary periods
           * (e.g. "Feb 10-20" vs "Jan 10-20" would show full-month MTD, not
           * the picked 10-day window).
           */}
          <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <ComparisonKPI
              label="Revenue"
              currentValue={current.kpi.today_gross}
              previousValue={previous.kpi.today_gross}
              isCurrency
            />
            <ComparisonKPI
              label="Transactions"
              currentValue={current.kpi.daily_transactions}
              previousValue={previous.kpi.daily_transactions}
            />
            <ComparisonKPI
              label="Avg Basket"
              currentValue={current.kpi.avg_basket_size}
              previousValue={previous.kpi.avg_basket_size}
              isCurrency
            />
            <ComparisonKPI
              label="Customers"
              currentValue={current.kpi.daily_customers}
              previousValue={previous.kpi.daily_customers}
            />
          </div>

          {/* Trend Comparison Chart */}
          <ComparisonChart
            currentData={current.daily_trend.points}
            previousData={previous.daily_trend.points}
            currentLabel={currentPeriod.label}
            previousLabel={previousPeriod.label}
          />
        </>
      ) : null}
    </div>
  );
}
