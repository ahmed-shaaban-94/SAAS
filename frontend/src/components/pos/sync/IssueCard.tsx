"use client";

import { useMemo } from "react";
import { cn } from "@/lib/utils";
import type { QueueRow } from "@/lib/pos/ipc";
import { classifyReason, TONE_CLASSES } from "./reason-tags";

export type IssueAction = "retry_override" | "record_loss" | "corrective_void";

interface IssueCardProps {
  row: QueueRow;
  isActive: boolean;
  onSelect: () => void;
  onAction: (kind: IssueAction) => void;
}

function formatElapsed(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function IssueCard({ row, isActive, onSelect, onAction }: IssueCardProps) {
  const reason = useMemo(() => classifyReason(row.last_error), [row.last_error]);
  const tone = TONE_CLASSES[reason.tone];

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
      data-testid={`issue-card-${row.local_id}`}
      data-reason={reason.key}
      aria-pressed={isActive}
      className={cn(
        "group relative grid cursor-pointer items-center gap-3 overflow-hidden rounded-xl border bg-surface px-4 py-3 transition-all",
        "grid-cols-[12px_auto_1fr_auto]",
        "hover:border-accent/40",
        isActive ? "border-accent shadow-[0_0_0_1px_rgba(0,199,242,0.4)]" : "border-border",
      )}
    >
      <span className={cn("absolute inset-y-0 left-0 w-[3px]", tone.rail)} aria-hidden="true" />

      <span className="sr-only">Select issue</span>

      <div className="flex flex-col gap-1">
        <span
          className={cn(
            "inline-flex items-center rounded-md border px-1.5 py-0.5 font-mono text-[9.5px] font-bold uppercase tracking-[0.18em]",
            tone.chip,
          )}
        >
          {reason.label}
        </span>
        <span className="font-mono text-[10px] uppercase tracking-wider text-text-secondary">
          #{row.client_txn_id.slice(-6)}
        </span>
      </div>

      <div className="min-w-0">
        <p className="truncate font-mono text-xs text-text-primary">{row.endpoint}</p>
        {row.last_error && (
          <p className={cn("mt-1 truncate text-xs", tone.text)}>{row.last_error}</p>
        )}
        <p className="mt-0.5 font-mono text-[10px] uppercase tracking-wider text-text-secondary">
          {formatElapsed(row.created_at)} · retries {row.retry_count}
        </p>
      </div>

      <div className="flex items-center gap-2">
        <ActionBtn
          kbd="O"
          label="Override"
          data-testid={`action-override-${row.local_id}`}
          onClick={(e) => {
            e.stopPropagation();
            onAction("retry_override");
          }}
          tone="accent"
        />
        <ActionBtn
          kbd="L"
          label="Loss"
          data-testid={`action-loss-${row.local_id}`}
          onClick={(e) => {
            e.stopPropagation();
            onAction("record_loss");
          }}
          tone="red"
        />
        <ActionBtn
          kbd="R"
          label="Void"
          data-testid={`action-void-${row.local_id}`}
          onClick={(e) => {
            e.stopPropagation();
            onAction("corrective_void");
          }}
          tone="amber"
        />
      </div>
    </div>
  );
}

interface ActionBtnProps {
  kbd: string;
  label: string;
  tone: "accent" | "red" | "amber";
  onClick: (e: React.MouseEvent<HTMLButtonElement>) => void;
  "data-testid"?: string;
}

function ActionBtn({ kbd, label, tone, onClick, ...rest }: ActionBtnProps) {
  const toneClass =
    tone === "accent"
      ? "border-accent/40 bg-accent/10 text-accent hover:bg-accent/20"
      : tone === "red"
        ? "border-destructive/40 bg-destructive/10 text-destructive hover:bg-destructive/20"
        : "border-amber-400/40 bg-amber-400/10 text-amber-300 hover:bg-amber-400/20";

  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={rest["data-testid"]}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] font-semibold uppercase tracking-wide transition-colors",
        toneClass,
      )}
    >
      <span>{label}</span>
      <kbd className="inline-flex h-4 min-w-[14px] items-center justify-center rounded border border-current/30 px-1 font-mono text-[9px] opacity-80">
        {kbd}
      </kbd>
    </button>
  );
}
