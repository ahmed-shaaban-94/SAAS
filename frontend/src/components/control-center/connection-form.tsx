"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { createConnection, updateConnection, type SourceConnection } from "@/hooks/use-connections";

const SOURCE_TYPES = ["file_upload", "google_sheets", "postgres", "mysql", "mssql", "shopify"] as const;

interface Props {
  initial: SourceConnection | null;
  onSaved: () => void;
  onCancel: () => void;
}

export function ConnectionForm({ initial, onSaved, onCancel }: Props) {
  const [name, setName] = useState(initial?.name ?? "");
  const [sourceType, setSourceType] = useState(initial?.source_type ?? "file_upload");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      if (initial) {
        await updateConnection(initial.id, { name });
      } else {
        await createConnection({ name, source_type: sourceType, config: {} });
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
        <h3 className="text-base font-semibold text-text-primary">
          {initial ? "Edit Connection" : "New Source Connection"}
        </h3>
        <button onClick={onCancel} className="rounded-lg p-1 text-text-secondary hover:text-text-primary">
          <X className="h-4 w-4" />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-text-primary">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="e.g. Q1-2025 Sales Upload"
            className="w-full rounded-xl border border-border/70 bg-background/60 px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/50"
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
              {SOURCE_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
        )}

        {error && (
          <p className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-500">{error}</p>
        )}

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-xl border border-border/70 px-4 py-2 text-sm text-text-secondary hover:text-text-primary"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            className="rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60"
          >
            {saving ? "Saving…" : initial ? "Save Changes" : "Create"}
          </button>
        </div>
      </form>
    </div>
  );
}
