"use client";

import { GripVertical, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface WidgetWrapperProps {
  children: React.ReactNode;
  title: string;
  editMode: boolean;
  onRemove?: () => void;
  className?: string;
}

export function WidgetWrapper({
  children,
  title,
  editMode,
  onRemove,
  className,
}: WidgetWrapperProps) {
  return (
    <div
      className={cn(
        "h-full rounded-xl border border-border bg-card overflow-hidden",
        editMode && "ring-2 ring-accent/20 ring-dashed",
        className,
      )}
    >
      {editMode && (
        <div className="flex items-center justify-between bg-divider/50 px-3 py-1.5 cursor-move drag-handle">
          <div className="flex items-center gap-1.5 text-xs text-text-secondary">
            <GripVertical className="h-3.5 w-3.5" />
            <span>{title}</span>
          </div>
          {onRemove && (
            <button
              onClick={onRemove}
              className="rounded p-0.5 text-text-secondary hover:bg-growth-red/10 hover:text-growth-red"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      )}
      <div className={cn("p-4", editMode && "pointer-events-none opacity-80")}>
        {children}
      </div>
    </div>
  );
}
