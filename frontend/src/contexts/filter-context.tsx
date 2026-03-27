"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  type ReactNode,
} from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import type { FilterParams } from "@/types/filters";

interface FilterContextValue {
  filters: FilterParams;
  setFilters: (filters: FilterParams) => void;
  updateFilter: (key: keyof FilterParams, value: string | number | undefined) => void;
  clearFilters: () => void;
}

const FilterContext = createContext<FilterContextValue | null>(null);

export function FilterProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const filters = useMemo<FilterParams>(() => {
    const params: FilterParams = {};
    const startDate = searchParams.get("start_date");
    const endDate = searchParams.get("end_date");
    const category = searchParams.get("category");
    const brand = searchParams.get("brand");
    const siteKey = searchParams.get("site_key");
    const staffKey = searchParams.get("staff_key");
    const limit = searchParams.get("limit");

    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    if (category) params.category = category;
    if (brand) params.brand = brand;
    if (siteKey) params.site_key = Number(siteKey);
    if (staffKey) params.staff_key = Number(staffKey);
    if (limit) params.limit = Number(limit);

    return params;
  }, [searchParams]);

  const setFilters = useCallback(
    (newFilters: FilterParams) => {
      const params = new URLSearchParams();
      for (const [key, value] of Object.entries(newFilters)) {
        if (value !== undefined && value !== null) {
          params.set(key, String(value));
        }
      }
      router.push(`${pathname}?${params.toString()}`);
    },
    [router, pathname],
  );

  const updateFilter = useCallback(
    (key: keyof FilterParams, value: string | number | undefined) => {
      const newFilters = { ...filters };
      if (value === undefined) {
        delete newFilters[key];
      } else {
        (newFilters as Record<string, unknown>)[key] = value;
      }
      setFilters(newFilters);
    },
    [filters, setFilters],
  );

  const clearFilters = useCallback(() => {
    router.push(pathname);
  }, [router, pathname]);

  const value = useMemo(
    () => ({ filters, setFilters, updateFilter, clearFilters }),
    [filters, setFilters, updateFilter, clearFilters],
  );

  return (
    <FilterContext.Provider value={value}>{children}</FilterContext.Provider>
  );
}

export function useFilters() {
  const ctx = useContext(FilterContext);
  if (!ctx) {
    throw new Error("useFilters must be used within a FilterProvider");
  }
  return ctx;
}
