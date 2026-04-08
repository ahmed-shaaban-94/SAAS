"use client";

import { useState } from "react";
import { useStaffQuota } from "@/hooks/use-staff-quota";
import { QuotaTable } from "./quota-table";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";

export function StaffQuotaSection() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);

  const { data, isLoading, error } = useStaffQuota(year, month);

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <select
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          className="rounded-lg border border-border bg-card px-3 py-1.5 text-sm text-text-primary"
        >
          {[2023, 2024, 2025, 2026].map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
        <select
          value={month}
          onChange={(e) => setMonth(Number(e.target.value))}
          className="rounded-lg border border-border bg-card px-3 py-1.5 text-sm text-text-primary"
        >
          {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
            <option key={m} value={m}>
              {new Date(2024, m - 1).toLocaleString("en", { month: "long" })}
            </option>
          ))}
        </select>
      </div>

      {isLoading && data.length === 0 ? (
        <LoadingCard className="h-64" />
      ) : error ? (
        <ErrorRetry title="Failed to load quota data" />
      ) : (
        <QuotaTable data={data} />
      )}
    </div>
  );
}
