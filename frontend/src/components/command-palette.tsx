"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Search, ArrowRight, Package, Users, UserCog, FileText, Loader2 } from "lucide-react";
import { NAV_ITEMS } from "@/lib/constants";
import { useSearch, type SearchResult } from "@/hooks/use-search";

interface FlatResult {
  id: string;
  label: string;
  subtitle?: string;
  href: string;
  type: "page" | "product" | "customer" | "staff";
}

const TYPE_ICONS = {
  page: FileText,
  product: Package,
  customer: Users,
  staff: UserCog,
} as const;

const TYPE_LABELS = {
  page: "Pages",
  product: "Products",
  customer: "Customers",
  staff: "Staff",
} as const;

function buildHref(item: SearchResult): string {
  switch (item.type) {
    case "page": return item.path ?? "/dashboard";
    case "product": return `/products/${item.key}`;
    case "customer": return `/customers/${item.key}`;
    case "staff": return `/staff/${item.key}`;
  }
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const { data: searchData, isLoading: searching } = useSearch(open ? query : "");

  // Flatten results into a single list with section headers
  const flatResults = useMemo<FlatResult[]>(() => {
    // Short query → nav-only
    if (query.trim().length < 2) {
      const q = query.toLowerCase();
      return NAV_ITEMS
        .filter((item) => !q || item.label.toLowerCase().includes(q))
        .map((item) => ({
          id: `page:${item.href}`,
          label: item.label,
          href: item.href,
          type: "page" as const,
        }));
    }

    if (!searchData) return [];

    const results: FlatResult[] = [];
    const addSection = (items: SearchResult[]) => {
      for (const item of items) {
        results.push({
          id: `${item.type}:${item.key ?? item.path ?? item.name}`,
          label: item.name,
          subtitle: item.subtitle,
          href: buildHref(item),
          type: item.type,
        });
      }
    };

    addSection(searchData.pages);
    addSection(searchData.products);
    addSection(searchData.customers);
    addSection(searchData.staff);

    return results;
  }, [query, searchData]);

  // Group results by type for section headers
  const groupedResults = useMemo(() => {
    const groups: { type: string; label: string; items: { result: FlatResult; globalIndex: number }[] }[] = [];
    let currentType = "";
    let globalIdx = 0;

    for (const result of flatResults) {
      if (result.type !== currentType) {
        currentType = result.type;
        groups.push({ type: result.type, label: TYPE_LABELS[result.type], items: [] });
      }
      groups[groups.length - 1].items.push({ result, globalIndex: globalIdx });
      globalIdx++;
    }
    return groups;
  }, [flatResults]);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      setOpen((prev) => !prev);
    }
  }, []);

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  useEffect(() => {
    if (open) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const navigate = (href: string) => {
    router.push(href);
    setOpen(false);
  };

  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      setOpen(false);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, flatResults.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && flatResults[selectedIndex]) {
      navigate(flatResults[selectedIndex].href);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[20vh]">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={() => setOpen(false)}
      />
      <div className="relative w-full max-w-lg rounded-xl border border-border bg-card shadow-2xl">
        {/* Search input */}
        <div className="flex items-center gap-3 border-b border-border px-4 py-3">
          {searching ? (
            <Loader2 className="h-5 w-5 animate-spin text-text-secondary" />
          ) : (
            <Search className="h-5 w-5 text-text-secondary" />
          )}
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelectedIndex(0); }}
            onKeyDown={handleInputKeyDown}
            placeholder="Search pages, products, customers, staff..."
            className="flex-1 bg-transparent text-sm text-text-primary placeholder-text-secondary outline-none"
          />
          <kbd className="hidden rounded border border-border px-1.5 py-0.5 text-[10px] text-text-secondary sm:inline">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-80 overflow-y-auto p-2">
          {flatResults.length === 0 && !searching ? (
            <p className="py-6 text-center text-sm text-text-secondary">
              {query.trim().length > 0 ? "No results found" : "Start typing to search..."}
            </p>
          ) : (
            groupedResults.map((group) => (
              <div key={group.type}>
                {query.trim().length >= 2 && (
                  <p className="px-3 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
                    {group.label}
                  </p>
                )}
                {group.items.map(({ result, globalIndex }) => {
                  const Icon = TYPE_ICONS[result.type];
                  return (
                    <button
                      key={result.id}
                      onClick={() => navigate(result.href)}
                      className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-colors ${
                        globalIndex === selectedIndex
                          ? "bg-accent/10 text-accent"
                          : "text-text-primary hover:bg-divider"
                      }`}
                    >
                      <Icon className="h-4 w-4 shrink-0 text-text-secondary" />
                      <div className="min-w-0 flex-1">
                        <span className="block truncate">{result.label}</span>
                        {result.subtitle && (
                          <span className="block truncate text-xs text-text-secondary">
                            {result.subtitle}
                          </span>
                        )}
                      </div>
                      <ArrowRight className="h-4 w-4 shrink-0 opacity-40" />
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-border px-4 py-2 text-[10px] text-text-secondary">
          <span className="mr-3">↑↓ Navigate</span>
          <span className="mr-3">↵ Open</span>
          <span className="mr-3">ESC Close</span>
          <span>? Shortcuts</span>
        </div>
      </div>
    </div>
  );
}
