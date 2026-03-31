"use client";

import { useState, useCallback } from "react";
import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { FieldPicker } from "@/components/explore/field-picker";
import { ExploreResults } from "@/components/explore/explore-results";
import { useExploreModels } from "@/hooks/use-explore-models";
import { useExploreQuery } from "@/hooks/use-explore-query";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { Play, RotateCcw, Database } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ExploreQueryRequest } from "@/types/api";

export default function ExplorePage() {
  const { data: catalog, isLoading: catalogLoading } = useExploreModels();
  const { data: result, error, isLoading: queryLoading, execute, reset } = useExploreQuery();

  const [selectedModel, setSelectedModel] = useState<string>("");
  const [selectedDimensions, setSelectedDimensions] = useState<string[]>([]);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([]);
  const [limit, setLimit] = useState(500);

  const model = catalog?.models.find((m) => m.name === selectedModel);

  const handleModelChange = useCallback((name: string) => {
    setSelectedModel(name);
    setSelectedDimensions([]);
    setSelectedMetrics([]);
    reset();
  }, [reset]);

  const toggleDimension = useCallback((name: string) => {
    setSelectedDimensions((prev) =>
      prev.includes(name) ? prev.filter((d) => d !== name) : [...prev, name],
    );
  }, []);

  const toggleMetric = useCallback((name: string) => {
    setSelectedMetrics((prev) =>
      prev.includes(name) ? prev.filter((m) => m !== name) : [...prev, name],
    );
  }, []);

  const handleRun = useCallback(async () => {
    if (!selectedModel || (selectedDimensions.length === 0 && selectedMetrics.length === 0)) return;

    const query: ExploreQueryRequest = {
      model: selectedModel,
      dimensions: selectedDimensions,
      metrics: selectedMetrics,
      filters: [],
      sorts: [],
      limit,
    };

    await execute(query);
  }, [selectedModel, selectedDimensions, selectedMetrics, limit, execute]);

  const canRun = selectedModel && (selectedDimensions.length > 0 || selectedMetrics.length > 0);

  if (catalogLoading) {
    return (
      <PageTransition>
        <Breadcrumbs />
        <Header title="Explore" description="Build custom queries from your data models" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          <LoadingCard />
          <LoadingCard />
          <LoadingCard />
        </div>
      </PageTransition>
    );
  }

  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Explore"
        description="Build custom queries from your dbt models — select dimensions and metrics, then run"
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
        {/* Left panel: model selector + field picker */}
        <div className="space-y-4">
          {/* Model selector */}
          <div className="rounded-xl border border-border bg-card p-4">
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-text-secondary">
              Model
            </label>
            <select
              value={selectedModel}
              onChange={(e) => handleModelChange(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none"
            >
              <option value="">Select a model...</option>
              {catalog?.models.map((m) => (
                <option key={m.name} value={m.name}>
                  {m.label || m.name}
                </option>
              ))}
            </select>
          </div>

          {/* Field picker */}
          {model && (
            <div className="rounded-xl border border-border bg-card p-4">
              <FieldPicker
                model={model}
                selectedDimensions={selectedDimensions}
                selectedMetrics={selectedMetrics}
                onToggleDimension={toggleDimension}
                onToggleMetric={toggleMetric}
              />
            </div>
          )}

          {/* Query controls */}
          {model && (
            <div className="rounded-xl border border-border bg-card p-4 space-y-3">
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-text-secondary">
                  Row Limit
                </label>
                <input
                  type="number"
                  min={1}
                  max={10000}
                  value={limit}
                  onChange={(e) => setLimit(Number(e.target.value))}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none"
                />
              </div>

              <button
                onClick={handleRun}
                disabled={!canRun || queryLoading}
                className={cn(
                  "flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all",
                  canRun && !queryLoading
                    ? "bg-accent text-white hover:bg-accent/90"
                    : "bg-divider text-text-secondary cursor-not-allowed",
                )}
              >
                <Play className="h-4 w-4" />
                {queryLoading ? "Running..." : "Run Query"}
              </button>

              {(result || error) && (
                <button
                  onClick={() => {
                    setSelectedDimensions([]);
                    setSelectedMetrics([]);
                    reset();
                  }}
                  className="flex w-full items-center justify-center gap-2 rounded-lg border border-border px-4 py-2 text-sm text-text-secondary hover:text-text-primary transition-colors"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  Reset
                </button>
              )}
            </div>
          )}
        </div>

        {/* Right panel: results */}
        <div>
          {!selectedModel && (
            <EmptyState
              title="No model selected"
              description="Select a model to start exploring your data"
            />
          )}

          {selectedModel && !result && !queryLoading && !error && (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/50 p-12 text-center">
              <Database className="mb-4 h-12 w-12 text-text-secondary/40" />
              <p className="text-sm text-text-secondary">
                Select dimensions and metrics, then click &quot;Run Query&quot;
              </p>
              {selectedDimensions.length > 0 && (
                <p className="mt-2 text-xs text-accent">
                  {selectedDimensions.length} dimension{selectedDimensions.length !== 1 ? "s" : ""},{" "}
                  {selectedMetrics.length} metric{selectedMetrics.length !== 1 ? "s" : ""} selected
                </p>
              )}
            </div>
          )}

          {queryLoading && (
            <div className="space-y-4">
              <LoadingCard />
              <LoadingCard />
            </div>
          )}

          {error && (
            <div className="rounded-xl border border-red-500/30 bg-red-500/5 p-6">
              <p className="text-sm font-medium text-red-400">Query failed</p>
              <p className="mt-1 text-xs text-red-400/70">{error.message}</p>
            </div>
          )}

          {result && <ExploreResults result={result} />}
        </div>
      </div>
    </PageTransition>
  );
}
