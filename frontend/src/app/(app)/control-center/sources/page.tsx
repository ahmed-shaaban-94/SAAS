"use client";

import { useState } from "react";
import { PageTransition } from "@/components/layout/page-transition";
import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { ConnectionForm } from "@/components/control-center/connection-form";
import {
  useConnections,
  archiveConnection,
  testConnection,
  triggerSync,
  type SourceConnection,
} from "@/hooks/use-connections";
import { Plus, Plug, RefreshCw, Zap, Trash2 } from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  draft:    "bg-yellow-500/10 text-yellow-500",
  active:   "bg-green-500/10 text-green-500",
  error:    "bg-red-500/10 text-red-500",
  archived: "bg-zinc-500/10 text-zinc-500",
};

export default function SourcesPage() {
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<SourceConnection | null>(null);
  const [busy, setBusy] = useState<Record<number, string>>({});

  const { data, isLoading, error, mutate } = useConnections({ page, page_size: 25 });
  const totalPages = Math.ceil(data.total / 25);

  async function handleTest(id: number) {
    setBusy((b) => ({ ...b, [id]: "test" }));
    try {
      const res = await testConnection(id);
      alert(res.ok ? `Connected (${res.latency_ms?.toFixed(0)} ms)` : `Failed: ${res.error}`);
    } finally {
      setBusy((b) => { const n = { ...b }; delete n[id]; return n; });
    }
  }

  async function handleSync(id: number) {
    setBusy((b) => ({ ...b, [id]: "sync" }));
    try {
      await triggerSync(id);
      mutate();
    } catch {
      alert("Sync trigger failed");
    } finally {
      setBusy((b) => { const n = { ...b }; delete n[id]; return n; });
    }
  }

  async function handleArchive(id: number) {
    if (!confirm("Archive this connection?")) return;
    await archiveConnection(id);
    mutate();
  }

  if (isLoading && !data.items.length) return <LoadingCard className="h-64" />;
  if (error) return <ErrorRetry title="Failed to load connections" />;

  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Data Sources"
        description="Registered source connections for this tenant"
        action={
          <button
            onClick={() => { setEditing(null); setShowForm(true); }}
            className="flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
          >
            <Plus className="h-4 w-4" /> New Source
          </button>
        }
      />

      {showForm && (
        <ConnectionForm
          initial={editing}
          onSaved={() => { setShowForm(false); mutate(); }}
          onCancel={() => setShowForm(false)}
        />
      )}

      <div className="mt-6 overflow-x-auto rounded-2xl border border-border/50 bg-card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border/50 text-left text-text-secondary">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Last Sync</th>
              <th className="px-4 py-3 font-medium">Created</th>
              <th className="px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((conn) => (
              <tr key={conn.id} className="border-b border-border/30 hover:bg-accent/20">
                <td className="px-4 py-3 font-medium text-text-primary">
                  <div className="flex items-center gap-2">
                    <Plug className="h-4 w-4 text-text-secondary" />
                    {conn.name}
                  </div>
                </td>
                <td className="px-4 py-3 text-text-secondary font-mono text-xs">{conn.source_type}</td>
                <td className="px-4 py-3">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[conn.status] ?? ""}`}>
                    {conn.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-text-secondary text-xs">
                  {conn.last_sync_at ? new Date(conn.last_sync_at).toLocaleString() : "—"}
                </td>
                <td className="px-4 py-3 text-text-secondary text-xs">
                  {new Date(conn.created_at).toLocaleDateString()}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleTest(conn.id)}
                      disabled={!!busy[conn.id]}
                      title="Test connection"
                      className="rounded-lg p-1.5 text-text-secondary hover:text-primary disabled:opacity-40"
                    >
                      <RefreshCw className={`h-4 w-4 ${busy[conn.id] === "test" ? "animate-spin" : ""}`} />
                    </button>
                    <button
                      onClick={() => handleSync(conn.id)}
                      disabled={!!busy[conn.id]}
                      title="Trigger sync"
                      className="rounded-lg p-1.5 text-text-secondary hover:text-primary disabled:opacity-40"
                    >
                      <Zap className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => { setEditing(conn); setShowForm(true); }}
                      className="rounded-lg px-2 py-1 text-xs text-text-secondary hover:text-text-primary"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleArchive(conn.id)}
                      title="Archive"
                      className="rounded-lg p-1.5 text-text-secondary hover:text-red-500"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {data.items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-text-secondary">
                  No source connections yet. Click <strong>New Source</strong> to add one.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="mt-4 flex justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="rounded-lg px-3 py-1.5 text-sm text-text-secondary hover:text-text-primary disabled:opacity-40"
          >
            Previous
          </button>
          <span className="px-3 py-1.5 text-sm text-text-secondary">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="rounded-lg px-3 py-1.5 text-sm text-text-secondary hover:text-text-primary disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </PageTransition>
  );
}
