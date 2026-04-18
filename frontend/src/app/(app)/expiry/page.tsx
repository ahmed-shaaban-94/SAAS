"use client";

import dynamic from "next/dynamic";
import { LoadingCard } from "@/components/loading-card";
import { FilterBar } from "@/components/filters/filter-bar";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { Header } from "@/components/layout/header";
import { PageTransition } from "@/components/layout/page-transition";
import { OpsSuiteNav } from "@/components/shared/ops-suite-nav";

const ExpiryCalendar = dynamic(
  () => import("@/components/expiry/expiry-calendar").then((module) => ({ default: module.ExpiryCalendar })),
  { loading: () => <LoadingCard lines={8} />, ssr: false },
);

const NearExpiryList = dynamic(
  () => import("@/components/expiry/near-expiry-list").then((module) => ({ default: module.NearExpiryList })),
  { loading: () => <LoadingCard lines={6} />, ssr: false },
);

const ExpiredStockTable = dynamic(
  () => import("@/components/expiry/expired-stock-table").then((module) => ({ default: module.ExpiredStockTable })),
  { loading: () => <LoadingCard lines={8} />, ssr: false },
);

const WriteOffSummaryChart = dynamic(
  () => import("@/components/expiry/write-off-summary-chart").then((module) => ({ default: module.WriteOffSummaryChart })),
  { loading: () => <LoadingCard lines={4} />, ssr: false },
);

export default function ExpiryPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Expiry Tracking"
        description="Monitor near-expiry inventory, expired batches, and write-off exposure."
      />
      <FilterBar />
      <OpsSuiteNav />

      <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
        <ExpiryCalendar />
        <WriteOffSummaryChart />
      </div>

      <div className="mt-6">
        <NearExpiryList />
      </div>

      <div className="mt-6">
        <ExpiredStockTable />
      </div>
    </PageTransition>
  );
}
