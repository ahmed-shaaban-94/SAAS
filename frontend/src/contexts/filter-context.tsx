"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  type ReactNode,
} from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { subDays, format } from "date-fns";
import { useDateRange } from "@/hooks/use-date-range";
import type { FilterParams } from "@/types/filters";

interface FilterContextValue {
  filters: FilterParams;
  setFilters: (filters: FilterParams) => void;
  updateFilter: {
    (updates: Partial<FilterParams>): void;
    (key: keyof FilterParams, value: string | number | undefined): void;
  };
  clearFilters: () => void;
}

const FilterContext = createContext<FilterContextValue | null>(null);

export function FilterProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { data: dateRange } = useDateRange();

  const STORAGE_KEY = "datapulse:filters";
  const hydratedRef = useRef(false);

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
    if (siteKey && !isNaN(Number(siteKey))) params.site_key = Number(siteKey);
    if (staffKey && !isNaN(Number(staffKey))) params.staff_key = Number(staffKey);
    if (limit && !isNaN(Number(limit))) params.limit = Number(limit);

    return params;
  }, [searchParams]);

  // Hydrate from sessionStorage when URL has no filter params
  useEffect(() => {
    if (hydratedRef.current) return;
    hydratedRef.current = true;

    const hasUrlFilters = searchParams.toString().length > 0;
    if (hasUrlFilters) return;

    try {
      const stored = sessionStorage.getItem(STORAGE_KEY);
      if (stored) {
        const saved: FilterParams = JSON.parse(stored);
        if (Object.keys(saved).length > 0) {
          const params = new URLSearchParams();
          for (const [key, value] of Object.entries(saved)) {
            if (value !== undefined && value !== null) {
              params.set(key, String(value));
            }
          }
          router.push(`${pathname}?${params.toString()}`);
          return;
        }
      }
    } catch {
      // Ignore corrupted sessionStorage
    }

    // Default to Last 30 days from the latest date in the database
    if (!dateRange?.max_date) return; // Wait for API to load
    const anchor = new Date(dateRange.max_date + "T00:00:00");
    const params = new URLSearchParams();
    params.set("start_date", format(subDays(anchor, 30), "yyyy-MM-dd"));
    params.set("end_date", format(anchor, "yyyy-MM-dd"));
    router.push(`${pathname}?${params.toString()}`);
  }, [dateRange?.max_date]); // eslint-disable-line react-hooks/exhaustive-deps

  // Persist filters to sessionStorage on every change
  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
    } catch {
      // Ignore quota errors
    }
  }, [filters]);

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
    (
      keyOrUpdates: keyof FilterParams | Partial<FilterParams>,
      value?: string | number | undefined,
    ) => {
      const params = new URLSearchParams(searchParams.toString());

      // Overload: single key-value pair (backward compatible)
      if (typeof keyOrUpdates === "string") {
        if (value === undefined) {
          params.delete(keyOrUpdates);
        } else {
          params.set(keyOrUpdates, String(value));
        }
      } else {
        // Overload: partial object — batch multiple updates in one navigation
        Object.entries(keyOrUpdates).forEach(([k, v]) => {
          if (v === undefined || v === null || v === "") {
            params.delete(k);
          } else {
            params.set(k, String(v));
          }
        });
      }

      router.push(`${pathname}?${params.toString()}`);
    },
    [searchParams, router, pathname],
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
