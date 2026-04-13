"use client";

import { cn } from "@/lib/utils";
import { REPORT_TEMPLATES, type ReportTemplate } from "./report-config";

interface TemplatePickerProps {
  selectedId: string | null;
  onSelect: (template: ReportTemplate) => void;
}

export function TemplatePicker({ selectedId, onSelect }: TemplatePickerProps) {
  return (
    <div>
      <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
        Start with a template
      </h3>
      <div className="flex gap-3 overflow-x-auto pb-2">
        {REPORT_TEMPLATES.map((t) => {
          const Icon = t.icon;
          const isSelected = selectedId === t.id;
          return (
            <button
              key={t.id}
              onClick={() => onSelect(t)}
              className={cn(
                "viz-card-hover flex min-w-[150px] flex-shrink-0 flex-col items-center gap-2 rounded-[1.4rem] border p-4 text-center transition-all",
                isSelected
                  ? "viz-panel border-accent/50 bg-accent/10"
                  : "viz-panel border-border/70",
              )}
            >
              <Icon
                className={cn(
                  "h-7 w-7",
                  isSelected ? "text-accent" : "text-text-secondary",
                )}
              />
              <span
                className={cn(
                  "text-xs font-semibold",
                  isSelected ? "text-accent" : "text-text-primary",
                )}
              >
                {t.name}
              </span>
              <span className="text-[10px] text-text-secondary">
                {t.description}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
