"use client";

import { X, Plus } from "lucide-react";
import { WIDGET_REGISTRY } from "./widget-registry";

interface WidgetPickerProps {
  open: boolean;
  onClose: () => void;
  onAdd: (widgetId: string) => void;
  activeWidgets: string[];
}

export function WidgetPicker({
  open,
  onClose,
  onAdd,
  activeWidgets,
}: WidgetPickerProps) {
  if (!open) return null;

  const available = WIDGET_REGISTRY.filter(
    (w) => !activeWidgets.includes(w.id),
  );

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative w-full max-w-md rounded-xl border border-border bg-card p-5 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-text-primary">
            Add Widget
          </h3>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-text-secondary hover:text-text-primary"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {available.length === 0 ? (
          <p className="py-6 text-center text-sm text-text-secondary">
            All widgets are already on your dashboard
          </p>
        ) : (
          <div className="space-y-2">
            {available.map((widget) => (
              <button
                key={widget.id}
                onClick={() => {
                  onAdd(widget.id);
                  onClose();
                }}
                className="flex w-full items-center gap-3 rounded-lg border border-border p-3 text-left transition-colors hover:border-accent/40 hover:bg-accent/5"
              >
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent/10">
                  <Plus className="h-4 w-4 text-accent" />
                </div>
                <div>
                  <p className="text-sm font-medium text-text-primary">
                    {widget.label}
                  </p>
                  <p className="text-xs text-text-secondary">
                    {widget.description}
                  </p>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
