"use client";

import { forwardRef } from "react";
import { Barcode } from "lucide-react";
import { cn } from "@/lib/utils";

interface ScanBarProps {
  value: string;
  onChange: (v: string) => void;
  onSubmit: (value: string) => void;
  isOnline: boolean;
  placeholder?: string;
  disabled?: boolean;
}

/**
 * Terminal v2 ScanBar — full-width input with an animated cyan scan-pulse
 * sweep. Exposes the underlying input via ref so the parent can refocus
 * after every cart addition or when '/' is pressed.
 */
export const ScanBar = forwardRef<HTMLInputElement, ScanBarProps>(function ScanBar(
  { value, onChange, onSubmit, isOnline, placeholder, disabled },
  ref,
) {
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit(value);
  }

  return (
    <form
      onSubmit={handleSubmit}
      className={cn(
        "relative flex items-center gap-3 overflow-hidden rounded-xl px-4 py-3",
        "border border-cyan-400/30 bg-[rgba(8,24,38,0.7)]",
        "shadow-[0_0_0_1px_rgba(0,199,242,0.08),0_0_24px_rgba(0,199,242,0.1)]",
      )}
    >
      {/* Cyan scan pulse — only animates when online */}
      <div
        aria-hidden="true"
        data-testid="scan-pulse"
        className={cn(
          "pointer-events-none absolute inset-y-0 left-0 w-full",
          "pos-animate-scan bg-gradient-to-r from-transparent via-cyan-400/10 to-transparent",
        )}
        style={{
          animation: isOnline ? "dpScan 2.6s linear infinite" : "none",
        }}
      />
      <Barcode className="relative h-5 w-5 shrink-0 text-cyan-300" aria-hidden="true" />
      <input
        ref={ref}
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder ?? "Scan a drug or enter SKU"}
        aria-label={placeholder ?? "Scan a drug or enter SKU"}
        data-pos-scanner-ignore=""
        disabled={disabled}
        autoComplete="off"
        spellCheck={false}
        className={cn(
          "relative flex-1 bg-transparent text-base font-medium",
          "text-text-primary placeholder:text-text-secondary focus:outline-none",
        )}
      />
      <kbd
        className={cn(
          "relative hidden rounded border border-border bg-surface-raised px-1.5 py-0.5",
          "font-mono text-[10px] uppercase tracking-wider text-text-secondary sm:inline-flex",
        )}
      >
        /
      </kbd>
    </form>
  );
});
