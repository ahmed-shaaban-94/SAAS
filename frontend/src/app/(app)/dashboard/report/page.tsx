"use client";

import { useSummary } from "@/hooks/use-summary";
import { useTopProducts } from "@/hooks/use-top-products";
import { useTopCustomers } from "@/hooks/use-top-customers";
import { useTopStaff } from "@/hooks/use-top-staff";
import { useFilters } from "@/contexts/filter-context";
import { formatCurrency, formatNumber, formatPercent } from "@/lib/formatters";
import { LoadingCard } from "@/components/loading-card";
import { Printer } from "lucide-react";

export default function PrintReportPage() {
  const { filters } = useFilters();
  const { data: summary, isLoading: sumLoading } = useSummary(filters);
  const { data: products, isLoading: prodLoading } = useTopProducts(filters);
  const { data: customers, isLoading: custLoading } = useTopCustomers(filters);
  const { data: staff, isLoading: staffLoading } = useTopStaff(filters);

  const isLoading = sumLoading || prodLoading || custLoading || staffLoading;

  if (isLoading) {
    return (
      <div className="space-y-6 p-8">
        {Array.from({ length: 4 }).map((_, i) => (
          <LoadingCard key={i} lines={4} />
        ))}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8 bg-page p-8 print:bg-white print:text-black">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary print:text-black">
            DataPulse Sales Report
          </h1>
          <p className="mt-1 text-sm text-text-secondary print:text-gray-600">
            Generated {new Date().toLocaleDateString("en-US", {
              year: "numeric",
              month: "long",
              day: "numeric",
            })}
          </p>
        </div>
        <button
          onClick={() => window.print()}
          className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-page transition-colors hover:bg-accent/90 print:hidden"
        >
          <Printer className="h-4 w-4" />
          Print
        </button>
      </div>

      {/* KPI Summary */}
      {summary && (
        <section>
          <h2 className="mb-4 text-lg font-semibold text-text-primary print:text-black">
            Key Performance Indicators
          </h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <KPICell label="Today Gross" value={formatCurrency(summary.today_gross)} />
            <KPICell label="MTD Gross" value={formatCurrency(summary.mtd_gross)} />
            <KPICell label="YTD Gross" value={formatCurrency(summary.ytd_gross)} />
            <KPICell label="Daily Transactions" value={formatNumber(summary.daily_transactions)} />
            <KPICell label="Daily Customers" value={formatNumber(summary.daily_customers)} />
            <KPICell
              label="MoM Growth"
              value={summary.mom_growth_pct !== null ? formatPercent(summary.mom_growth_pct) : "N/A"}
            />
            <KPICell
              label="YoY Growth"
              value={summary.yoy_growth_pct !== null ? formatPercent(summary.yoy_growth_pct) : "N/A"}
            />
          </div>
        </section>
      )}

      {/* Top Products */}
      {products && products.items.length > 0 && (
        <section>
          <h2 className="mb-4 text-lg font-semibold text-text-primary print:text-black">
            Top Products
          </h2>
          <ReportTable
            headers={["Rank", "Product", "Revenue", "% of Total"]}
            rows={products.items.map((item) => [
              `#${item.rank}`,
              item.name,
              formatCurrency(item.value),
              formatPercent(item.pct_of_total),
            ])}
          />
        </section>
      )}

      {/* Top Customers */}
      {customers && customers.items.length > 0 && (
        <section>
          <h2 className="mb-4 text-lg font-semibold text-text-primary print:text-black">
            Top Customers
          </h2>
          <ReportTable
            headers={["Rank", "Customer", "Revenue", "% of Total"]}
            rows={customers.items.map((item) => [
              `#${item.rank}`,
              item.name,
              formatCurrency(item.value),
              formatPercent(item.pct_of_total),
            ])}
          />
        </section>
      )}

      {/* Top Staff */}
      {staff && staff.items.length > 0 && (
        <section>
          <h2 className="mb-4 text-lg font-semibold text-text-primary print:text-black">
            Top Staff
          </h2>
          <ReportTable
            headers={["Rank", "Staff", "Revenue", "% of Total"]}
            rows={staff.items.map((item) => [
              `#${item.rank}`,
              item.name,
              formatCurrency(item.value),
              formatPercent(item.pct_of_total),
            ])}
          />
        </section>
      )}
    </div>
  );
}

function KPICell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4 print:border-gray-300 print:bg-gray-50">
      <p className="text-xs font-semibold uppercase tracking-wide text-text-secondary print:text-gray-500">
        {label}
      </p>
      <p className="mt-1 text-xl font-bold text-text-primary print:text-black">
        {value}
      </p>
    </div>
  );
}

function ReportTable({
  headers,
  rows,
}: {
  headers: string[];
  rows: string[][];
}) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-border print:border-gray-300">
          {headers.map((h) => (
            <th
              key={h}
              className="px-3 py-2 text-left font-semibold text-text-secondary print:text-gray-500"
            >
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr
            key={i}
            className="border-b border-divider print:border-gray-200"
          >
            {row.map((cell, j) => (
              <td
                key={j}
                className="px-3 py-2 text-text-primary print:text-black"
              >
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
