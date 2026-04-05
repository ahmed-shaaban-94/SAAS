"use client";

import { useState } from "react";
import { X, MessageSquarePlus } from "lucide-react";

interface AddAnnotationDialogProps {
  open: boolean;
  onClose: () => void;
  onSave: (dataPoint: string, note: string, color: string) => void;
  /** Pre-filled data point (e.g. from clicking a chart point) */
  dataPoint?: string;
}

const COLORS = ["#D97706", "#4F46E5", "#059669", "#DC2626", "#8B5CF6"];

export function AddAnnotationDialog({
  open,
  onClose,
  onSave,
  dataPoint: defaultDataPoint,
}: AddAnnotationDialogProps) {
  const [dataPoint, setDataPoint] = useState(defaultDataPoint ?? "");
  const [note, setNote] = useState("");
  const [color, setColor] = useState(COLORS[0]);

  if (!open) return null;

  const handleSave = () => {
    if (!dataPoint.trim() || !note.trim()) return;
    onSave(dataPoint.trim(), note.trim(), color);
    setNote("");
    setDataPoint("");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative w-full max-w-sm rounded-xl border border-border bg-card p-5 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquarePlus className="h-5 w-5 text-accent" />
            <h3 className="text-sm font-semibold text-text-primary">
              Add Annotation
            </h3>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-text-secondary hover:text-text-primary"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-text-secondary">
              Data Point
            </label>
            <input
              type="text"
              value={dataPoint}
              onChange={(e) => setDataPoint(e.target.value)}
              placeholder="e.g. 2024-01-15"
              className="w-full rounded-lg border border-border bg-transparent px-3 py-2 text-sm text-text-primary outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-text-secondary">
              Note
            </label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. Ramadan sale started"
              rows={2}
              className="w-full resize-none rounded-lg border border-border bg-transparent px-3 py-2 text-sm text-text-primary outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-text-secondary">
              Color
            </label>
            <div className="flex gap-2">
              {COLORS.map((c) => (
                <button
                  key={c}
                  onClick={() => setColor(c)}
                  className={`h-6 w-6 rounded-full border-2 transition-transform ${
                    color === c
                      ? "scale-110 border-text-primary"
                      : "border-transparent"
                  }`}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
          </div>
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-lg border border-border px-3 py-1.5 text-sm text-text-secondary hover:bg-divider"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!dataPoint.trim() || !note.trim()}
            className="rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
