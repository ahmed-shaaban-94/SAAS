"use client";

import dynamic from "next/dynamic";
import { LoadingCard } from "@/components/loading-card";
import { FilterBar } from "@/components/filters/filter-bar";
import { InventoryOverview } from "@/components/inventory/inventory-overview";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { Header } from "@/components/layout/header";
import { PageTransition } from "@/components/layout/page-transition";
import { OpsSuiteNav } from "@/components/shared/ops-suite-nav";

const StockLevelTable = dynamic(
  () => import("@/components/inventory/stock-level-table").then((module) => ({ default: module.StockLevelTable })),
  { loading: () => <LoadingCard lines={8} />, ssr: false },
);

const StockMovementChart = dynamic(
  () => import("@/components/inventory/stock-movement-chart").then((module) => ({ default: module.StockMovementChart })),
  { loading: () => <LoadingCard lines={4} />, ssr: false },
);

const ReorderAlertsList = dynamic(
  () => import("@/components/inventory/reorder-alerts-list").then((module) => ({ default: module.ReorderAlertsList })),
  { loading: () => <LoadingCard lines={4} />, ssr: false },
);

export default function InventoryPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Inventory Management"
        description="Stock levels, movement activity, and reorder risk across operations."
      />
      <FilterBar />
      <OpsSuiteNav />
      <InventoryOverview />
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <StockMovementChart />
        <ReorderAlertsList />
      </div>
      <div className="mt-6">
        <StockLevelTable />
      </div>
    </PageTransition>
  );
}
