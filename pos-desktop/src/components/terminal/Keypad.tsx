import { useEffect, useState } from "react";
import { Delete } from "lucide-react";
import { cn } from "@shared/lib/utils";

interface KeypadProps {
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
  /**
   * External key signal — when the parent wants to echo a keypress into
   * the "last key" ghost indicator without going through the keypad
   * itself (e.g. keyboard 0-9 events).
   */
  lastKey?: string | null;
}

const KEYS: string[] = ["7", "8", "9", "4", "5", "6", "1", "2", "3", ".", "0", "⌫"];

/**
 * 3x4 numeric keypad — binds to a string `value`. Pressing any key either
 * appends (digits, `.`) or deletes the last char (`⌫`). When a key is
 * pressed (internally or via `lastKey`), a ghost character floats over
 * the keypad and fades out after 350ms via the dpKeyFade keyframe.
 */
export function Keypad({ value, onChange, disabled, lastKey }: KeypadProps) {
  const [ghost, setGhost] = useState<{ key: string; id: number } | null>(null);

  // Echo external key presses (keyboard 0-9) into the ghost indicator.
  useEffect(() => {
    if (!lastKey) return;
    setGhost({ key: lastKey, id: Date.now() });
    const t = setTimeout(() => setGhost(null), 350);
    return () => clearTimeout(t);
  }, [lastKey]);

  function press(k: string) {
    if (disabled) return;
    setGhost({ key: k, id: Date.now() });
    const t = setTimeout(() => setGhost(null), 350);
    if (k === "⌫") onChange(value.slice(0, -1));
    else if (k === "." && value.includes(".")) {
      // ignore double dot
    } else {
      onChange(value + k);
    }
    return () => clearTimeout(t);
  }

  return (
    <div
      className={cn(
        "relative rounded-xl border border-[var(--pos-line)] bg-[rgba(8,24,38,0.5)] p-3",
      )}
    >
      <div className="mb-2 flex items-center justify-between">
        <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-text-secondary">
          Keypad
        </span>
        <span
          data-testid="keypad-value"
          className="font-mono text-[13px] tabular-nums font-semibold text-text-primary"
        >
          {value || "—"}
        </span>
      </div>

      {/* Ghost last-key indicator */}
      <div className="pointer-events-none absolute inset-x-0 top-6 flex justify-center">
        {ghost && (
          <span
            key={ghost.id}
            data-testid="keypad-ghost"
            style={{ animation: "dpKeyFade 350ms ease-out forwards" }}
            className="pos-display text-6xl text-cyan-300/60"
          >
            {ghost.key === "⌫" ? "⌫" : ghost.key}
          </span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-1.5">
        {KEYS.map((k) => (
          <button
            key={k}
            type="button"
            onClick={() => press(k)}
            disabled={disabled}
            aria-label={k === "⌫" ? "backspace" : `key ${k}`}
            className={cn(
              "grid h-10 place-items-center rounded-md border font-mono text-lg font-semibold",
              "border-[var(--pos-line)] bg-white/[0.025] text-text-primary",
              "transition-colors duration-100",
              "hover:border-cyan-400/40 hover:bg-cyan-400/10",
              "disabled:cursor-not-allowed disabled:opacity-40",
            )}
          >
            {k === "⌫" ? <Delete className="h-4 w-4" /> : k}
          </button>
        ))}
      </div>
    </div>
  );
}
