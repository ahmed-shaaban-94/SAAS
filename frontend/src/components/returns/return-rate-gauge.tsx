"use client";

import { useReturnsTrend } from "@/hooks/use-returns-trend";
import { formatCurrency, formatNumber } from "@/lib/formatters";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { ShieldAlert, ShieldCheck } from "lucide-react";

export function ReturnRateGauge() {
  const { data, isLoading, error } = useReturnsTrend();

  if (isLoading) return <LoadingCard className="h-48" />;
  if (error) return <ErrorRetry message="Failed to load return rate" />;
  if (!data) return null;

  const rate = data.avg_return_rate;
  const isHealthy = rate < 5;
  const isWarning = rate >= 5 && rate < 10;

  // SVG gauge
  const startAngle = -135;
  const endAngle = 135;
  const totalAngle = endAngle - startAngle;
  const normalizedRate = Math.min(rate / 20, 1); // 0-20% scale
  const currentAngle = startAngle + normalizedRate * totalAngle;

  const r = 60;
  const cx = 80;
  const cy = 80;

  const polarToCartesian = (angle: number) => ({
    x: cx + r * Math.cos((angle * Math.PI) / 180),
    y: cy + r * Math.sin((angle * Math.PI) / 180),
  });

  const bgStart = polarToCartesian(startAngle);
  const bgEnd = polarToCartesian(endAngle);
  const valEnd = polarToCartesian(currentAngle);

  const bgPath = `M ${bgStart.x} ${bgStart.y} A ${r} ${r} 0 1 1 ${bgEnd.x} ${bgEnd.y}`;
  const valPath = `M ${bgStart.x} ${bgStart.y} A ${r} ${r} 0 ${normalizedRate > 0.5 ? 1 : 0} 1 ${valEnd.x} ${valEnd.y}`;

  const gaugeColor = isHealthy ? "#059669" : isWarning ? "#FFB300" : "#EF4444";

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center gap-2 mb-3">
        {isHealthy ? (
          <ShieldCheck className="h-4 w-4 text-green-500" />
        ) : (
          <ShieldAlert className="h-4 w-4 text-red-500" />
        )}
        <h3 className="text-sm font-semibold text-text-primary">Return Rate</h3>
      </div>

      <div className="flex items-center gap-4">
        <svg width="160" height="110" viewBox="0 0 160 110" className="flex-shrink-0" role="img" aria-label={`Return rate gauge: ${rate.toFixed(1)}% — ${isHealthy ? "healthy" : isWarning ? "needs attention" : "critical"}`}>
          {/* Background arc */}
          <path d={bgPath} fill="none" stroke="currentColor" strokeWidth="12" strokeLinecap="round" className="text-divider" />
          {/* Value arc */}
          <path d={valPath} fill="none" stroke={gaugeColor} strokeWidth="12" strokeLinecap="round" />
          {/* Center text */}
          <text x={cx} y={cy - 5} textAnchor="middle" className="text-xl font-bold fill-text-primary">
            {rate.toFixed(1)}%
          </text>
          <text x={cx} y={cy + 12} textAnchor="middle" className="text-[10px] fill-text-secondary">
            return rate
          </text>
          {/* Scale labels */}
          <text x="15" y="105" className="text-[9px] fill-text-secondary">0%</text>
          <text x="135" y="105" className="text-[9px] fill-text-secondary">20%</text>
        </svg>

        <div className="flex-1 space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-text-secondary">Total Returns</span>
            <span className="font-medium text-text-primary">{formatNumber(data.total_returns)}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-text-secondary">Return Amount</span>
            <span className="font-medium text-text-primary">{formatCurrency(data.total_return_amount)}</span>
          </div>
          <div className={`mt-2 text-xs font-medium rounded px-2 py-1 text-center ${
            isHealthy ? "bg-green-500/10 text-green-500" :
            isWarning ? "bg-yellow-500/10 text-yellow-500" : "bg-red-500/10 text-red-500"
          }`}>
            {isHealthy ? "Healthy" : isWarning ? "Needs Attention" : "Critical"}
          </div>
        </div>
      </div>
    </div>
  );
}
