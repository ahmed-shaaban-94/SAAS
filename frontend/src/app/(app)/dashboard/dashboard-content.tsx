"use client";

import type { ReactNode } from "react";
import { DashboardDataProvider } from "@/contexts/dashboard-data-context";
import { CrosshairProvider } from "@/contexts/crosshair-context";

/**
 * Client boundary that wraps dashboard children in the composite data provider.
 * This fetches /api/v1/analytics/dashboard once and shares the data via context
 * instead of each child making its own API call.
 * CrosshairProvider syncs hover state across trend charts.
 */
export function DashboardContent({ children }: { children: ReactNode }) {
  return (
    <DashboardDataProvider>
      <CrosshairProvider>{children}</CrosshairProvider>
    </DashboardDataProvider>
  );
}
