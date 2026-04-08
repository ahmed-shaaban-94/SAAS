"use client";

import { useState } from "react";
import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { FilterBar } from "@/components/filters/filter-bar";
import { ProductOverview } from "@/components/products/product-overview";
import { ProductHierarchyView } from "@/components/products/product-hierarchy";
import { ParetoChart } from "@/components/products/pareto-chart";
import { ABCSummary } from "@/components/products/abc-summary";
import { cn } from "@/lib/utils";
import { BarChart3, FolderTree } from "lucide-react";

const VIEWS = [
  { key: "ranking" as const, label: "Ranking", icon: BarChart3 },
  { key: "hierarchy" as const, label: "Category / Brand", icon: FolderTree },
];

export default function ProductsPage() {
  const [view, setView] = useState<"ranking" | "hierarchy">("ranking");

  return (
    <PageTransition>
      <Breadcrumbs />
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <Header
          title="Product Analytics"
          description="Top performing products by revenue"
        />
        <div className="flex gap-1 rounded-lg bg-background p-1 self-start">
          {VIEWS.map((v) => (
            <button
              key={v.key}
              onClick={() => setView(v.key)}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all",
                view === v.key
                  ? "bg-accent/20 text-accent"
                  : "text-text-secondary hover:text-text-primary",
              )}
            >
              <v.icon className="h-3.5 w-3.5" />
              {v.label}
            </button>
          ))}
        </div>
      </div>
      <FilterBar />
      {view === "ranking" ? <ProductOverview /> : <ProductHierarchyView />}

      {/* ABC / Pareto Section */}
      <div className="mt-10">
        <div className="flex items-center gap-2 mb-4">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-accent/10">
            <BarChart3 className="h-3.5 w-3.5 text-accent" />
          </div>
          <h2 className="text-[11px] font-semibold uppercase tracking-widest text-text-secondary">
            ABC / Pareto Analysis
          </h2>
          <div className="flex-1 section-divider" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 md:gap-6 lg:grid-cols-3">
          <div className="md:col-span-2">
            <ParetoChart />
          </div>
          <ABCSummary />
        </div>
      </div>
    </PageTransition>
  );
}
