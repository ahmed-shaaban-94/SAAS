"use client";

import { useState, useCallback, useEffect } from "react";
import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { postAPI, fetchAPI } from "@/lib/api-client";
import { Play, ChevronRight, ChevronDown, Table, Columns } from "lucide-react";
import { cn } from "@/lib/utils";

interface SchemaColumn {
  column_name: string;
  data_type: string;
  is_nullable: boolean;
}

interface SchemaTable {
  table_name: string;
  columns: SchemaColumn[];
}

interface SQLResult {
  columns: string[];
  rows: (string | number | boolean | null)[][];
  row_count: number;
  truncated: boolean;
  duration_ms: number;
  sql: string;
}

export default function SQLLabPage() {
  const [sql, setSql] = useState("SELECT * FROM public_marts.fct_sales LIMIT 100");
  const [result, setResult] = useState<SQLResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [schemas, setSchemas] = useState<SchemaTable[]>([]);
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());

  // Load schema on mount
  useEffect(() => {
    fetchAPI<SchemaTable[]>("/api/v1/sql-lab/schemas")
      .then(setSchemas)
      .catch(() => {});
  }, []);

  const handleRun = useCallback(async () => {
    if (!sql.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await postAPI<SQLResult>("/api/v1/sql-lab/execute", {
        sql,
        row_limit: 1000,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  }, [sql]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        handleRun();
      }
    },
    [handleRun],
  );

  const toggleTable = (name: string) => {
    setExpandedTables((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="SQL Lab"
        description="Write SQL queries against your analytics warehouse"
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[220px_1fr]">
        {/* Schema browser */}
        <div className="rounded-xl border border-border bg-card p-3 max-h-[80vh] overflow-y-auto">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-text-secondary">
            Tables (public_marts)
          </h3>
          <div className="space-y-0.5">
            {schemas.map((table) => (
              <div key={table.table_name}>
                <button
                  onClick={() => toggleTable(table.table_name)}
                  className="flex w-full items-center gap-1.5 rounded-md px-2 py-1.5 text-sm text-text-secondary hover:bg-divider hover:text-text-primary transition-colors"
                >
                  {expandedTables.has(table.table_name) ? (
                    <ChevronDown className="h-3 w-3 flex-shrink-0" />
                  ) : (
                    <ChevronRight className="h-3 w-3 flex-shrink-0" />
                  )}
                  <Table className="h-3.5 w-3.5 flex-shrink-0 text-accent" />
                  <span className="truncate font-mono text-xs">{table.table_name}</span>
                </button>
                {expandedTables.has(table.table_name) && (
                  <div className="ml-6 space-y-0.5">
                    {table.columns.map((col) => (
                      <button
                        key={col.column_name}
                        onClick={() =>
                          setSql((prev) => prev + ` ${col.column_name}`)
                        }
                        className="flex w-full items-center gap-1.5 rounded px-2 py-1 text-xs text-text-secondary hover:bg-divider hover:text-text-primary"
                        title={`${col.data_type}${col.is_nullable ? " (nullable)" : ""}`}
                      >
                        <Columns className="h-3 w-3 flex-shrink-0" />
                        <span className="truncate font-mono">{col.column_name}</span>
                        <span className="ml-auto text-[10px] text-text-secondary/60">
                          {col.data_type}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Editor + Results */}
        <div className="space-y-4">
          {/* SQL Editor */}
          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="flex items-center justify-between border-b border-border px-4 py-2">
              <span className="text-xs font-semibold text-text-secondary">SQL Editor</span>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-text-secondary/60">Ctrl+Enter to run</span>
                <button
                  onClick={handleRun}
                  disabled={isLoading || !sql.trim()}
                  className={cn(
                    "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all",
                    !isLoading && sql.trim()
                      ? "bg-accent text-white hover:bg-accent/90"
                      : "bg-divider text-text-secondary cursor-not-allowed",
                  )}
                >
                  <Play className="h-3.5 w-3.5" />
                  {isLoading ? "Running..." : "Run"}
                </button>
              </div>
            </div>
            <textarea
              value={sql}
              onChange={(e) => setSql(e.target.value)}
              onKeyDown={handleKeyDown}
              spellCheck={false}
              className="w-full resize-y bg-background p-4 font-mono text-sm text-text-primary focus:outline-none min-h-[160px]"
              placeholder="SELECT * FROM public_marts.fct_sales LIMIT 100"
            />
          </div>

          {/* Error */}
          {error && (
            <div className="rounded-xl border border-red-500/30 bg-red-500/5 p-4">
              <p className="text-sm font-medium text-red-400">Query Error</p>
              <p className="mt-1 text-xs text-red-400/70 font-mono">{error}</p>
            </div>
          )}

          {/* Results */}
          {result && (
            <div className="space-y-2">
              <div className="flex items-center gap-4 text-xs text-text-secondary">
                <span>{result.row_count} rows</span>
                <span>{result.duration_ms}ms</span>
                {result.truncated && (
                  <span className="text-chart-amber">Results truncated</span>
                )}
              </div>
              <div className="overflow-x-auto rounded-xl border border-border">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-background">
                      {result.columns.map((col) => (
                        <th
                          key={col}
                          className="px-3 py-2 text-left text-xs font-medium text-text-secondary whitespace-nowrap"
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.rows.map((row, i) => (
                      <tr
                        key={i}
                        className="border-b border-border last:border-0 hover:bg-divider/50"
                      >
                        {row.map((cell, j) => (
                          <td
                            key={j}
                            className="px-3 py-1.5 text-xs text-text-primary font-mono whitespace-nowrap"
                          >
                            {cell === null ? (
                              <span className="text-text-secondary/40">NULL</span>
                            ) : typeof cell === "number" ? (
                              cell.toLocaleString()
                            ) : (
                              String(cell)
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </PageTransition>
  );
}
