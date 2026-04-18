"use client";

/**
 * Onboarding Strip (Phase 2 Task 5 / #404).
 *
 * A small 4-step progress strip on the dashboard. Auto-advances as the
 * user hits each golden-path milestone, via the `ttfi:event` window
 * CustomEvent emitted by `lib/analytics-events.ts` (#399).
 *
 * State persistence is frontend-only for this pass (localStorage,
 * `ttfi_onboarding_strip_v1`). Backend sync against
 * `users.onboarding_state` is a scoped follow-up when we know what
 * the cross-device UX should look like.
 *
 * Hides itself when either:
 *   - All 4 steps are complete, OR
 *   - More than 14 days have passed since the strip first mounted.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { Check, Copy, CheckCheck } from "lucide-react";
import { cn } from "@/lib/utils";

const STATE_KEY = "ttfi_onboarding_strip_v1";
const AUTO_HIDE_DAYS = 14;

// "upload_data" is intentionally distinct from the OnboardingWizard's "connect_data" step.
// The wizard tracks account setup; this strip tracks TTFI milestones. See ADR 006.
type StepId = "upload_data" | "validate" | "first_insight" | "share";

interface StepDef {
  id: StepId;
  label: string;
  /** TTFI event that auto-completes this step, if any. */
  trigger?: "upload_started" | "upload_completed" | "first_insight_seen";
}

const STEPS: readonly StepDef[] = [
  { id: "upload_data", label: "Upload data", trigger: "upload_started" },
  { id: "validate", label: "Validate", trigger: "upload_completed" },
  { id: "first_insight", label: "See first insight", trigger: "first_insight_seen" },
  { id: "share", label: "Share with teammate" /* manual */ },
] as const;

interface StripState {
  first_seen_at?: string;
  completed?: Partial<Record<StepId, string>>;
}

function loadState(): StripState {
  if (typeof localStorage === "undefined") return {};
  try {
    const raw = localStorage.getItem(STATE_KEY);
    return raw ? (JSON.parse(raw) as StripState) : {};
  } catch {
    return {};
  }
}

function saveState(next: StripState): void {
  if (typeof localStorage === "undefined") return;
  try {
    localStorage.setItem(STATE_KEY, JSON.stringify(next));
  } catch {
    // localStorage full or disabled — degrade silently.
  }
}

function daysBetween(iso: string): number {
  const then = new Date(iso).getTime();
  const now = Date.now();
  return Math.floor((now - then) / (1000 * 60 * 60 * 24));
}

export function OnboardingStrip() {
  const [state, setState] = useState<StripState>(() => {
    const loaded = loadState();
    // Stamp first_seen_at on the very first mount.
    if (!loaded.first_seen_at) {
      const next = { ...loaded, first_seen_at: new Date().toISOString() };
      saveState(next);
      return next;
    }
    return loaded;
  });

  const markComplete = useCallback((id: StepId) => {
    setState((prev) => {
      if (prev.completed?.[id]) return prev;
      const next: StripState = {
        ...prev,
        completed: {
          ...(prev.completed ?? {}),
          [id]: new Date().toISOString(),
        },
      };
      saveState(next);
      return next;
    });
  }, []);

  // Subscribe to TTFI events to auto-complete steps.
  useEffect(() => {
    function onEvent(e: Event) {
      const detail = (e as CustomEvent).detail as { name?: string } | undefined;
      if (!detail?.name) return;
      for (const step of STEPS) {
        if (step.trigger && step.trigger === detail.name) {
          markComplete(step.id);
        }
      }
    }
    window.addEventListener("ttfi:event", onEvent);
    // Cross-tab + test-simulation support: re-read on storage events.
    function onStorage() {
      setState(loadState());
    }
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener("ttfi:event", onEvent);
      window.removeEventListener("storage", onStorage);
    };
  }, [markComplete]);

  const allDone = useMemo(
    () => STEPS.every((s) => !!state.completed?.[s.id]),
    [state.completed],
  );
  const expired = useMemo(
    () =>
      state.first_seen_at
        ? daysBetween(state.first_seen_at) > AUTO_HIDE_DAYS
        : false,
    [state.first_seen_at],
  );

  const [justCopied, setJustCopied] = useState(false);

  async function handleShare() {
    const url =
      typeof window !== "undefined" ? window.location.origin : "https://datapulse";
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(url);
      }
      setJustCopied(true);
      markComplete("share");
      window.setTimeout(() => setJustCopied(false), 2000);
    } catch {
      // Clipboard denied — still mark step complete so the user can move on.
      markComplete("share");
    }
  }

  if (allDone || expired) return null;

  return (
    <ol
      aria-label="Onboarding progress"
      className="mb-6 flex flex-wrap items-center gap-3 rounded-[1.5rem] border border-border bg-background/40 p-3 text-xs"
    >
      {STEPS.map((step) => {
        const done = !!state.completed?.[step.id];
        const isShare = step.id === "share";
        return (
          <li
            key={step.id}
            data-step={step.id}
            data-step-state={done ? "complete" : "pending"}
            className="flex items-center gap-2"
          >
            <span
              className={cn(
                "flex h-6 w-6 items-center justify-center rounded-full border text-[10px]",
                done
                  ? "border-green-500/40 bg-green-500/10 text-green-500"
                  : "border-border bg-background/50 text-text-tertiary",
              )}
            >
              {done ? <Check className="h-3 w-3" /> : ""}
            </span>
            <span
              className={cn(
                "font-medium",
                done ? "text-text-primary" : "text-text-secondary",
              )}
            >
              {step.label}
            </span>
            {isShare && !done && (
              <button
                type="button"
                onClick={handleShare}
                aria-label="Copy share link"
                className="ml-1 inline-flex items-center gap-1 rounded-md border border-border bg-background/60 px-2 py-0.5 text-[11px] font-semibold text-text-secondary transition-colors hover:text-accent"
              >
                {justCopied ? (
                  <>
                    <CheckCheck className="h-3 w-3" /> Copied
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3" /> Copy share link
                  </>
                )}
              </button>
            )}
          </li>
        );
      })}
    </ol>
  );
}
