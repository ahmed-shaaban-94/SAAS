"use client";

import { useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { ExploreResults } from "@/components/explore/explore-results";
import { FieldPicker } from "@/components/explore/field-picker";
import { useExploreModels } from "@/hooks/use-explore-models";
import { Play, Database } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ExploreQueryRequest, ExploreResult, ExploreModel } from "@/types/api";

/**
 * Standalone embed page — rendered inside an iframe.
 * No sidebar, no auth prompt, no navigation.
 * Uses embed token for API authentication.
 */
export default function EmbedPage() {
  const params = useParams();
  const token = params.token as string;

  const { data: catalog, isLoading: catalogLoading } = useExploreModels();
  const [selectedModel, setSelectedModel] = useState("");
  const [selectedDimensions, setSelectedDimensions] = useState<string[]>([]);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([]);
  const [result, setResult] = useState<ExploreResult | null>(null);
  const [queryLoading, setQueryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const model = catalog?.models.find((m: ExploreModel) => m.name === selectedModel);

  const handleRun = useCallback(async () => {
    if (!selectedModel || (selectedDimensions.length === 0 && selectedMetrics.length === 0)) return;

    setQueryLoading(true);
    setError(null);

    const query: ExploreQueryRequest = {
      model: selectedModel,
      dimensions: selectedDimensions,
      metrics: selectedMetrics,
      filters: [],
      sorts: [],
      limit: 500,
    };

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "";
      const res = await fetch(`${apiBase}/api/v1/embed/${token}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(query),
      });

      if (!res.ok) {
        const body = await res.text();
        throw new Error(`API error ${res.status}: ${body}`);
      }

      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setQueryLoading(false);
    }
  }, [token, selectedModel, selectedDimensions, selectedMetrics]);

  const canRun = selectedModel && (selectedDimensions.length > 0 || selectedMetrics.length > 0);

  return (
    <div className="min-h-screen bg-page text-text-primary p-4">
      {/* Minimal header */}
      <div className="mb-4 flex items-center gap-2">
        <Database className="h-5 w-5 text-accent" />
        <h1 className="text-lg font-semibold">DataPulse Explore</h1>
        <span className="ml-auto rounded-full bg-accent/10 px-2 py-0.5 text-xs text-accent">
          Embedded
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[240px_1fr]">
        {/* Left: model + field picker */}
        <div className="space-y-3">
          <select
            value={selectedModel}
            onChange={(e) => {
              setSelectedModel(e.target.value);
              setSelectedDimensions([]);
              setSelectedMetrics([]);
              setResult(null);
            }}
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
          >
            <option value="">Select model...</option>
            {catalog?.models.map((m: ExploreModel) => (
              <option key={m.name} value={m.name}>
                {m.label || m.name}
              </option>
            ))}
          </select>

          {model && (
            <FieldPicker
              model={model}
              selectedDimensions={selectedDimensions}
              selectedMetrics={selectedMetrics}
              onToggleDimension={(n) =>
                setSelectedDimensions((p) =>
                  p.includes(n) ? p.filter((d) => d !== n) : [...p, n],
                )
              }
              onToggleMetric={(n) =>
                setSelectedMetrics((p) =>
                  p.includes(n) ? p.filter((m) => m !== n) : [...p, n],
                )
              }
            />
          )}

          <button
            onClick={handleRun}
            disabled={!canRun || queryLoading}
            className={cn(
              "flex w-full items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium",
              canRun && !queryLoading
                ? "bg-accent text-white hover:bg-accent/90"
                : "bg-divider text-text-secondary cursor-not-allowed",
            )}
          >
            <Play className="h-4 w-4" />
            {queryLoading ? "Running..." : "Run Query"}
          </button>
        </div>

        {/* Right: results */}
        <div>
          {error && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-4 text-sm text-red-400">
              {error}
            </div>
          )}
          {result && <ExploreResults result={result} />}
          {!result && !error && !queryLoading && (
            <div className="flex items-center justify-center h-64 text-text-secondary text-sm">
              Select fields and run a query
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
