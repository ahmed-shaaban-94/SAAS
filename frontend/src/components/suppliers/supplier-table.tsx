"use client";

import { useState } from "react";
import { Search } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SupplierInfo } from "@/types/suppliers";

interface SupplierTableProps {
  suppliers: SupplierInfo[];
}

export function SupplierTable({ suppliers }: SupplierTableProps) {
  const [query, setQuery] = useState("");
  const [activeOnly, setActiveOnly] = useState(false);

  const filtered = suppliers.filter((s) => {
    const matchesQuery =
      query === "" ||
      s.supplier_name.toLowerCase().includes(query.toLowerCase()) ||
      s.supplier_code.toLowerCase().includes(query.toLowerCase());
    const matchesActive = !activeOnly || s.is_active;
    return matchesQuery && matchesActive;
  });

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-secondary" />
          <input
            type="text"
            placeholder="Search suppliers…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full rounded-lg border border-border bg-muted pl-9 pr-4 py-2 text-sm text-text-primary focus:border-accent focus:outline-none"
          />
        </div>
        <label className="flex cursor-pointer items-center gap-2 text-sm text-text-secondary">
          <input
            type="checkbox"
            checked={activeOnly}
            onChange={(e) => setActiveOnly(e.target.checked)}
            className="rounded"
          />
          Active only
        </label>
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border/70 py-12 text-center text-sm text-muted-foreground">
          No suppliers found.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/40">
                <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
                  Code
                </th>
                <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
                  Name
                </th>
                <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
                  Contact
                </th>
                <th className="px-4 py-3 text-center text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
                  Lead (days)
                </th>
                <th className="px-4 py-3 text-center text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
                  Terms (days)
                </th>
                <th className="px-4 py-3 text-center text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
                  Status
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => (
                <tr
                  key={s.supplier_code}
                  className="border-b border-border/50 last:border-0 hover:bg-accent/5"
                >
                  <td className="px-4 py-3 font-mono text-xs text-text-secondary">
                    {s.supplier_code}
                  </td>
                  <td className="px-4 py-3 font-medium text-text-primary">
                    {s.supplier_name}
                  </td>
                  <td className="px-4 py-3 text-text-secondary">
                    {s.contact_name && <p>{s.contact_name}</p>}
                    {s.contact_email && (
                      <p className="text-xs text-accent">{s.contact_email}</p>
                    )}
                    {s.contact_phone && (
                      <p className="text-xs">{s.contact_phone}</p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">{s.lead_time_days}</td>
                  <td className="px-4 py-3 text-center">{s.payment_terms_days}</td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={cn(
                        "rounded-full px-2.5 py-1 text-[11px] font-semibold",
                        s.is_active
                          ? "bg-green-500/15 text-green-400"
                          : "bg-muted text-muted-foreground",
                      )}
                    >
                      {s.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
