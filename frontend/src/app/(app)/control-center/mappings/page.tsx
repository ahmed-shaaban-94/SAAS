"use client";

import { useState } from "react";
import { PageTransition } from "@/components/layout/page-transition";
import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { useMappings, createMapping, updateMapping, validateMapping, type MappingTemplate, type MappingColumn } from "@/hooks/use-mappings";
import { Plus, GitBranch, X, CheckCircle, XCircle } from "lucide-react";

function MappingForm({
  initial,
  onSaved,
  onCancel,
}: {
  initial: MappingTemplate | null;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const existingCols: MappingColumn[] = initial?.mapping?.columns ?? [];
  const [templateName, setTemplateName] = useState(initial?.template_name ?? "");
  const [sourceType, setSourceType] = useState(initial?.source_type ?? "file_upload");
  const [columns, setColumns] = useState<MappingColumn[]>(existingCols.length ? existingCols : [{ source: "", canonical: "", cast: "string" }]);
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validation, setValidation] = useState<{ ok: boolean; errors: { code: string; message: string }[]; warnings: { code: string; message: string }[] } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const CANONICAL_FIELDS = ["order_id", "customer_id", "product_id", "qty", "gross_amount", "order_date", "sku", "warehouse", "site_code", "name"];
  const CAST_TYPES = ["string", "integer", "numeric", "date", "timestamp", "boolean"];

  function setCol(idx: number, field: keyof MappingColumn, value: string) {
    setColumns((cols) => cols.map((c, i) => i === idx ? { ...c, [field]: value } : c));
  }

  function addCol() {
    setColumns((cols) => [...cols, { source: "", canonical: "", cast: "string" }]);
  }

  function removeCol(idx: number) {
    setColumns((cols) => cols.filter((_, i) => i !== idx));
  }

  async function handleValidate() {
    setValidating(true);
    setValidation(null);
    try {
      const result = await validateMapping({
        source_type: sourceType,
        columns,
        target_domain: "sales_orders",
      });
      setValidation(result);
    } catch {
      setError("Validation request failed");
    } finally {
      setValidating(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      if (initial) {
        await updateMapping(initial.id, { template_name: templateName, columns });
      } else {
        await createMapping({ source_type: sourceType, template_name: templateName, columns });
      }
      onSaved();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mb-6 rounded-2xl border border-border/50 bg-card p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-base font-semibold text-text-primary">{initial ? "Edit Mapping" : "New Mapping Template"}</h3>
        <button onClick={onCancel}><X className="h-4 w-4 text-text-secondary" /></button>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-text-primary">Template Name</label>
            <input
              type="text"
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              required
              className="w-full rounded-xl border border-border/70 bg-background/60 px-3 py-2 text-sm text-text-primary"
            />
          </div>
          {!initial && (
            <div>
              <label className="mb-1 block text-sm font-medium text-text-primary">Source Type</label>
              <select
                value={sourceType}
                onChange={(e) => setSourceType(e.target.value)}
                className="w-full rounded-xl border border-border/70 bg-background/60 px-3 py-2 text-sm text-text-primary"
              >
                {["file_upload", "google_sheets", "postgres"].map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          )}
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-text-primary">Column Mappings</span>
            <button type="button" onClick={addCol} className="text-xs text-primary hover:underline">+ Add row</button>
          </div>
          <div className="overflow-x-auto rounded-xl border border-border/50">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border/50 bg-card/50 text-left text-xs text-text-secondary">
                  <th className="px-3 py-2 font-medium">Source Column</th>
                  <th className="px-3 py-2 font-medium">Canonical Field</th>
                  <th className="px-3 py-2 font-medium">Cast</th>
                  <th className="px-3 py-2 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {columns.map((col, idx) => (
                  <tr key={idx} className="border-b border-border/20">
                    <td className="px-3 py-1.5">
                      <input
                        type="text"
                        value={col.source}
                        onChange={(e) => setCol(idx, "source", e.target.value)}
                        placeholder="source_col"
                        className="w-full rounded-lg border border-border/50 bg-background/60 px-2 py-1 text-xs text-text-primary"
                      />
                    </td>
                    <td className="px-3 py-1.5">
                      <select
                        value={col.canonical}
                        onChange={(e) => setCol(idx, "canonical", e.target.value)}
                        className="w-full rounded-lg border border-border/50 bg-background/60 px-2 py-1 text-xs text-text-primary"
                      >
                        <option value="">— select —</option>
                        {CANONICAL_FIELDS.map((f) => <option key={f} value={f}>{f}</option>)}
                      </select>
                    </td>
                    <td className="px-3 py-1.5">
                      <select
                        value={col.cast ?? "string"}
                        onChange={(e) => setCol(idx, "cast", e.target.value)}
                        className="w-full rounded-lg border border-border/50 bg-background/60 px-2 py-1 text-xs text-text-primary"
                      >
                        {CAST_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                      </select>
                    </td>
                    <td className="px-3 py-1.5">
                      <button type="button" onClick={() => removeCol(idx)} className="text-text-secondary hover:text-red-500">
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {validation && (
          <div className={`rounded-xl p-4 text-sm ${validation.ok ? "bg-green-500/10 text-green-500" : "bg-red-500/10 text-red-500"}`}>
            <div className="flex items-center gap-2 font-medium mb-2">
              {validation.ok ? <CheckCircle className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
              {validation.ok ? "Validation passed" : `${validation.errors.length} error(s)`}
            </div>
            {validation.errors.map((e, i) => <p key={i} className="text-xs">• {e.message}</p>)}
            {validation.warnings.map((w, i) => <p key={i} className="text-xs text-yellow-500">⚠ {w.message}</p>)}
          </div>
        )}

        {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-500">{error}</p>}

        <div className="flex justify-end gap-2">
          <button type="button" onClick={handleValidate} disabled={validating} className="rounded-xl border border-border/70 px-4 py-2 text-sm text-text-secondary hover:text-text-primary disabled:opacity-60">
            {validating ? "Validating…" : "Validate"}
          </button>
          <button type="button" onClick={onCancel} className="rounded-xl border border-border/70 px-4 py-2 text-sm text-text-secondary">Cancel</button>
          <button type="submit" disabled={saving} className="rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60">
            {saving ? "Saving…" : initial ? "Save Changes" : "Create"}
          </button>
        </div>
      </form>
    </div>
  );
}

export default function MappingsPage() {
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<MappingTemplate | null>(null);
  const { data, isLoading, error, mutate } = useMappings({ page, page_size: 25 });
  const totalPages = Math.ceil(data.total / 25);

  if (isLoading && !data.items.length) return <LoadingCard className="h-64" />;
  if (error) return <ErrorRetry title="Failed to load mappings" />;

  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Mapping Templates"
        description="Column-level source → canonical mapping definitions"
        action={
          <button
            onClick={() => { setEditing(null); setShowForm(true); }}
            className="flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
          >
            <Plus className="h-4 w-4" /> New Mapping
          </button>
        }
      />

      {showForm && (
        <MappingForm initial={editing} onSaved={() => { setShowForm(false); mutate(); }} onCancel={() => setShowForm(false)} />
      )}

      <div className="mt-6 overflow-x-auto rounded-2xl border border-border/50 bg-card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border/50 text-left text-text-secondary">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Source Type</th>
              <th className="px-4 py-3 font-medium">Columns</th>
              <th className="px-4 py-3 font-medium">Version</th>
              <th className="px-4 py-3 font-medium">Updated</th>
              <th className="px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((tpl) => (
              <tr key={tpl.id} className="border-b border-border/30 hover:bg-accent/20">
                <td className="px-4 py-3 font-medium text-text-primary">
                  <div className="flex items-center gap-2">
                    <GitBranch className="h-4 w-4 text-text-secondary" />
                    {tpl.template_name}
                  </div>
                </td>
                <td className="px-4 py-3 text-text-secondary font-mono text-xs">{tpl.source_type}</td>
                <td className="px-4 py-3 text-text-secondary">{tpl.mapping?.columns?.length ?? 0}</td>
                <td className="px-4 py-3 text-text-secondary font-mono text-xs">v{tpl.version}</td>
                <td className="px-4 py-3 text-text-secondary text-xs">{new Date(tpl.updated_at).toLocaleDateString()}</td>
                <td className="px-4 py-3">
                  <button onClick={() => { setEditing(tpl); setShowForm(true); }} className="text-xs text-text-secondary hover:text-text-primary">Edit</button>
                </td>
              </tr>
            ))}
            {data.items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-text-secondary">No mapping templates yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="mt-4 flex justify-center gap-2">
          <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="rounded-lg px-3 py-1.5 text-sm text-text-secondary disabled:opacity-40">Previous</button>
          <span className="px-3 py-1.5 text-sm text-text-secondary">{page} / {totalPages}</span>
          <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="rounded-lg px-3 py-1.5 text-sm text-text-secondary disabled:opacity-40">Next</button>
        </div>
      )}
    </PageTransition>
  );
}
