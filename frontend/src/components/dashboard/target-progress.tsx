"use client";

import { useTargetSummary } from "@/hooks/use-targets";
import { formatCurrency, formatPercent } from "@/lib/formatters";
import { LoadingCard } from "@/components/loading-card";
import { Target, TrendingUp, TrendingDown } from "lucide-react";

function ProgressRing({ pct, size = 80 }: { pct: number; size?: number }) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const clampedPct = Math.min(Math.max(pct, 0), 150);
  const offset = circumference - (clampedPct / 100) * circumference;

  const color =
    pct >= 100 ? "#00BFA5" : pct >= 75 ? "#FFB300" : "#EF4444";

  return (
    <svg width={size} height={size} className="-rotate-90 transform">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        stroke="currentColor"
        strokeWidth="4"
        fill="none"
        className="text-divider"
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        stroke={color}
        strokeWidth="4"
        fill="none"
        strokeDasharray={circumference}
        strokeDashoffset={Math.max(offset, 0)}
        strokeLinecap="round"
        className="transition-all duration-1000 ease-out"
      />
    </svg>
  );
}

export function TargetProgress() {
  const { data, isLoading } = useTargetSummary();

  if (isLoading) return <LoadingCard className="h-64" />;

  if (!data || data.monthly_targets.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="mb-4 flex items-center gap-2">
          <Target className="h-4 w-4 text-accent" />
          <h3 className="text-sm font-semibold text-text-primary">
            Target vs Actual
          </h3>
        </div>
        <div className="flex flex-col items-center justify-center py-8 text-text-secondary">
          <Target className="mb-2 h-10 w-10 opacity-30" />
          <p className="text-sm">No targets configured</p>
          <p className="mt-1 text-xs">Set monthly targets in the Goals page</p>
        </div>
      </div>
    );
  }

  const ytdPct = data.ytd_achievement_pct;

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="mb-4 flex items-center gap-2">
        <Target className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold text-text-primary">
          YTD Target Progress
        </h3>
      </div>

      <div className="flex items-center gap-6">
        {/* Gauge */}
        <div className="relative flex-shrink-0">
          <ProgressRing pct={ytdPct} size={100} />
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-lg font-bold text-text-primary">
              {formatPercent(ytdPct)}
            </span>
          </div>
        </div>

        {/* Stats */}
        <div className="flex-1 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">Target</span>
            <span className="font-medium text-text-primary">
              {formatCurrency(data.ytd_target)}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">Actual</span>
            <span className="font-medium text-text-primary">
              {formatCurrency(data.ytd_actual)}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">Variance</span>
            <span
              className={`flex items-center gap-1 font-medium ${
                data.ytd_actual >= data.ytd_target
                  ? "text-green-500"
                  : "text-red-500"
              }`}
            >
              {data.ytd_actual >= data.ytd_target ? (
                <TrendingUp className="h-3 w-3" />
              ) : (
                <TrendingDown className="h-3 w-3" />
              )}
              {formatCurrency(Math.abs(data.ytd_actual - data.ytd_target))}
            </span>
          </div>
        </div>
      </div>

      {/* Monthly mini bars */}
      <div className="mt-4 grid grid-cols-6 gap-1">
        {data.monthly_targets.slice(0, 12).map((m) => {
          const pct =
            m.target_value > 0
              ? (m.actual_value / m.target_value) * 100
              : 0;
          const month = m.period.split("-")[1];
          return (
            <div key={m.period} className="text-center">
              <div className="relative h-12 overflow-hidden rounded bg-divider">
                <div
                  className="absolute bottom-0 w-full rounded transition-all duration-500"
                  style={{
                    height: `${Math.min(pct, 100)}%`,
                    backgroundColor:
                      pct >= 100
                        ? "#00BFA5"
                        : pct >= 75
                          ? "#FFB300"
                          : "#EF4444",
                  }}
                />
              </div>
              <span className="mt-0.5 block text-[9px] text-text-secondary">
                {month}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
