"use client";

import { StaffQuota } from "@/hooks/use-staff-quota";
import { formatCurrency } from "@/lib/formatters";

function ProgressBar({ pct }: { pct: number | null }) {
  if (pct == null) return <span className="text-text-tertiary text-xs">No target</span>;
  const clamped = Math.min(pct, 150);
  const color =
    pct >= 100 ? "bg-green-500" : pct >= 80 ? "bg-yellow-500" : "bg-red-500";

  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-24 rounded-full bg-border overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${Math.min(clamped / 1.5, 100)}%` }}
        />
      </div>
      <span className={`text-xs font-bold ${pct >= 100 ? "text-green-500" : pct >= 80 ? "text-yellow-500" : "text-red-500"}`}>
        {pct.toFixed(0)}%
      </span>
    </div>
  );
}

interface Props {
  data: StaffQuota[];
}

export function QuotaTable({ data }: Props) {
  if (data.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card p-8 text-center text-text-tertiary">
        No quota data available for this period
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-card">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs text-text-secondary">
            <th className="px-4 py-3 font-medium">Staff</th>
            <th className="px-4 py-3 font-medium">Position</th>
            <th className="px-4 py-3 font-medium text-right">Actual Revenue</th>
            <th className="px-4 py-3 font-medium text-right">Target Revenue</th>
            <th className="px-4 py-3 font-medium">Revenue Achievement</th>
            <th className="px-4 py-3 font-medium text-right">Variance</th>
          </tr>
        </thead>
        <tbody>
          {data.map((q) => (
            <tr key={`${q.staff_key}-${q.year}-${q.month}`} className="border-b border-border/50 hover:bg-muted/50">
              <td className="px-4 py-2 font-medium text-text-primary">{q.staff_name}</td>
              <td className="px-4 py-2 text-xs text-text-secondary">{q.staff_position || "-"}</td>
              <td className="px-4 py-2 text-right text-xs font-mono text-text-primary">
                {formatCurrency(q.actual_revenue)}
              </td>
              <td className="px-4 py-2 text-right text-xs font-mono text-text-secondary">
                {q.target_revenue != null ? formatCurrency(q.target_revenue) : "-"}
              </td>
              <td className="px-4 py-2">
                <ProgressBar pct={q.revenue_achievement_pct} />
              </td>
              <td className="px-4 py-2 text-right text-xs font-mono">
                {q.revenue_variance != null ? (
                  <span className={q.revenue_variance >= 0 ? "text-green-500" : "text-red-500"}>
                    {q.revenue_variance >= 0 ? "+" : ""}
                    {formatCurrency(q.revenue_variance)}
                  </span>
                ) : "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
