"use client";

import { X } from "lucide-react";
import { KEYBOARD_SHORTCUTS } from "@/hooks/use-keyboard-shortcuts";

interface KeyboardShortcutsHelpProps {
  open: boolean;
  onClose: () => void;
}

function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="inline-flex h-6 min-w-[24px] items-center justify-center rounded border border-border bg-divider px-1.5 text-[11px] font-semibold text-text-primary">
      {children}
    </kbd>
  );
}

export function KeyboardShortcutsHelp({ open, onClose }: KeyboardShortcutsHelpProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Dialog */}
      <div className="relative w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-text-primary">
            Keyboard Shortcuts
          </h2>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-text-secondary hover:text-text-primary"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-1">
          {/* Global shortcuts */}
          <div className="mb-3 flex items-center justify-between rounded-lg bg-divider/30 px-3 py-2">
            <span className="text-sm text-text-secondary">Search</span>
            <div className="flex items-center gap-1">
              <Kbd>⌘</Kbd>
              <Kbd>K</Kbd>
            </div>
          </div>
          <div className="mb-3 flex items-center justify-between rounded-lg bg-divider/30 px-3 py-2">
            <span className="text-sm text-text-secondary">Search (alt)</span>
            <Kbd>/</Kbd>
          </div>
          <div className="mb-4 flex items-center justify-between rounded-lg bg-divider/30 px-3 py-2">
            <span className="text-sm text-text-secondary">Show shortcuts</span>
            <Kbd>?</Kbd>
          </div>

          {/* Navigation shortcuts */}
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
            Navigation
          </p>
          {KEYBOARD_SHORTCUTS.map((shortcut) => (
            <div
              key={shortcut.keys.join("")}
              className="flex items-center justify-between px-3 py-1.5"
            >
              <span className="text-sm text-text-secondary">{shortcut.label}</span>
              <div className="flex items-center gap-1">
                {shortcut.keys.map((key, i) => (
                  <Kbd key={i}>{key.toUpperCase()}</Kbd>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 border-t border-border pt-3 text-center text-[10px] text-text-secondary">
          Press <Kbd>?</Kbd> anytime to show this help
        </div>
      </div>
    </div>
  );
}
