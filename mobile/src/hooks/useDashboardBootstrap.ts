import { useEffect, useState } from "react";

import { ApiError, fetchHealth, fetchSummary } from "../api/client";
import type { HealthStatus, KPISummary } from "../types/api";

type SummaryState = "idle" | "ready" | "auth_required" | "error";

interface DashboardBootstrapState {
  health: HealthStatus | null;
  summary: KPISummary | null;
  healthError: string | null;
  summaryError: string | null;
  summaryState: SummaryState;
  loading: boolean;
  refreshing: boolean;
  lastUpdated: string | null;
  refresh: () => Promise<void>;
}

export function useDashboardBootstrap(): DashboardBootstrapState {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [summary, setSummary] = useState<KPISummary | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [summaryState, setSummaryState] = useState<SummaryState>("idle");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  async function refresh() {
    setRefreshing(true);
    try {
      const [healthResult, summaryResult] = await Promise.allSettled([
        fetchHealth(),
        fetchSummary(),
      ]);

      if (healthResult.status === "fulfilled") {
        setHealth(healthResult.value);
        setHealthError(null);
      } else {
        setHealth(null);
        setHealthError(extractMessage(healthResult.reason, "Health check failed."));
      }

      if (summaryResult.status === "fulfilled") {
        setSummary(summaryResult.value);
        setSummaryError(null);
        setSummaryState("ready");
      } else {
        setSummary(null);
        if (summaryResult.reason instanceof ApiError && summaryResult.reason.status === 401) {
          setSummaryState("auth_required");
          setSummaryError(
            "Analytics summary needs auth. Add mobile auth or a dev-only EXPO_PUBLIC_API_KEY.",
          );
        } else {
          setSummaryState("error");
          setSummaryError(extractMessage(summaryResult.reason, "Summary request failed."));
        }
      }

      setLastUpdated(new Date().toISOString());
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return {
    health,
    summary,
    healthError,
    summaryError,
    summaryState,
    loading,
    refreshing,
    lastUpdated,
    refresh,
  };
}

function extractMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}
