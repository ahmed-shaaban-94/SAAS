"use client";

import { cn } from "@/lib/utils";

interface NumPadProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  className?: string;
}

const PAD_KEYS = [
  ["1", "2", "3", "QTY"],
  ["4", "5", "6", "DEL"],
  ["7", "8", "9", "CLR"],
  [".", "0", "00", "ENTER"],
] as const;

export function NumPad({ value, onChange, onSubmit, className }: NumPadProps) {
  function handleKey(key: string) {
    switch (key) {
      case "DEL":
        onChange(value.slice(0, -1));
        break;
      case "CLR":
        onChange("");
        break;
      case "ENTER":
        onSubmit(value);
        break;
      case "QTY":
        // Signal qty mode — handled by parent
        window.dispatchEvent(new CustomEvent("pos:numpad-qty", { detail: value }));
        break;
      default:
        // Prevent multiple decimal points
        if (key === "." && value.includes(".")) return;
        onChange(value + key);
    }
  }

  return (
    <div className={cn("grid grid-cols-4 gap-2", className)}>
      {PAD_KEYS.flat().map((key) => {
        const isAction = ["QTY", "DEL", "CLR", "ENTER"].includes(key);
        const isEnter = key === "ENTER";
        return (
          <button
            key={key}
            type="button"
            aria-label={key}
            onClick={() => handleKey(key)}
            className={cn(
              // Minimum 48×48px touch targets per plan spec
              "flex min-h-[3rem] min-w-[3rem] items-center justify-center rounded-xl",
              "text-sm font-semibold select-none transition-all duration-100",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
              "active:scale-95",
              isEnter
                ? "col-span-1 bg-accent text-accent-foreground shadow-[0_8px_24px_rgba(0,199,242,0.25)] hover:bg-accent/90"
                : isAction
                  ? "bg-surface-raised text-text-secondary hover:bg-surface-raised/80"
                  : "bg-surface text-text-primary hover:bg-surface/80",
            )}
          >
            {key}
          </button>
        );
      })}
    </div>
  );
}
