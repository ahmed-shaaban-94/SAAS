"use client";

import { useState } from "react";
import { useProductHierarchy } from "@/hooks/use-product-hierarchy";
import { useFilters } from "@/contexts/filter-context";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { formatCurrency, formatNumber } from "@/lib/formatters";
import { ChevronRight, ChevronDown, Folder, Package } from "lucide-react";
import { cn } from "@/lib/utils";

export function ProductHierarchyView() {
  const { filters } = useFilters();
  const { data, isLoading } = useProductHierarchy(filters);
  const [expandedCats, setExpandedCats] = useState<Set<string>>(new Set());
  const [expandedBrands, setExpandedBrands] = useState<Set<string>>(new Set());

  if (isLoading) return <LoadingCard lines={10} className="h-96" />;
  if (!data?.categories?.length)
    return <EmptyState title="No product hierarchy data" />;

  const toggleCat = (cat: string) => {
    setExpandedCats((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  };

  const toggleBrand = (key: string) => {
    setExpandedBrands((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <div className="rounded-xl border border-border bg-card">
      {data.categories.map((cat) => {
        const catExpanded = expandedCats.has(cat.category);
        return (
          <div key={cat.category} className="border-b border-border last:border-b-0">
            {/* Category row */}
            <button
              onClick={() => toggleCat(cat.category)}
              className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-accent/5"
            >
              {catExpanded ? (
                <ChevronDown className="h-4 w-4 text-accent" />
              ) : (
                <ChevronRight className="h-4 w-4 text-text-secondary" />
              )}
              <Folder className="h-4 w-4 text-accent" />
              <span className="flex-1 text-sm font-semibold text-text-primary">
                {cat.category}
              </span>
              <span className="text-sm font-medium text-text-secondary">
                {formatCurrency(cat.total_net_amount)}
              </span>
            </button>

            {/* Brands (only render when expanded) */}
            {catExpanded &&
              cat.brands.map((brand) => {
                const brandKey = `${cat.category}::${brand.brand}`;
                const brandExpanded = expandedBrands.has(brandKey);
                return (
                  <div key={brandKey}>
                    <button
                      onClick={() => toggleBrand(brandKey)}
                      className="flex w-full items-center gap-3 py-2.5 pl-10 pr-4 text-left transition-colors hover:bg-accent/5"
                    >
                      {brandExpanded ? (
                        <ChevronDown className="h-3.5 w-3.5 text-accent/70" />
                      ) : (
                        <ChevronRight className="h-3.5 w-3.5 text-text-secondary" />
                      )}
                      <span className="flex-1 text-sm text-text-primary">
                        {brand.brand}
                      </span>
                      <span className="text-xs text-text-secondary">
                        {formatCurrency(brand.total_net_amount)}
                      </span>
                    </button>

                    {/* Products (only render when expanded) */}
                    {brandExpanded &&
                      brand.products.map((product) => (
                        <div
                          key={product.product_key}
                          className="flex items-center gap-3 py-2 pl-[4.5rem] pr-4"
                        >
                          <Package className="h-3.5 w-3.5 text-text-secondary/50" />
                          <span className="flex-1 truncate text-xs text-text-secondary">
                            {product.drug_name}
                          </span>
                          <span className="text-xs text-text-secondary">
                            {formatNumber(product.transaction_count)} txn
                          </span>
                          <span className="min-w-[5rem] text-right text-xs font-medium text-text-primary">
                            {formatCurrency(product.total_net_amount)}
                          </span>
                        </div>
                      ))}
                  </div>
                );
              })}
          </div>
        );
      })}
    </div>
  );
}
