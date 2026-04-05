"use client";

import { useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";

interface ShortcutAction {
  /** Two-key sequence, e.g. ["g", "d"] for G then D */
  keys: string[];
  /** Navigation path or callback */
  action: string | (() => void);
  /** Label shown in help modal */
  label: string;
}

export const KEYBOARD_SHORTCUTS: ShortcutAction[] = [
  { keys: ["g", "d"], action: "/dashboard", label: "Go to Dashboard" },
  { keys: ["g", "p"], action: "/products", label: "Go to Products" },
  { keys: ["g", "c"], action: "/customers", label: "Go to Customers" },
  { keys: ["g", "s"], action: "/staff", label: "Go to Staff" },
  { keys: ["g", "b"], action: "/billing", label: "Go to Billing" },
  { keys: ["g", "i"], action: "/insights", label: "Go to Insights" },
  { keys: ["g", "r"], action: "/returns", label: "Go to Returns" },
  { keys: ["g", "t"], action: "/goals", label: "Go to Goals" },
  { keys: ["g", "l"], action: "/pipeline", label: "Go to Pipeline" },
];

/**
 * Registers global two-key combo shortcuts (e.g. G then D = Dashboard).
 * Returns a function to open the help modal.
 */
export function useKeyboardShortcuts(onHelpOpen?: () => void) {
  const router = useRouter();
  const bufferRef = useRef<string>("");
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Ignore when typing in inputs
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      // "?" opens help
      if (e.key === "?" && onHelpOpen) {
        e.preventDefault();
        onHelpOpen();
        return;
      }

      // "/" opens search (Cmd+K)
      if (e.key === "/") {
        e.preventDefault();
        document.dispatchEvent(
          new KeyboardEvent("keydown", { key: "k", metaKey: true, bubbles: true }),
        );
        return;
      }

      const key = e.key.toLowerCase();
      bufferRef.current += key;

      // Reset buffer after 800ms of inactivity
      clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        bufferRef.current = "";
      }, 800);

      // Check for matching shortcut
      for (const shortcut of KEYBOARD_SHORTCUTS) {
        const combo = shortcut.keys.join("");
        if (bufferRef.current.endsWith(combo)) {
          bufferRef.current = "";
          if (typeof shortcut.action === "string") {
            router.push(shortcut.action);
          } else {
            shortcut.action();
          }
          break;
        }
      }
    },
    [router, onHelpOpen],
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);
}
