"use client";

import { useEffect, useRef, useState } from "react";
import { Search, Package } from "lucide-react";
import { usePosProducts } from "@/hooks/use-pos-products";
import { cn } from "@/lib/utils";
import type { PosProductResult } from "@/types/pos";
import { EmptyState } from "@/components/empty-state";

interface ProductSearchProps {
  siteCode: string;
  onSelect: (drug: PosProductResult) => void;
  className?: string;
}

function fmt(n: number): string {
  return n.toLocaleString("ar-EG", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function ProductSearch({ siteCode, onSelect, className }: ProductSearchProps) {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // Debounce — 300ms
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 300);
    return () => clearTimeout(timer);
  }, [query]);

  // F1 keyboard shortcut focuses search
  useEffect(() => {
    const handler = () => inputRef.current?.focus();
    window.addEventListener("pos:focus-search", handler);
    return () => window.removeEventListener("pos:focus-search", handler);
  }, []);

  const { products, isLoading } = usePosProducts({ query: debouncedQuery, siteCode });

  function handleSelect(drug: PosProductResult) {
    onSelect(drug);
    setQuery("");
    setDebouncedQuery("");
    inputRef.current?.focus();
  }

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {/* Search input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-secondary" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search drug… (F1)"
          aria-label="Search drug"
          className={cn(
            "w-full rounded-xl border border-border bg-surface py-3 ps-9 pe-4 text-sm",
            "text-text-primary placeholder:text-text-secondary",
            "focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent",
          )}
        />
        {isLoading && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          </div>
        )}
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto space-y-1">
        {products.length === 0 && debouncedQuery.length >= 2 && !isLoading && (
          <EmptyState
            title="No drugs found"
            description={`No results for "${debouncedQuery}". Try a different name or code.`}
          />
        )}
        {products.map((drug) => (
          <button
            key={drug.drug_code}
            type="button"
            onClick={() => handleSelect(drug)}
            className={cn(
              "w-full rounded-xl border border-border/50 bg-surface p-3 text-left",
              "hover:border-accent/40 hover:bg-accent/5 active:scale-[0.99]",
              "transition-all duration-100",
              drug.stock_available === 0 && "opacity-50",
            )}
            disabled={drug.stock_available === 0}
            aria-label={`Add ${drug.drug_name}`}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-text-primary">{drug.drug_name}</p>
                {drug.drug_brand && (
                  <p className="text-xs text-text-secondary">{drug.drug_brand}</p>
                )}
                <div className="mt-1 flex items-center gap-2">
                  <span
                    className={cn(
                      "text-xs",
                      drug.stock_available > 20
                        ? "text-green-400"
                        : drug.stock_available > 0
                          ? "text-amber-400"
                          : "text-destructive",
                    )}
                  >
                    Stock: {drug.stock_available}
                  </span>
                  {drug.is_controlled && (
                    <span className="rounded bg-amber-500/20 px-1 py-0.5 text-[10px] font-bold text-amber-400">
                      CTRL
                    </span>
                  )}
                </div>
              </div>
              <span className="flex-shrink-0 text-sm font-semibold tabular-nums text-accent">
                EGP {fmt(drug.unit_price)}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
