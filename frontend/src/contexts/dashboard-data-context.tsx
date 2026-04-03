"use client";

import { createContext, useContext, type ReactNode } from "react";
import { useDashboard, type DashboardData } from "@/hooks/use-dashboard";
import { useFilters } from "@/contexts/filter-context";

interface DashboardDataContextValue {
  data: DashboardData | undefined;
  error: Error | undefined;
  isLoading: boolean;
}

const DashboardDataContext = createContext<DashboardDataContextValue | null>(
  null,
);

export function DashboardDataProvider({ children }: { children: ReactNode }) {
  const { filters } = useFilters();
  const { data, error, isLoading } = useDashboard(filters ?? undefined);

  return (
    <DashboardDataContext.Provider value={{ data, error, isLoading }}>
      {children}
    </DashboardDataContext.Provider>
  );
}

/**
 * Consume the composite dashboard data fetched by DashboardDataProvider.
 * Must be used inside <DashboardDataProvider>.
 */
export function useDashboardData(): DashboardDataContextValue {
  const ctx = useContext(DashboardDataContext);
  if (!ctx) {
    throw new Error(
      "useDashboardData must be used within a <DashboardDataProvider>",
    );
  }
  return ctx;
}
