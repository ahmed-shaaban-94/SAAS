import { useState } from "react";
import { API_BASE_URL } from "@/lib/constants";
import { getSession } from "next-auth/react";

export interface Adjustment {
  parameter: "price" | "volume" | "cost";
  change_type: "percentage";
  change_value: number;
}

export interface TimePoint {
  month: string;
  baseline: number;
  projected: number;
}

export interface ImpactSummary {
  baseline_total: number;
  projected_total: number;
  absolute_change: number;
  percentage_change: number;
}

export interface ScenarioResult {
  revenue_series: TimePoint[];
  margin_series: TimePoint[];
  revenue_impact: ImpactSummary;
  margin_impact: ImpactSummary;
}

export function useScenario() {
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const simulate = async (adjustments: Adjustment[], months: number) => {
    setLoading(true);
    setError(null);
    try {
      const session = await getSession();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (session?.accessToken)
        headers["Authorization"] = `Bearer ${session.accessToken}`;

      const res = await fetch(`${API_BASE_URL}/api/v1/scenarios/simulate`, {
        method: "POST",
        headers,
        body: JSON.stringify({ adjustments, months }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data: ScenarioResult = await res.json();
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setLoading(false);
    }
  };

  return { result, loading, error, simulate };
}
