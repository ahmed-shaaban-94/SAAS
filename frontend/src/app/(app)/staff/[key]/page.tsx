"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { useStaffDetail } from "@/hooks/use-staff-detail";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { EmptyState } from "@/components/empty-state";
import { StatCard } from "@/components/shared/stat-card";
import { formatCurrency, formatNumber } from "@/lib/formatters";

export default function StaffDetailPage() {
  const params = useParams<{ key: string }>();
  const staffKey = Number(params.key);
  const { data, error, isLoading, mutate } = useStaffDetail(staffKey);

  if (isLoading) {
    return (
      <PageTransition>
        <div className="space-y-6">
          <LoadingCard lines={2} />
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <LoadingCard key={i} lines={2} />
            ))}
          </div>
        </div>
      </PageTransition>
    );
  }

  if (error) {
    return (
      <PageTransition>
        <ErrorRetry
          title="Failed to load staff details"
          description={error.message || "An error occurred while fetching staff data."}
          onRetry={() => mutate()}
        />
      </PageTransition>
    );
  }

  if (!data) {
    return (
      <PageTransition>
        <EmptyState
          title="Staff member not found"
          description="The requested staff member could not be found."
        />
      </PageTransition>
    );
  }

  return (
    <PageTransition>
      <div className="space-y-6">
        <Breadcrumbs />

        <div>
          <h1 className="text-2xl font-bold text-text-primary">{data.staff_name}</h1>
          <p className="mt-1 text-sm text-text-secondary">{data.staff_position}</p>
        </div>

        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard label="Staff ID" value={data.staff_id} />
          <StatCard label="Position" value={data.staff_position} />
          <StatCard label="Net Amount" value={formatCurrency(data.total_net_amount)} />
          <StatCard label="Transactions" value={formatNumber(data.transaction_count)} />
          <StatCard label="Avg Transaction Value" value={formatCurrency(data.avg_transaction_value)} />
          <StatCard label="Unique Customers" value={formatNumber(data.unique_customers)} />
        </div>

        <Link
          href="/staff"
          className="inline-flex items-center gap-1 text-sm text-accent hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Staff
        </Link>
      </div>
    </PageTransition>
  );
}
