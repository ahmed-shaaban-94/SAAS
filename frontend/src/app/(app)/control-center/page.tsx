"use client";

import { PageTransition } from "@/components/layout/page-transition";
import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { useHealthSummary } from "@/hooks/use-health-summary";
import {
  Activity,
  CheckCircle2,
  Clock,
  FileStack,
  AlertTriangle,
} from "lucide-react";

function formatDate(iso: string | null): string {
  if (!iso) return "Never";
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  highlight?: boolean;
}

function StatCard({ icon, label, value, highlight }: StatCardProps) {
  return (
    <div
      className={`flex items-start gap-4 rounded-xl border p-4 ${
        highlight
          ? "border-red-500/30 bg-red-500/5"
          : "border-border bg-card"
      }`}
    >
      <div
        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
          highlight ? "bg-red-500/10 text-red-500" : "bg-accent/10 text-accent"
        }`}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <p className="truncate text-xs text-text-secondary">{label}</p>
        <p
          className={`mt-0.5 text-xl font-semibold ${
            highlight ? "text-red-500" : "text-text-primary"
          }`}
        >
          {value}
        </p>
      </div>
    </div>
  );
}

export default function ControlCenterPage() {
  const { data, error, isLoading, mutate } = useHealthSummary();

  if (isLoading) return <LoadingCard />;
  if (error) return <ErrorRetry onRetry={() => mutate()} />;
  if (!data) return null;

  const hasFailed = data.failed_syncs_last_24h > 0;

  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Control Center"
        description="Overview of your data pipeline health"
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          icon={<Activity className="h-5 w-5" />}
          label="Active Connections"
          value={data.active_connections}
        />
        <StatCard
          icon={<Clock className="h-5 w-5" />}
          label="Last Sync"
          value={formatDate(data.last_sync_at)}
        />
        <StatCard
          icon={<CheckCircle2 className="h-5 w-5" />}
          label="Active Release"
          value={
            data.active_release_version != null
              ? `v${data.active_release_version}`
              : "None"
          }
        />
        <StatCard
          icon={<FileStack className="h-5 w-5" />}
          label="Pending Drafts"
          value={data.pending_drafts}
        />
        <StatCard
          icon={<AlertTriangle className="h-5 w-5" />}
          label="Failed Syncs (24h)"
          value={data.failed_syncs_last_24h}
          highlight={hasFailed}
        />
      </div>
    </PageTransition>
  );
}
