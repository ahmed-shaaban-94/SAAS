"use client";

/** /control-center/releases — Published configuration snapshots on the v2 shell. */

import { useState } from "react";
import { History, RotateCcw } from "lucide-react";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { useReleases, rollbackRelease } from "@/hooks/use-releases";

export default function ReleasesPage() {
  const [page, setPage] = useState(1);
  const [rolling, setRolling] = useState<number | null>(null);
  const { data, isLoading, error, mutate } = useReleases({ page, page_size: 25 });
  const totalPages = Math.ceil(data.total / 25);

  async function handleRollback(id: number, version: number) {
    if (!confirm(`Roll back to release v${version}? This creates a new release restoring that snapshot.`))
      return;
    setRolling(id);
    try {
      await rollbackRelease(id);
      mutate();
    } catch {
      alert("Rollback failed");
    } finally {
      setRolling(null);
    }
  }

  return (
    <DashboardShell
      activeHref="/control-center/releases"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Control Center", href: "/control-center" },
        { label: "Releases" },
      ]}
    >
      <div className="page">
        <div>
          <h1 className="page-title">Releases.</h1>
          <p className="page-sub">Immutable published configuration snapshots (append-only log).</p>
        </div>

        {isLoading && !data.items.length ? (
          <LoadingCard className="h-64" />
        ) : error ? (
          <ErrorRetry title="Failed to load releases" />
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-border/50 bg-card">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border/50 text-left text-text-secondary">
                  <th className="px-4 py-3 font-medium">Version</th>
                  <th className="px-4 py-3 font-medium">Type</th>
                  <th className="px-4 py-3 font-medium">Notes</th>
                  <th className="px-4 py-3 font-medium">Published By</th>
                  <th className="px-4 py-3 font-medium">Published At</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((rel) => (
                  <tr key={rel.id} className="border-b border-border/30 hover:bg-accent/20">
                    <td className="px-4 py-3 font-medium text-text-primary">
                      <div className="flex items-center gap-2">
                        <History className="h-4 w-4 text-text-secondary" />v{rel.release_version}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {rel.is_rollback ? (
                        <span className="rounded-full bg-orange-500/10 px-2 py-0.5 text-xs font-medium text-orange-500">
                          rollback
                        </span>
                      ) : (
                        <span className="rounded-full bg-green-500/10 px-2 py-0.5 text-xs font-medium text-green-500">
                          publish
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-text-secondary max-w-xs truncate">
                      {rel.release_notes || <span className="italic text-text-tertiary">—</span>}
                    </td>
                    <td className="px-4 py-3 text-text-secondary text-xs font-mono">
                      {rel.published_by ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-text-secondary text-xs">
                      {new Date(rel.published_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleRollback(rel.id, rel.release_version)}
                        disabled={rolling === rel.id}
                        title="Rollback to this release"
                        className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-text-secondary hover:text-orange-500 disabled:opacity-40"
                      >
                        <RotateCcw className="h-3.5 w-3.5" />
                        Rollback
                      </button>
                    </td>
                  </tr>
                ))}
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center text-text-secondary">
                      No releases yet. Publish a validated draft to create the first one.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {totalPages > 1 && (
          <div className="flex justify-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="rounded-lg px-3 py-1.5 text-sm text-text-secondary disabled:opacity-40"
            >
              Previous
            </button>
            <span className="px-3 py-1.5 text-sm text-text-secondary">
              {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="rounded-lg px-3 py-1.5 text-sm text-text-secondary disabled:opacity-40"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </DashboardShell>
  );
}
