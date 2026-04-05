"use client";

import { useEffect, useCallback, useRef } from "react";
import { createPortal } from "react-dom";
import { X, Maximize2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChartSpotlightProps {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}

/**
 * Full-screen spotlight overlay for charts.
 * Opens with a cinematic scale-up animation.
 * Close via Esc, click backdrop, or X button.
 */
export function ChartSpotlight({ open, onClose, title, subtitle, children }: ChartSpotlightProps) {
  const contentRef = useRef<HTMLDivElement>(null);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (!open) return;
    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [open, handleKeyDown]);

  // Focus trap
  useEffect(() => {
    if (open && contentRef.current) {
      contentRef.current.focus();
    }
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-label={`${title} — expanded view`}
    >
      {/* Backdrop with blur */}
      <div
        className="absolute inset-0 bg-page/80 backdrop-blur-md animate-spotlight-backdrop"
        onClick={onClose}
      />

      {/* Spotlight card */}
      <div
        ref={contentRef}
        tabIndex={-1}
        className={cn(
          "relative z-10 w-[95vw] max-w-5xl max-h-[90vh] overflow-auto",
          "rounded-2xl border border-accent/20 bg-card shadow-2xl shadow-accent/10",
          "animate-spotlight-enter",
          "focus:outline-none",
        )}
      >
        {/* Glowing top edge */}
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-accent/60 to-transparent" />

        {/* Header */}
        <div className="sticky top-0 z-20 flex items-center justify-between border-b border-border bg-card/95 backdrop-blur-sm px-6 py-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">
              {title}
            </h2>
            {subtitle && (
              <p className="mt-0.5 text-2xl font-bold text-text-primary" data-kpi-value>
                {subtitle}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-text-secondary transition-all hover:bg-accent/10 hover:text-accent"
            aria-label="Close spotlight"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Chart body — taller in spotlight */}
        <div className="p-6">
          {children}
        </div>
      </div>
    </div>,
    document.body,
  );
}

/** Small expand button for ChartCard actions slot */
export function SpotlightTrigger({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex h-7 w-7 items-center justify-center rounded-lg text-text-secondary opacity-0 transition-all group-hover:opacity-100 hover:bg-accent/10 hover:text-accent"
      aria-label="Expand chart"
      title="Expand"
    >
      <Maximize2 className="h-3.5 w-3.5" />
    </button>
  );
}
