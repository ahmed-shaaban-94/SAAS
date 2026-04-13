"use client";

import { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { fetchAPI, postAPI } from "@/lib/api-client";
import { LoadingCard } from "@/components/loading-card";
import { useToast } from "@/components/ui/toast";
import { FileText, Play, Printer } from "lucide-react";
import { cn } from "@/lib/utils";

interface ReportParam {
  name: string;
  label: string;
  param_type: "text" | "number" | "date" | "select";
  default: string | number | null;
  options: string[];
  required: boolean;
}

interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  parameters: ReportParam[];
}

interface RenderedSection {
  section_type: "text" | "query" | "kpi";
  title: string;
  text: string;
  columns: string[];
  rows: (string | number | boolean | null)[][];
  row_count: number;
  chart_type: string;
}

interface RenderedReport {
  template_id: string;
  template_name: string;
  parameters: Record<string, string | number>;
  sections: RenderedSection[];
}

export default function ReportsPage() {
  const { success, error: toastError, info } = useToast();
  const [templates, setTemplates] = useState<ReportTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<ReportTemplate | null>(null);
  const [paramValues, setParamValues] = useState<Record<string, string | number>>({});
  const [report, setReport] = useState<RenderedReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAPI<ReportTemplate[]>("/api/v1/reports")
      .then(setTemplates)
      .catch(() => {});
  }, []);

  const selectTemplate = useCallback((template: ReportTemplate) => {
    setSelectedTemplate(template);
    setReport(null);
    setError(null);
    const defaults: Record<string, string | number> = {};
    template.parameters.forEach((p) => {
      if (p.default !== null) defaults[p.name] = p.default;
    });
    setParamValues(defaults);
  }, []);

  const handleRender = useCallback(async () => {
    if (!selectedTemplate) return;
    setIsLoading(true);
    setError(null);
    try {
      const result = await postAPI<RenderedReport>(
        `/api/v1/reports/${selectedTemplate.id}/render`,
        { parameters: paramValues },
      );
      setReport(result);
      success(`Report "${selectedTemplate.name}" generated`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      toastError(`Failed to generate report: ${msg}`);
    } finally {
      setIsLoading(false);
    }
  }, [selectedTemplate, paramValues, success, toastError]);

  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Reports"
        description="Generate parameterized reports from templates"
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-[240px_1fr] md:gap-6 lg:grid-cols-[280px_1fr]">
        {/* Template list */}
        <div className="space-y-2">
          <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
            Templates
          </h3>
          {templates.map((t) => (
            <button
              key={t.id}
              onClick={() => selectTemplate(t)}
              className={cn(
                "flex w-full items-start gap-3 rounded-[1.35rem] border p-3 text-left transition-all",
                selectedTemplate?.id === t.id
                  ? "viz-panel border-accent/30 bg-accent/8"
                  : "viz-panel hover:border-accent/30",
              )}
            >
              <FileText className="mt-0.5 h-4 w-4 flex-shrink-0 text-accent" />
              <div>
                <p className="text-sm font-medium text-text-primary">{t.name}</p>
                <p className="text-xs text-text-secondary">{t.description}</p>
              </div>
            </button>
          ))}
        </div>

        {/* Report content */}
        <div>
          {!selectedTemplate && (
            <div className="viz-panel-soft flex flex-col items-center justify-center rounded-[1.75rem] border border-dashed border-border/70 p-12 text-center">
              <FileText className="mb-4 h-12 w-12 text-text-secondary/40" />
              <p className="text-sm text-text-secondary">Select a report template</p>
            </div>
          )}

          {selectedTemplate && (
            <div className="space-y-6">
              {/* Parameters form */}
              <div className="viz-panel rounded-[1.75rem] p-4">
                <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">Parameters</h3>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {selectedTemplate.parameters.map((param) => (
                    <div key={param.name}>
                      <label className="mb-1 block text-xs font-medium text-text-secondary">
                        {param.label}
                      </label>
                      {param.param_type === "select" ? (
                        <select
                          value={paramValues[param.name] ?? ""}
                          onChange={(e) =>
                            setParamValues((prev) => ({ ...prev, [param.name]: e.target.value }))
                          }
                          className="w-full rounded-xl border border-border/70 bg-background/60 px-3 py-2 text-sm"
                        >
                          {param.options.map((opt) => (
                            <option key={opt} value={opt}>
                              {opt}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type={param.param_type === "number" ? "number" : "text"}
                          value={paramValues[param.name] ?? ""}
                          onChange={(e) =>
                            setParamValues((prev) => ({
                              ...prev,
                              [param.name]:
                                param.param_type === "number"
                                  ? Number(e.target.value)
                                  : e.target.value,
                            }))
                          }
                          className="w-full rounded-xl border border-border/70 bg-background/60 px-3 py-2 text-sm"
                        />
                      )}
                    </div>
                  ))}
                </div>

                <div className="mt-4 flex gap-2">
                  <button
                    onClick={handleRender}
                    disabled={isLoading}
                    className={cn(
                      "flex items-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-semibold",
                      !isLoading
                        ? "bg-accent text-white hover:bg-accent/90"
                        : "bg-divider text-text-secondary cursor-not-allowed",
                    )}
                  >
                    <Play className="h-4 w-4" />
                    {isLoading ? "Generating..." : "Generate Report"}
                  </button>
                  {report && (
                    <button
                      onClick={() => { info("Printing report..."); window.print(); }}
                      className="viz-panel-soft flex items-center gap-2 rounded-2xl px-4 py-2.5 text-sm text-text-secondary hover:text-text-primary"
                    >
                      <Printer className="h-4 w-4" />
                      Print
                    </button>
                  )}
                </div>
              </div>

              {error && (
                <div className="viz-panel rounded-[1.5rem] border border-red-500/20 bg-red-500/8 p-4 text-sm text-red-400">
                  {error}
                </div>
              )}

              {isLoading && <LoadingCard />}

              {/* Rendered report sections */}
              {report && (
                <div className="space-y-6 print:space-y-4" id="report-content">
                  <h2 className="text-xl font-bold text-text-primary print:text-black">
                    {report.template_name}
                  </h2>

                  {report.sections.map((section, i) => (
                    <div key={i} className="viz-panel rounded-[1.5rem] p-4 print:border-gray-300">
                      {section.title && (
                        <h3 className="mb-3 text-sm font-semibold text-text-primary print:text-black">
                          {section.title}
                        </h3>
                      )}

                      {section.section_type === "text" && (
                        <p className="text-sm text-text-secondary print:text-gray-600">
                          {section.text}
                        </p>
                      )}

                      {(section.section_type === "query" || section.section_type === "kpi") &&
                        section.columns.length > 0 && (
                          <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                              <thead>
                                <tr className="border-b border-border">
                                  {section.columns.map((col) => (
                                    <th
                                      key={col}
                                      className="px-3 py-2 text-left text-xs font-medium text-text-secondary"
                                    >
                                      {col.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {section.rows.slice(0, 200).map((row, ri) => (
                                  <tr key={ri} className="border-b border-border last:border-0">
                                    {row.map((cell, ci) => (
                                      <td key={ci} className="px-3 py-2 text-text-primary">
                                        {typeof cell === "number"
                                          ? cell.toLocaleString("en-EG", { maximumFractionDigits: 2 })
                                          : cell ?? "—"}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                            <p className="mt-1 text-xs text-text-secondary">
                              {section.rows.length > 200
                                ? `Showing 200 of ${section.row_count} rows`
                                : `${section.row_count} rows`}
                            </p>
                          </div>
                        )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </PageTransition>
  );
}
