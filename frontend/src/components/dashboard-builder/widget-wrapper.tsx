"use client";

import { Component, type ReactNode } from "react";
import { GripVertical, RefreshCw, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface WidgetErrorState {
  hasError: boolean;
  error: Error | null;
}

class WidgetErrorBoundary extends Component<
  { title: string; children: ReactNode },
  WidgetErrorState
> {
  constructor(props: { title: string; children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): WidgetErrorState {
    return { hasError: true, error };
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-4 text-center">
        <p className="text-xs text-text-secondary">
          <span className="font-medium text-text-primary">{this.props.title}</span>
          {" "}failed to load
        </p>
        <button
          aria-label="retry"
          onClick={() => this.setState({ hasError: false, error: null })}
          className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs text-text-secondary hover:border-accent hover:text-accent"
        >
          <RefreshCw className="h-3 w-3" />
          Retry
        </button>
      </div>
    );
  }
}

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
        <WidgetErrorBoundary title={title}>
          {children}
        </WidgetErrorBoundary>
      </div>
    </div>
  );
}
