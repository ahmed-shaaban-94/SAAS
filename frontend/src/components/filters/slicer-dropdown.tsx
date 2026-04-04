"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { ChevronDown, Search, X } from "lucide-react";

export interface SlicerDropdownProps {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  options: { key: string; label: string }[];
  value: string | undefined;
  onChange: (value: string | undefined) => void;
  searchable?: boolean;
}

export function SlicerDropdown({
  label,
  icon: Icon,
  options,
  value,
  onChange,
  searchable = false,
}: SlicerDropdownProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [focusIdx, setFocusIdx] = useState(-1);
  const ref = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setSearch("");
        setFocusIdx(-1);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Reset focus index when dropdown opens/closes or search changes
  useEffect(() => {
    setFocusIdx(-1);
  }, [open, search]);

  const filtered = searchable && search
    ? options.filter((o) =>
        o.label.toLowerCase().includes(search.toLowerCase())
      )
    : options;

  const selectedLabel = value
    ? options.find((o) => o.key === value)?.label ?? value
    : null;

  // Keyboard navigation handler
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!open) {
        if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          setOpen(true);
        }
        return;
      }

      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setFocusIdx((prev) => Math.min(prev + 1, filtered.length - 1));
          break;
        case "ArrowUp":
          e.preventDefault();
          setFocusIdx((prev) => Math.max(prev - 1, 0));
          break;
        case "Enter":
        case " ":
          e.preventDefault();
          if (focusIdx >= 0 && focusIdx < filtered.length) {
            onChange(filtered[focusIdx].key);
            setOpen(false);
            setSearch("");
          }
          break;
        case "Escape":
          e.preventDefault();
          setOpen(false);
          setSearch("");
          break;
        case "Home":
          e.preventDefault();
          setFocusIdx(0);
          break;
        case "End":
          e.preventDefault();
          setFocusIdx(filtered.length - 1);
          break;
      }
    },
    [open, filtered, focusIdx, onChange],
  );

  // Scroll focused item into view
  useEffect(() => {
    if (focusIdx >= 0 && listRef.current) {
      const items = listRef.current.querySelectorAll("[data-option]");
      items[focusIdx]?.scrollIntoView({ block: "nearest" });
    }
  }, [focusIdx]);

  return (
    <div ref={ref} className="relative" onKeyDown={handleKeyDown}>
      {/* Trigger button */}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`Filter by ${label}${selectedLabel ? `: ${selectedLabel}` : ""}`}
        className={cn(
          "flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-all duration-200",
          "min-w-[140px] max-w-[220px]",
          value
            ? "border-accent/50 bg-accent/10 text-accent"
            : "border-border bg-card text-text-secondary hover:border-accent/30 hover:text-text-primary",
        )}
      >
        <Icon className="h-4 w-4 shrink-0" />
        <span className="truncate flex-1 text-left">
          {selectedLabel ?? label}
        </span>
        {value ? (
          <X
            className="h-3.5 w-3.5 shrink-0 opacity-60 hover:opacity-100"
            onClick={(e) => {
              e.stopPropagation();
              onChange(undefined);
              setOpen(false);
            }}
          />
        ) : (
          <ChevronDown
            className={cn(
              "h-3.5 w-3.5 shrink-0 transition-transform duration-200",
              open && "rotate-180",
            )}
          />
        )}
      </button>

      {/* Dropdown panel */}
      {open && (
        <div
          role="listbox"
          aria-label={`${label} options`}
          className="absolute left-0 top-full z-50 mt-1 w-64 rounded-lg border border-border bg-card shadow-xl shadow-black/20"
        >
          {/* Search */}
          {searchable && (
            <div className="border-b border-border p-2">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-secondary" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder={`Search ${label.toLowerCase()}...`}
                  className="w-full rounded-md bg-page py-1.5 pl-8 pr-3 text-sm text-text-primary placeholder:text-text-secondary/50 focus:outline-none focus:ring-1 focus:ring-accent"
                  autoFocus
                  aria-label={`Search ${label}`}
                />
              </div>
            </div>
          )}

          {/* Options list */}
          <div ref={listRef} className="max-h-60 overflow-y-auto p-1">
            {/* Clear option */}
            {value && (
              <button
                type="button"
                onClick={() => {
                  onChange(undefined);
                  setOpen(false);
                  setSearch("");
                }}
                className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-text-secondary transition-colors hover:bg-divider hover:text-text-primary"
              >
                <X className="h-3.5 w-3.5" />
                Clear selection
              </button>
            )}

            {filtered.length === 0 ? (
              <p className="px-3 py-4 text-center text-xs text-text-secondary">
                No matches found
              </p>
            ) : (
              filtered.map((option, idx) => (
                <button
                  key={option.key}
                  type="button"
                  data-option
                  role="option"
                  aria-selected={option.key === value}
                  onClick={() => {
                    onChange(option.key);
                    setOpen(false);
                    setSearch("");
                  }}
                  className={cn(
                    "flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                    option.key === value
                      ? "bg-accent/10 text-accent"
                      : "text-text-primary hover:bg-divider",
                    idx === focusIdx && "ring-2 ring-accent ring-inset",
                  )}
                >
                  {/* Radio-style indicator */}
                  <span
                    className={cn(
                      "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border",
                      option.key === value
                        ? "border-accent bg-accent"
                        : "border-border",
                    )}
                  >
                    {option.key === value && (
                      <span className="h-1.5 w-1.5 rounded-full bg-page" />
                    )}
                  </span>
                  <span className="truncate">{option.label}</span>
                </button>
              ))
            )}
          </div>

          {/* Footer count */}
          <div className="border-t border-border px-3 py-1.5">
            <p className="text-[10px] text-text-secondary">
              {filtered.length} of {options.length} items
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
