"use client";

import { useState } from "react";
import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { FilterBar } from "@/components/filters/filter-bar";
import { ProductOverview } from "@/components/products/product-overview";
import { ProductHierarchyView } from "@/components/products/product-hierarchy";
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
      <div className="flex items-start justify-between">
        <Header
          title="Product Analytics"
          description="Top performing products by revenue"
        />
        <div className="flex gap-1 rounded-lg bg-background p-1">
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
    </PageTransition>
  );
}
