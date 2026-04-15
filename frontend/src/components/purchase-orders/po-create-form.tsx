"use client";

import { useState } from "react";
import { X, Plus, Trash2 } from "lucide-react";
import { usePOCreate } from "@/hooks/use-po-create";
import type { POCreateRequest } from "@/types/purchase-orders";

interface LineItemDraft {
  drug_code: string;
  quantity: number;
  unit_price: number;
}

const EMPTY_LINE: LineItemDraft = { drug_code: "", quantity: 0, unit_price: 0 };

interface POCreateFormProps {
  open: boolean;
  onClose: () => void;
  onCreated?: () => void;
}

export function POCreateForm({ open, onClose, onCreated }: POCreateFormProps) {
  const { createPO, isCreating } = usePOCreate();

  const [form, setForm] = useState<Omit<POCreateRequest, "lines">>({
    po_date: new Date().toISOString().slice(0, 10),
    supplier_code: "",
    site_code: "",
    expected_date: "",
  });
  const [lines, setLines] = useState<LineItemDraft[]>([{ ...EMPTY_LINE }]);
  const [error, setError] = useState<string | null>(null);

  const updateLine = (i: number, patch: Partial<LineItemDraft>) => {
    setLines((prev) => prev.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));
  };

  const addLine = () => setLines((prev) => [...prev, { ...EMPTY_LINE }]);

  const removeLine = (i: number) =>
    setLines((prev) => prev.filter((_, idx) => idx !== i));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const validLines = lines.filter((l) => l.drug_code.trim() && l.quantity > 0);
    if (validLines.length === 0) {
      setError("Add at least one line item with a drug code and quantity.");
      return;
    }
    if (!form.supplier_code.trim() || !form.site_code.trim()) {
      setError("Supplier code and site code are required.");
      return;
    }

    const payload: POCreateRequest = {
      ...form,
      expected_date: form.expected_date || undefined,
      lines: validLines,
    };

    try {
      await createPO(payload);
      onCreated?.();
      onClose();
    } catch {
      setError("Failed to create purchase order. Please try again.");
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      {/* Drawer */}
      <aside className="relative flex h-full w-full max-w-xl flex-col border-l border-border bg-card shadow-2xl overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <h2 className="text-lg font-semibold text-text-primary">New Purchase Order</h2>
          <button
            onClick={onClose}
            className="rounded-xl p-1.5 text-text-secondary hover:bg-muted hover:text-text-primary"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-1 flex-col gap-5 p-6">
          {/* Core fields */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-text-secondary">
                PO Date
              </label>
              <input
                type="date"
                required
                value={form.po_date}
                onChange={(e) => setForm((f) => ({ ...f, po_date: e.target.value }))}
                className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-text-secondary">
                Expected Date
              </label>
              <input
                type="date"
                value={form.expected_date ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, expected_date: e.target.value }))}
                className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-text-secondary">
                Supplier Code
              </label>
              <input
                type="text"
                required
                placeholder="SUP-001"
                value={form.supplier_code}
                onChange={(e) => setForm((f) => ({ ...f, supplier_code: e.target.value }))}
                className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-text-secondary">
                Site Code
              </label>
              <input
                type="text"
                required
                placeholder="SITE-01"
                value={form.site_code}
                onChange={(e) => setForm((f) => ({ ...f, site_code: e.target.value }))}
                className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none"
              />
            </div>
          </div>

          {/* Line items */}
          <div>
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                Line Items
              </h3>
              <button
                type="button"
                onClick={addLine}
                className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium text-accent hover:bg-accent/10"
              >
                <Plus className="h-3.5 w-3.5" />
                Add Line
              </button>
            </div>

            <div className="space-y-2">
              {lines.map((line, i) => (
                <div key={i} className="flex items-center gap-2 rounded-lg border border-border bg-muted/40 p-2">
                  <input
                    type="text"
                    placeholder="Drug code"
                    value={line.drug_code}
                    onChange={(e) => updateLine(i, { drug_code: e.target.value })}
                    className="flex-1 rounded border border-border bg-transparent px-2 py-1.5 text-sm focus:border-accent focus:outline-none"
                  />
                  <input
                    type="number"
                    min={1}
                    placeholder="Qty"
                    value={line.quantity || ""}
                    onChange={(e) => updateLine(i, { quantity: Number(e.target.value) })}
                    className="w-20 rounded border border-border bg-transparent px-2 py-1.5 text-sm focus:border-accent focus:outline-none"
                  />
                  <input
                    type="number"
                    min={0}
                    step="0.01"
                    placeholder="Price"
                    value={line.unit_price || ""}
                    onChange={(e) => updateLine(i, { unit_price: Number(e.target.value) })}
                    className="w-24 rounded border border-border bg-transparent px-2 py-1.5 text-sm focus:border-accent focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => removeLine(i)}
                    disabled={lines.length === 1}
                    className="rounded p-1 text-text-secondary hover:text-red-400 disabled:opacity-30"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {error && (
            <p className="rounded-lg bg-red-500/10 px-4 py-2 text-sm text-red-400">{error}</p>
          )}

          <div className="mt-auto flex gap-3 border-t border-border pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-text-secondary hover:bg-muted"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isCreating}
              className="flex-1 rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-black hover:bg-accent/90 disabled:opacity-60"
            >
              {isCreating ? "Creating…" : "Create PO"}
            </button>
          </div>
        </form>
      </aside>
    </div>
  );
}
