"use client";

import { useCallback, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { Bookmark, X } from "lucide-react";
import { useFilters } from "@/contexts/filter-context";
import { useToast } from "@/components/ui/toast";
import { useSavedViews } from "@/hooks/use-saved-views";

interface SaveViewDialogProps {
  open: boolean;
  onClose: () => void;
}

export function SaveViewDialog({ open, onClose }: SaveViewDialogProps) {
  const { filters } = useFilters();
  const pathname = usePathname();
  const { createView } = useSavedViews();
  const { success, error: showError } = useToast();

  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const activeFilters = Object.entries(filters).filter(
    ([, v]) => v !== undefined,
  );

  const handleSave = useCallback(async () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    setSaving(true);
    try {
      const filterRecord: Record<string, string | number> = {};
      for (const [k, v] of Object.entries(filters)) {
        if (v !== undefined) filterRecord[k] = v;
      }
      await createView(trimmed, pathname, filterRecord);
      success(`View "${trimmed}" saved`);
      setName("");
      onClose();
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Failed to save view";
      if (msg.includes("409") || msg.includes("duplicate") || msg.includes("unique")) {
        showError(`A view named "${trimmed}" already exists`);
      } else if (msg.includes("422")) {
        showError("Maximum saved views reached (20)");
      } else {
        showError(msg);
      }
    } finally {
      setSaving(false);
    }
  }, [name, filters, pathname, createView, success, showError, onClose]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && name.trim()) handleSave();
    if (e.key === "Escape") onClose();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center" role="dialog" aria-modal="true" aria-label="Save view">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Dialog */}
      <div className="relative z-10 w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-2xl">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bookmark className="h-5 w-5 text-accent" />
            <h2 className="text-lg font-semibold text-text-primary">Save View</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-text-secondary hover:text-text-primary"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* View name input */}
        <div className="mb-4">
          <label
            htmlFor="view-name"
            className="mb-1.5 block text-sm font-medium text-text-secondary"
          >
            View name
          </label>
          <input
            ref={inputRef}
            id="view-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g. Q4 Sales by Region"
            maxLength={100}
            autoFocus
            className="w-full rounded-lg border border-border bg-page px-3 py-2 text-sm text-text-primary outline-none placeholder:text-text-secondary/50 focus:border-accent focus:ring-1 focus:ring-accent"
          />
        </div>

        {/* Current filters summary */}
        <div className="mb-5">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-text-secondary">
            Filters to save
          </p>
          {activeFilters.length === 0 ? (
            <p className="text-sm text-text-secondary">No filters active</p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {activeFilters.map(([key, value]) => (
                <span
                  key={key}
                  className="inline-flex items-center gap-1 rounded-md bg-accent/10 px-2 py-1 text-xs font-medium text-accent"
                >
                  {key}: {String(value)}
                </span>
              ))}
            </div>
          )}
          <p className="mt-2 text-xs text-text-secondary">
            Page: {pathname}
          </p>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm font-medium text-text-secondary transition-colors hover:bg-divider hover:text-text-primary"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!name.trim() || saving}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save View"}
          </button>
        </div>
      </div>
    </div>
  );
}
