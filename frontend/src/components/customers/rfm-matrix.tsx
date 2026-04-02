"use client";

import { useState } from "react";
import { useSegmentSummary, useCustomerSegments } from "@/hooks/use-segments";
import { formatCurrency, formatNumber } from "@/lib/formatters";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { Users } from "lucide-react";

// RFM segment descriptions and colors
const SEGMENT_META: Record<string, { label: string; color: string; emoji: string; description: string }> = {
  Champions: { label: "Champions", color: "#00BFA5", emoji: "★", description: "Best customers - high R, F, M" },
  "Loyal Customers": { label: "Loyal", color: "#2196F3", emoji: "♦", description: "Buy often, good spenders" },
  "Potential Loyalist": { label: "Potential Loyalist", color: "#8BC34A", emoji: "↑", description: "Recent, moderate frequency" },
  "New Customers": { label: "New", color: "#FFB300", emoji: "●", description: "Bought recently, first time" },
  "Promising": { label: "Promising", color: "#FF9800", emoji: "◆", description: "Recent but low frequency" },
  "Need Attention": { label: "Need Attention", color: "#FF5722", emoji: "!", description: "Above avg but slipping" },
  "About To Sleep": { label: "About to Sleep", color: "#E91E63", emoji: "⌛", description: "Below avg recency & frequency" },
  "At Risk": { label: "At Risk", color: "#F44336", emoji: "⚠", description: "Spent big, absent for a while" },
  "Cant Lose Them": { label: "Can't Lose", color: "#9C27B0", emoji: "★", description: "High value, disappearing" },
  Hibernating: { label: "Hibernating", color: "#607D8B", emoji: "⏸", description: "Long gone, low value" },
  Lost: { label: "Lost", color: "#9E9E9E", emoji: "✕", description: "Lowest R, F, M scores" },
};

function getSegmentMeta(segment: string) {
  return SEGMENT_META[segment] || { label: segment, color: "#64748b", emoji: "?", description: "" };
}

export function RFMMatrix() {
  const { data: segments, isLoading } = useSegmentSummary();
  const [selectedSegment, setSelectedSegment] = useState<string | null>(null);
  const { data: customers, isLoading: customersLoading } = useCustomerSegments(
    selectedSegment ?? undefined,
    20,
  );

  if (isLoading) return <LoadingCard className="h-96" />;
  if (!segments || segments.length === 0) return <EmptyState title="No customer segment data available" />;

  const totalCustomers = segments.reduce((sum, s) => sum + s.count, 0);

  return (
    <div className="space-y-6">
      {/* Segment Grid */}
      <div className="rounded-xl border border-border bg-card p-4">
        <div className="flex items-center gap-2 mb-4">
          <Users className="h-4 w-4 text-accent" />
          <h3 className="text-sm font-semibold text-text-primary">Customer Segments (RFM)</h3>
          <span className="ml-auto text-xs text-text-secondary">{formatNumber(totalCustomers)} customers</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {segments.map((seg) => {
            const meta = getSegmentMeta(seg.segment);
            const isSelected = selectedSegment === seg.segment;
            return (
              <button
                key={seg.segment}
                onClick={() => setSelectedSegment(isSelected ? null : seg.segment)}
                className={`text-left rounded-lg border p-3 transition-all hover:shadow-md ${
                  isSelected
                    ? "border-accent bg-accent/5 ring-1 ring-accent"
                    : "border-border bg-card hover:border-accent/50"
                }`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <div
                    className="w-3 h-3 rounded-full flex-shrink-0"
                    style={{ backgroundColor: meta.color }}
                  />
                  <span className="text-xs font-semibold text-text-primary truncate">
                    {meta.label}
                  </span>
                </div>
                <div className="text-lg font-bold text-text-primary">{formatNumber(seg.count)}</div>
                <div className="text-[10px] text-text-secondary">{seg.pct_of_customers.toFixed(1)}% of total</div>
                <div className="mt-2 text-xs text-text-secondary">
                  Avg: {formatCurrency(seg.avg_monetary)}
                </div>
                {/* Mini progress bar */}
                <div className="mt-1.5 h-1 rounded-full bg-divider overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${seg.pct_of_customers}%`, backgroundColor: meta.color }}
                  />
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Segment Detail */}
      {selectedSegment && (
        <div className="rounded-xl border border-border bg-card p-4 animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-semibold text-text-primary flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: getSegmentMeta(selectedSegment).color }}
              />
              {getSegmentMeta(selectedSegment).label} Customers
            </h4>
            <span className="text-xs text-text-secondary">{getSegmentMeta(selectedSegment).description}</span>
          </div>

          {customersLoading ? (
            <LoadingCard className="h-32" />
          ) : customers && customers.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-2 px-2 font-medium text-text-secondary">Customer</th>
                    <th className="text-center py-2 px-2 font-medium text-text-secondary">R</th>
                    <th className="text-center py-2 px-2 font-medium text-text-secondary">F</th>
                    <th className="text-center py-2 px-2 font-medium text-text-secondary">M</th>
                    <th className="text-right py-2 px-2 font-medium text-text-secondary">Revenue</th>
                    <th className="text-right py-2 px-2 font-medium text-text-secondary">Frequency</th>
                    <th className="text-right py-2 px-2 font-medium text-text-secondary">Last Visit</th>
                  </tr>
                </thead>
                <tbody>
                  {customers.map((c) => (
                    <tr key={c.customer_key} className="border-b border-border/50 hover:bg-divider/50">
                      <td className="py-1.5 px-2 text-text-primary font-medium truncate max-w-[150px]">
                        {c.customer_name}
                      </td>
                      <td className="py-1.5 px-2 text-center">
                        <span className={`inline-flex h-5 w-5 items-center justify-center rounded text-[10px] font-bold ${
                          c.r_score >= 4 ? "bg-green-500/20 text-green-500" :
                          c.r_score >= 3 ? "bg-yellow-500/20 text-yellow-500" : "bg-red-500/20 text-red-500"
                        }`}>{c.r_score}</span>
                      </td>
                      <td className="py-1.5 px-2 text-center">
                        <span className={`inline-flex h-5 w-5 items-center justify-center rounded text-[10px] font-bold ${
                          c.f_score >= 4 ? "bg-green-500/20 text-green-500" :
                          c.f_score >= 3 ? "bg-yellow-500/20 text-yellow-500" : "bg-red-500/20 text-red-500"
                        }`}>{c.f_score}</span>
                      </td>
                      <td className="py-1.5 px-2 text-center">
                        <span className={`inline-flex h-5 w-5 items-center justify-center rounded text-[10px] font-bold ${
                          c.m_score >= 4 ? "bg-green-500/20 text-green-500" :
                          c.m_score >= 3 ? "bg-yellow-500/20 text-yellow-500" : "bg-red-500/20 text-red-500"
                        }`}>{c.m_score}</span>
                      </td>
                      <td className="py-1.5 px-2 text-right text-text-primary">{formatCurrency(c.monetary)}</td>
                      <td className="py-1.5 px-2 text-right text-text-secondary">{c.frequency}x</td>
                      <td className="py-1.5 px-2 text-right text-text-secondary">{c.days_since_last}d ago</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-text-secondary py-4 text-center">No customers in this segment</p>
          )}
        </div>
      )}
    </div>
  );
}
