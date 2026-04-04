"use client";

import { useForecastSummary } from "@/hooks/use-forecast";
import { formatCurrency, formatPercent } from "@/lib/formatters";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { TrendingUp, TrendingDown, Brain } from "lucide-react";

export function ForecastCard() {
  const { data, isLoading, error } = useForecastSummary();

  if (isLoading) return <LoadingCard className="h-48" />;
  if (error) return <ErrorRetry message="Failed to load forecast" />;

  if (!data) {
    return (
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="mb-4 flex items-center gap-2">
          <Brain className="h-4 w-4 text-accent" />
          <h3 className="text-sm font-semibold text-text-primary">
            Revenue Forecast
          </h3>
        </div>
        <p className="py-4 text-center text-sm text-text-secondary">
          No forecast data available
        </p>
      </div>
    );
  }

  const trendIcon =
    data.revenue_trend === "up" ? (
      <TrendingUp className="h-4 w-4 text-green-500" />
    ) : data.revenue_trend === "down" ? (
      <TrendingDown className="h-4 w-4 text-red-500" />
    ) : null;

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-accent" />
          <h3 className="text-sm font-semibold text-text-primary">
            Revenue Forecast
          </h3>
        </div>
        {data.mape !== null && (
          <span className="rounded-full bg-accent/10 px-2 py-0.5 text-[10px] text-accent">
            MAPE: {formatPercent(data.mape)}
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs text-text-secondary">Next 30 Days</p>
          <p className="flex items-center gap-1 text-lg font-bold text-text-primary">
            {formatCurrency(data.next_30d_revenue)}
            {trendIcon}
          </p>
        </div>
        <div>
          <p className="text-xs text-text-secondary">Next 3 Months</p>
          <p className="text-lg font-bold text-text-primary">
            {formatCurrency(data.next_3m_revenue)}
          </p>
        </div>
      </div>

      {/* Top growing / declining products */}
      {(data.top_growing_products.length > 0 ||
        data.top_declining_products.length > 0) && (
        <div className="mt-4 grid grid-cols-2 gap-3">
          {data.top_growing_products.length > 0 && (
            <div>
              <p className="mb-1 text-[10px] font-medium text-green-500">
                Growing
              </p>
              {data.top_growing_products.slice(0, 3).map((p) => (
                <div
                  key={p.product_key}
                  className="flex justify-between py-0.5 text-xs"
                >
                  <span className="max-w-[120px] truncate text-text-secondary">
                    {p.drug_name}
                  </span>
                  <span className="font-medium text-green-500">
                    +{formatPercent(p.forecast_change_pct)}
                  </span>
                </div>
              ))}
            </div>
          )}
          {data.top_declining_products.length > 0 && (
            <div>
              <p className="mb-1 text-[10px] font-medium text-red-500">
                Declining
              </p>
              {data.top_declining_products.slice(0, 3).map((p) => (
                <div
                  key={p.product_key}
                  className="flex justify-between py-0.5 text-xs"
                >
                  <span className="max-w-[120px] truncate text-text-secondary">
                    {p.drug_name}
                  </span>
                  <span className="font-medium text-red-500">
                    {formatPercent(p.forecast_change_pct)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
