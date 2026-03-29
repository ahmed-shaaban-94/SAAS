"use client";

import { useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";

type SortDirection = "asc" | "desc" | null;

interface Column<T> {
  key: string;
  label: string;
  align?: "left" | "right";
  sortable?: boolean;
  render: (item: T) => React.ReactNode;
  sortValue?: (item: T) => string | number;
}

interface SortableTableProps<T> {
  data: T[];
  columns: Column<T>[];
  keyExtractor: (item: T) => string | number;
  className?: string;
  emptyMessage?: string;
}

export function SortableTable<T>({
  data,
  columns,
  keyExtractor,
  className,
  emptyMessage = "No data available",
}: SortableTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDirection>(null);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      if (sortDir === "asc") setSortDir("desc");
      else if (sortDir === "desc") {
        setSortKey(null);
        setSortDir(null);
      }
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const sorted = useMemo(() => {
    if (!sortKey || !sortDir) return data;
    const col = columns.find((c) => c.key === sortKey);
    if (!col?.sortValue) return data;

    return [...data].sort((a, b) => {
      const va = col.sortValue?.(a) ?? "";
      const vb = col.sortValue?.(b) ?? "";
      const cmp =
        typeof va === "number" && typeof vb === "number"
          ? va - vb
          : String(va).localeCompare(String(vb));
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [data, sortKey, sortDir, columns]);

  function SortIcon({ colKey }: { colKey: string }) {
    if (sortKey !== colKey) return <ArrowUpDown className="h-3.5 w-3.5 opacity-40" />;
    if (sortDir === "asc") return <ArrowUp className="h-3.5 w-3.5" />;
    return <ArrowDown className="h-3.5 w-3.5" />;
  }

  if (data.length === 0) {
    return (
      <div className="py-12 text-center text-sm text-text-secondary">{emptyMessage}</div>
    );
  }

  return (
    <div className={cn("overflow-x-auto", className)}>
      <table className="w-full min-w-[500px] text-left text-sm">
        <thead>
          <tr className="border-b border-border text-text-secondary">
            {columns.map((col) => (
              <th
                key={col.key}
                className={cn(
                  "pb-3 pr-4 font-medium last:pr-0",
                  col.align === "right" && "text-right",
                  col.sortable !== false && "cursor-pointer select-none",
                )}
              >
                {col.sortable !== false ? (
                  <button
                    onClick={() => handleSort(col.key)}
                    className="inline-flex items-center gap-1 transition-colors hover:text-text-primary"
                    aria-label={`Sort by ${col.label}`}
                  >
                    {col.label}
                    <SortIcon colKey={col.key} />
                  </button>
                ) : (
                  col.label
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((item) => (
            <tr
              key={keyExtractor(item)}
              className="border-b border-divider transition-colors hover:bg-divider/50"
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={cn(
                    "py-3 pr-4 last:pr-0",
                    col.align === "right" && "text-right",
                  )}
                >
                  {col.render(item)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
