"use client";

import { useState } from "react";
import { useAuditLog, AuditLogFilters } from "@/hooks/use-audit-log";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { ScrollText, ChevronLeft, ChevronRight } from "lucide-react";

const METHOD_COLORS: Record<string, string> = {
  GET: "bg-blue-500/10 text-blue-500",
  POST: "bg-green-500/10 text-green-500",
  PATCH: "bg-yellow-500/10 text-yellow-500",
  PUT: "bg-orange-500/10 text-orange-500",
  DELETE: "bg-red-500/10 text-red-500",
};

function StatusBadge({ status }: { status: number | null }) {
  if (!status) return <span className="text-text-tertiary">-</span>;
  const color =
    status < 300
      ? "text-green-500"
      : status < 400
        ? "text-blue-500"
        : status < 500
          ? "text-yellow-500"
          : "text-red-500";
  return <span className={`text-xs font-mono font-medium ${color}`}>{status}</span>;
}

export function AuditLogOverview() {
  const [filters, setFilters] = useState<AuditLogFilters>({
    page: 1,
    page_size: 25,
  });

  const { data, isLoading, error } = useAuditLog(filters);
  const totalPages = Math.ceil(data.total / (filters.page_size || 25));

  if (isLoading && data.items.length === 0) return <LoadingCard className="h-96" />;
  if (error) return <ErrorRetry title="Failed to load audit log" />;

  return (
    <div className="space-y-4 mt-6">
      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <select
          value={filters.method || ""}
          onChange={(e) => setFilters({ ...filters, method: e.target.value || undefined, page: 1 })}
          className="rounded-lg border border-border bg-card px-3 py-1.5 text-sm text-text-primary"
        >
          <option value="">All Methods</option>
          {["GET", "POST", "PATCH", "PUT", "DELETE"].map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>

        <input
          type="text"
          placeholder="Filter endpoint..."
          value={filters.endpoint || ""}
          onChange={(e) => setFilters({ ...filters, endpoint: e.target.value || undefined, page: 1 })}
          className="rounded-lg border border-border bg-card px-3 py-1.5 text-sm text-text-primary placeholder:text-text-tertiary"
        />

        <input
          type="date"
          value={filters.start_date || ""}
          onChange={(e) => setFilters({ ...filters, start_date: e.target.value || undefined, page: 1 })}
          className="rounded-lg border border-border bg-card px-3 py-1.5 text-sm text-text-primary"
        />
        <input
          type="date"
          value={filters.end_date || ""}
          onChange={(e) => setFilters({ ...filters, end_date: e.target.value || undefined, page: 1 })}
          className="rounded-lg border border-border bg-card px-3 py-1.5 text-sm text-text-primary"
        />
      </div>

      {/* Summary */}
      <div className="flex items-center gap-2 text-sm text-text-secondary">
        <ScrollText className="h-4 w-4" />
        <span>{data.total.toLocaleString()} entries</span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-border bg-card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-text-secondary">
              <th className="px-4 py-3 font-medium">Time</th>
              <th className="px-4 py-3 font-medium">Method</th>
              <th className="px-4 py-3 font-medium">Endpoint</th>
              <th className="px-4 py-3 font-medium">Action</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Duration</th>
              <th className="px-4 py-3 font-medium">User</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((entry) => (
              <tr key={entry.id} className="border-b border-border/50 hover:bg-muted/50">
                <td className="px-4 py-2 text-xs text-text-secondary whitespace-nowrap">
                  {new Date(entry.created_at).toLocaleString()}
                </td>
                <td className="px-4 py-2">
                  <span className={`inline-block rounded px-1.5 py-0.5 text-xs font-mono font-medium ${METHOD_COLORS[entry.method] ?? "bg-muted text-text-secondary"}`}>
                    {entry.method}
                  </span>
                </td>
                <td className="px-4 py-2 font-mono text-xs text-text-primary max-w-[300px] truncate">
                  {entry.endpoint}
                </td>
                <td className="px-4 py-2 text-xs text-text-secondary">{entry.action}</td>
                <td className="px-4 py-2"><StatusBadge status={entry.response_status} /></td>
                <td className="px-4 py-2 text-xs text-text-secondary">
                  {entry.duration_ms != null ? `${entry.duration_ms.toFixed(0)}ms` : "-"}
                </td>
                <td className="px-4 py-2 text-xs text-text-secondary truncate max-w-[120px]">
                  {entry.user_id || "-"}
                </td>
              </tr>
            ))}
            {data.items.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-text-tertiary">
                  No audit log entries found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-xs text-text-secondary">
            Page {data.page} of {totalPages}
          </span>
          <div className="flex gap-1">
            <button
              onClick={() => setFilters({ ...filters, page: Math.max(1, (filters.page || 1) - 1) })}
              disabled={data.page <= 1}
              className="rounded-lg border border-border p-1.5 text-text-secondary hover:bg-muted disabled:opacity-30"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setFilters({ ...filters, page: Math.min(totalPages, (filters.page || 1) + 1) })}
              disabled={data.page >= totalPages}
              className="rounded-lg border border-border p-1.5 text-text-secondary hover:bg-muted disabled:opacity-30"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
