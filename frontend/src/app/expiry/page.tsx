"use client";

/**
 * /expiry — v2 cutover. Near-expiry inventory, expired batches, and
 * write-off exposure rendered on the shared DashboardShell.
 */

import dynamic from "next/dynamic";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { FilterBar } from "@/components/filters/filter-bar";
import { LoadingCard } from "@/components/loading-card";

const ExpiryCalendar = dynamic(
  () =>
    import("@/components/expiry/expiry-calendar").then((m) => ({
      default: m.ExpiryCalendar,
    })),
  { loading: () => <LoadingCard lines={8} />, ssr: false },
);

const NearExpiryList = dynamic(
  () =>
    import("@/components/expiry/near-expiry-list").then((m) => ({
      default: m.NearExpiryList,
    })),
  { loading: () => <LoadingCard lines={6} />, ssr: false },
);

const ExpiredStockTable = dynamic(
  () =>
    import("@/components/expiry/expired-stock-table").then((m) => ({
      default: m.ExpiredStockTable,
    })),
  { loading: () => <LoadingCard lines={8} />, ssr: false },
);

const WriteOffSummaryChart = dynamic(
  () =>
    import("@/components/expiry/write-off-summary-chart").then((m) => ({
      default: m.WriteOffSummaryChart,
    })),
  { loading: () => <LoadingCard lines={4} />, ssr: false },
);

export default function ExpiryPage() {
  return (
    <DashboardShell
      activeHref="/expiry"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Operations" },
        { label: "Expiry" },
      ]}
    >
      <div className="page">
        <div>
          <h1 className="page-title">Expiry.</h1>
          <p className="page-sub">
            Near-expiry inventory, expired batches, and write-off exposure
            across every branch.
          </p>
        </div>

        <FilterBar />

        <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
          <ExpiryCalendar />
          <WriteOffSummaryChart />
        </div>

        <div style={{ marginTop: 24 }}>
          <NearExpiryList />
        </div>

        <div style={{ marginTop: 24 }}>
          <ExpiredStockTable />
        </div>
      </div>
    </DashboardShell>
  );
}
