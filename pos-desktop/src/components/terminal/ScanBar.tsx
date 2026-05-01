import { forwardRef } from "react";
import { Barcode } from "lucide-react";
import { cn } from "@shared/lib/utils";

interface ScanBarProps {
  value: string;
  onChange: (v: string) => void;
  onSubmit: (value: string) => void;
  isOnline: boolean;
  placeholder?: string;
  disabled?: boolean;
  /**
   * Bumping this number plays a 220ms white flash overlay (visual
   * confirmation of a successful scan). Use the same key for every
   * cart-add commit point. Inspired by the Gemini POV mockup.
   */
  flashKey?: number;
  /**
   * Bumping this number plays a 320ms red flash overlay (rejected
   * scan / no match). Independent counter from {@link flashKey} so
   * either can fire without affecting the other.
   */
  errorFlashKey?: number;
}

/**
 * Terminal v2 ScanBar — full-width input with an animated cyan scan-pulse
 * sweep. Exposes the underlying input via ref so the parent can refocus
 * after every cart addition or when '/' is pressed.
 */
export const ScanBar = forwardRef<HTMLInputElement, ScanBarProps>(function ScanBar(
  { value, onChange, onSubmit, isOnline, placeholder, disabled, flashKey, errorFlashKey },
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
      {/* Scan-success flash — re-mounts on flashKey change */}
      {flashKey !== undefined && flashKey > 0 && (
        <div
          key={`ok-${flashKey}`}
          aria-hidden="true"
          data-testid="scan-flash"
          className={cn(
            "pointer-events-none absolute inset-0 z-[1] bg-white",
            "pos-scan-flash",
          )}
        />
      )}
      {/* Scan-error flash — re-mounts on errorFlashKey change */}
      {errorFlashKey !== undefined && errorFlashKey > 0 && (
        <div
          key={`err-${errorFlashKey}`}
          aria-hidden="true"
          data-testid="scan-flash-error"
          className={cn(
            "pointer-events-none absolute inset-0 z-[1] bg-red-500/70",
            "pos-scan-flash-error",
          )}
        />
      )}
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
