"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useFilters } from "@/contexts/filter-context";
import { EmptyState } from "@/components/empty-state";
import { ErrorRetry } from "@/components/error-retry";
import { LoadingCard } from "@/components/loading-card";
import { Button } from "@/components/ui/button";
import { SortableTable } from "@/components/shared/sortable-table";
import { useStockLevels } from "@/hooks/use-stock-levels";
import { formatDateLabel } from "@/lib/date-utils";
import { formatNumber } from "@/lib/formatters";

const PAGE_SIZE = 10;

export function StockLevelTable() {
  const { filters } = useFilters();
  const { data, error, isLoading, mutate } = useStockLevels(filters);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    const items = data ?? [];
    const search = query.trim().toLowerCase();

    if (!search) return items;

    return items.filter((item) =>
      [item.drug_code, item.drug_name, item.drug_brand, item.site_code, item.site_name]
        .join(" ")
        .toLowerCase()
        .includes(search),
    );
  }, [data, query]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const paged = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  if (isLoading) return <LoadingCard lines={8} className="h-[28rem]" />;
  if (error) {
    return (
      <ErrorRetry
        title="Failed to load stock levels"
        description="The current stock table could not be loaded."
        onRetry={() => mutate()}
      />
    );
  }
  if (!data?.length) {
    return (
      <EmptyState
        title="No stock levels available"
        description="Inventory stock levels will appear here when data is available."
      />
    );
  }

  return (
    <section className="viz-panel rounded-[1.75rem] p-5">
      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
            Stock Levels
          </p>
          <h3 className="mt-2 text-2xl font-bold tracking-tight text-text-primary">
            {formatNumber(filtered.length)} rows
          </h3>
        </div>
        <input
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setPage(1);
          }}
          placeholder="Search by drug, brand, or site"
          className="h-11 w-full rounded-2xl border border-border bg-page px-4 text-sm text-text-primary outline-none transition-colors focus:border-accent focus:ring-1 focus:ring-accent lg:max-w-sm"
        />
      </div>

      <SortableTable
        data={paged}
        keyExtractor={(item) => `${item.product_key}-${item.site_key}`}
        columns={[
          {
            key: "drug_name",
            label: "Drug",
            sortValue: (item) => item.drug_name,
            render: (item) => (
              <div>
                <Link
                  href={`/inventory/${item.drug_code}`}
                  className="font-semibold text-text-primary transition-colors hover:text-accent"
                >
                  {item.drug_name}
                </Link>
                <p className="text-xs text-text-secondary">{item.drug_code}</p>
              </div>
            ),
          },
          {
            key: "brand",
            label: "Brand",
            sortValue: (item) => item.drug_brand,
            render: (item) => <span className="text-text-secondary">{item.drug_brand}</span>,
          },
          {
            key: "site",
            label: "Site",
            sortValue: (item) => item.site_name,
            render: (item) => (
              <div>
                <p className="font-medium text-text-primary">{item.site_name}</p>
                <p className="text-xs text-text-secondary">{item.site_code}</p>
              </div>
            ),
          },
          {
            key: "current_quantity",
            label: "On Hand",
            align: "right",
            sortValue: (item) => item.current_quantity,
            render: (item) => <span className="font-semibold text-text-primary">{formatNumber(item.current_quantity)}</span>,
          },
          {
            key: "total_received",
            label: "Received",
            align: "right",
            sortValue: (item) => item.total_received,
            render: (item) => <span className="text-text-secondary">{formatNumber(item.total_received)}</span>,
          },
          {
            key: "last_movement_date",
            label: "Last Movement",
            sortValue: (item) => item.last_movement_date ?? "",
            render: (item) => (
              <span className="text-text-secondary">
                {item.last_movement_date ? formatDateLabel(item.last_movement_date) : "No movements"}
              </span>
            ),
          },
        ]}
      />

      <div className="mt-4 flex items-center justify-between">
        <p className="text-sm text-text-secondary">
          Showing {formatNumber((currentPage - 1) * PAGE_SIZE + 1)}-
          {formatNumber(Math.min(currentPage * PAGE_SIZE, filtered.length))} of {formatNumber(filtered.length)}
        </p>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((value) => Math.max(1, value - 1))}
            disabled={currentPage === 1}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((value) => Math.min(pageCount, value + 1))}
            disabled={currentPage === pageCount}
          >
            Next
          </Button>
        </div>
      </div>
    </section>
  );
}
