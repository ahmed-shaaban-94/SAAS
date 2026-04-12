"use client";

import { useState, useCallback } from "react";
import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { TemplatePicker } from "@/components/custom-report/template-picker";
import { MeasureSelector } from "@/components/custom-report/measure-selector";
import { GroupingSelector } from "@/components/custom-report/grouping-selector";
import { ChartTypePicker } from "@/components/custom-report/chart-type-picker";
import { ReportResults } from "@/components/custom-report/report-results";
import { useExploreModels } from "@/hooks/use-explore-models";
import { useExploreQuery } from "@/hooks/use-explore-query";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { Play, RotateCcw, Sparkles, X } from "lucide-react";
import { DateRangePicker } from "@/components/filters/date-range-picker";
import { getDatePresets, formatDateParam } from "@/lib/date-utils";
import { cn } from "@/lib/utils";
import { ReportSummary } from "@/components/custom-report/report-summary";
import { RankingFilter } from "@/components/custom-report/ranking-filter";
import type { ReportTemplate, ChartType } from "@/components/custom-report/report-config";
import type { ExploreQueryRequest } from "@/types/api";

export default function CustomReportPage() {
  const { data: catalog, isLoading: catalogLoading } = useExploreModels();
  const {
    data: result,
    error,
    isLoading: queryLoading,
    execute,
    reset,
  } = useExploreQuery();

  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState("fct_sales");
  const [selectedDimensions, setSelectedDimensions] = useState<string[]>([]);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([]);
  const [chartType, setChartType] = useState<ChartType>("table");
  const [startDate, setStartDate] = useState<string | undefined>();
  const [endDate, setEndDate] = useState<string | undefined>();
  const [rankLimit, setRankLimit] = useState(0);
  const [sortField, setSortField] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  const datePresets = getDatePresets();

  const model = catalog?.models.find((m) => m.name === selectedModel);

  const handleTemplateSelect = useCallback(
    (template: ReportTemplate) => {
      setSelectedTemplate(template.id);
      setSelectedModel(template.model);
      setSelectedDimensions([...template.dimensions]);
      setSelectedMetrics([...template.metrics]);
      setChartType(template.chartType);
      setRankLimit(0);
      setSortField(null);
      setSortDirection("desc");
      reset();
    },
    [reset],
  );

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

  const handleGenerate = useCallback(async () => {
    if (selectedDimensions.length === 0 && selectedMetrics.length === 0) return;

    const filters: ExploreQueryRequest["filters"] = [];
    if (startDate) {
      filters.push({ field: "full_date", operator: "gte", value: startDate });
    }
    if (endDate) {
      filters.push({ field: "full_date", operator: "lte", value: endDate });
    }

    const query: ExploreQueryRequest = {
      model: selectedModel,
      dimensions: selectedDimensions,
      metrics: selectedMetrics,
      filters,
      sorts: sortField ? [{ field: sortField, direction: sortDirection }] : [],
      limit: rankLimit > 0 ? rankLimit : 500,
    };

    await execute(query);
  }, [selectedModel, selectedDimensions, selectedMetrics, startDate, endDate, sortField, sortDirection, rankLimit, execute]);

  const handleDateChange = useCallback(
    (start: string | undefined, end: string | undefined) => {
      setStartDate(start);
      setEndDate(end);
    },
    [],
  );

  const handlePreset = useCallback(
    (preset: { startDate: Date; endDate: Date }) => {
      setStartDate(formatDateParam(preset.startDate));
      setEndDate(formatDateParam(preset.endDate));
    },
    [],
  );

  const clearDates = useCallback(() => {
    setStartDate(undefined);
    setEndDate(undefined);
  }, []);

  const handleReset = useCallback(() => {
    setSelectedTemplate(null);
    setSelectedModel("fct_sales");
    setSelectedDimensions([]);
    setSelectedMetrics([]);
    setChartType("table");
    setRankLimit(0);
    setSortField(null);
    setSortDirection("desc");
    setStartDate(undefined);
    setEndDate(undefined);
    reset();
  }, [reset]);

  const canGenerate =
    selectedDimensions.length > 0 || selectedMetrics.length > 0;

  if (catalogLoading) {
    return (
      <PageTransition>
        <Breadcrumbs />
        <Header
          title="Custom Report"
          description="Build your own analysis"
        />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
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
        title="Custom Report"
        description="Build your own analysis -- pick a template or start from scratch"
      />

      <div className="space-y-6">
        {/* Templates */}
        <TemplatePicker
          selectedId={selectedTemplate}
          onSelect={handleTemplateSelect}
        />

        {/* Configuration Panel */}
        {model && (
          <div className="viz-panel rounded-[1.75rem] p-5 space-y-6">
            {/* Guided hint for From Scratch */}
            {selectedTemplate === "from-scratch" &&
              selectedMetrics.length === 0 &&
              selectedDimensions.length === 0 && (
                <div className="viz-panel-soft flex items-start gap-3 rounded-[1.25rem] border border-accent/20 p-4">
                  <Sparkles className="mt-0.5 h-5 w-5 flex-shrink-0 text-accent" />
                  <div>
                    <p className="text-sm font-medium text-text-primary">
                      Build your own report
                    </p>
                    <p className="mt-0.5 text-xs text-text-secondary">
                      Pick at least one metric below (e.g. Total Revenue) and a
                      grouping (e.g. Month or Product) to get started.
                    </p>
                  </div>
                </div>
              )}

            <MeasureSelector
              availableMetrics={model.metrics}
              selected={selectedMetrics}
              onToggle={toggleMetric}
            />

            <div className="border-t border-border" />

            <GroupingSelector
              availableDimensions={model.dimensions}
              selected={selectedDimensions}
              onToggle={toggleDimension}
            />

            <div className="border-t border-border" />

            <ChartTypePicker value={chartType} onChange={setChartType} />

            <div className="border-t border-border" />

            <RankingFilter
              selectedMetrics={selectedMetrics}
              rankLimit={rankLimit}
              sortField={sortField}
              sortDirection={sortDirection}
              onRankLimitChange={setRankLimit}
              onSortFieldChange={setSortField}
              onSortDirectionChange={setSortDirection}
            />
          </div>
        )}

        {/* Date Filter */}
        {model && (
          <div className="viz-panel rounded-[1.75rem] p-5 space-y-3">
            <h4 className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
              Date range{" "}
              <span className="font-normal normal-case tracking-normal text-text-secondary text-xs">
                (optional — defaults to all data)
              </span>
            </h4>

            <div className="flex flex-wrap items-center gap-2">
              {/* Quick presets */}
              {datePresets.map((p) => (
                <button
                  key={p.label}
                  onClick={() => handlePreset(p)}
                  className={cn(
                    "rounded-full px-3 py-1.5 text-xs font-medium transition-all",
                    startDate === formatDateParam(p.startDate) &&
                      endDate === formatDateParam(p.endDate)
                      ? "bg-accent text-white"
                      : "viz-panel-soft border border-border text-text-secondary hover:text-text-primary",
                  )}
                >
                  {p.label}
                </button>
              ))}

              {/* Calendar picker */}
              <DateRangePicker
                startDate={startDate}
                endDate={endDate}
                onRangeChange={handleDateChange}
              />

              {/* Clear dates */}
              {startDate && endDate && (
                <button
                  onClick={clearDates}
                  className="flex items-center gap-1 rounded-full border border-border px-2.5 py-1.5 text-xs text-text-secondary hover:text-text-primary hover:border-border-hover transition-colors"
                >
                  <X className="h-3 w-3" />
                  Clear
                </button>
              )}
            </div>
          </div>
        )}

        {/* Generate / Reset */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleGenerate}
            disabled={!canGenerate || queryLoading}
            className={cn(
              "flex items-center gap-2 rounded-2xl px-6 py-2.5 text-sm font-semibold transition-all",
              canGenerate && !queryLoading
                ? "bg-accent text-white hover:bg-accent/90"
                : "bg-divider text-text-secondary cursor-not-allowed",
            )}
          >
            <Play className="h-4 w-4" />
            {queryLoading ? "Generating..." : "Generate Report"}
          </button>

          {(result || error || selectedTemplate) && (
            <button
              onClick={handleReset}
              className="viz-panel-soft flex items-center gap-2 rounded-2xl px-4 py-2.5 text-sm text-text-secondary hover:text-text-primary transition-colors"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset
            </button>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="viz-panel rounded-[1.5rem] border border-red-500/20 bg-red-500/8 p-6">
            <p className="text-sm font-medium text-red-400">
              Report generation failed
            </p>
            <p className="mt-1 text-xs text-red-400/70">{error.message}</p>
          </div>
        )}

        {/* Summary KPIs + Results */}
        {result && (
          <>
            <ReportSummary result={result} />
            <ReportResults result={result} chartType={chartType} />
          </>
        )}

        {/* Empty state */}
        {!result && !queryLoading && !error && (
          <EmptyState
            title="No report generated yet"
            description="Pick a template or select measures and groupings above, then click Generate Report"
          />
        )}
      </div>
    </PageTransition>
  );
}
