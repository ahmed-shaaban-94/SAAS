"use client";

/**
 * /staff/[key] — drill-down detail on the v2 focus shell.
 */

import { useParams, notFound } from "next/navigation";

import { FocusShell } from "@/components/dashboard-v2/shell";
import { useStaffDetail } from "@/hooks/use-staff-detail";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { EmptyState } from "@/components/empty-state";
import { StatCard } from "@/components/shared/stat-card";
import { MiniTrendChart } from "@/components/shared/mini-trend-chart";
import { formatCurrency, formatNumber } from "@/lib/formatters";

export default function StaffDetailPage() {
  const params = useParams<{ key: string }>();
  const staffKey = Number(params.key);
  if (isNaN(staffKey)) {
    notFound();
  }
  const { data, error, isLoading, mutate } = useStaffDetail(staffKey);

  const breadcrumbs: Array<{ label: string; href?: string }> = [
    { label: "DataPulse", href: "/dashboard" },
    { label: "Staff", href: "/staff" },
    { label: data?.staff_name ?? String(staffKey) },
  ];

  const shell = (body: React.ReactNode) => (
    <FocusShell backHref="/staff" backLabel="Staff" breadcrumbs={breadcrumbs}>
      {body}
    </FocusShell>
  );

  if (isLoading) {
    return shell(
      <div className="space-y-6">
        <LoadingCard lines={2} />
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <LoadingCard key={i} lines={2} />
          ))}
        </div>
      </div>,
    );
  }

  if (error) {
    return shell(
      <ErrorRetry
        title="Failed to load staff details"
        description={error.message || "An error occurred while fetching staff data."}
        onRetry={() => mutate()}
      />,
    );
  }

  if (!data) {
    return shell(
      <EmptyState
        title="Staff member not found"
        description="The requested staff member could not be found."
      />,
    );
  }

  return shell(
    <>
      <div>
        <h1 className="page-title">{data.staff_name}</h1>
        <p className="page-sub">{data.staff_position}</p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Staff ID" value={data.staff_id} />
        <StatCard label="Position" value={data.staff_position} />
        <StatCard label="Net Amount" value={formatCurrency(data.total_net_amount)} />
        <StatCard label="Transactions" value={formatNumber(data.transaction_count)} />
        <StatCard label="Avg Transaction Value" value={formatCurrency(data.avg_transaction_value)} />
        <StatCard label="Unique Customers" value={formatNumber(data.unique_customers)} />
      </div>

      {data.monthly_trend && data.monthly_trend.length > 0 && (
        <MiniTrendChart data={data.monthly_trend} title="Monthly Revenue Trend" />
      )}
    </>,
  );
}
