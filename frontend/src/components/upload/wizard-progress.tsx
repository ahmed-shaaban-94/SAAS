"use client";

/**
 * Wizard progress indicator (Phase 2 Task 1 / #400).
 *
 * Three-step breadcrumb: Choose Source → Map Columns → Validate & Run.
 * Purely presentational; step state is derived by the parent from the
 * upload flow's actual state.
 */

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

type StepState = "complete" | "active" | "upcoming";

const STEPS = [
  { label: "Choose source" },
  { label: "Map columns" },
  { label: "Validate & run" },
] as const;

export interface WizardProgressProps {
  /** 1-based current step (clamped to [1, 3]). */
  currentStep: number;
}

function stepState(index: number, current: number): StepState {
  if (index < current) return "complete";
  if (index === current) return "active";
  return "upcoming";
}

export function WizardProgress({ currentStep }: WizardProgressProps) {
  const clamped = Math.min(STEPS.length, Math.max(1, currentStep));

  return (
    <ol
      aria-label="Upload wizard progress"
      className="flex items-center gap-2 rounded-[1.5rem] border border-border bg-background/40 p-3"
    >
      {STEPS.map((step, i) => {
        const stepNumber = i + 1;
        const state = stepState(stepNumber, clamped);
        return (
          <li
            key={step.label}
            data-step-state={state}
            className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em]"
          >
            <span
              className={cn(
                "flex h-7 w-7 items-center justify-center rounded-full border text-[11px]",
                state === "complete" &&
                  "border-green-500/40 bg-green-500/10 text-green-500",
                state === "active" &&
                  "border-accent/60 bg-accent/15 text-accent",
                state === "upcoming" &&
                  "border-border bg-background/60 text-text-tertiary",
              )}
            >
              {state === "complete" ? <Check className="h-3.5 w-3.5" /> : stepNumber}
            </span>
            <span
              className={cn(
                state === "upcoming" ? "text-text-tertiary" : "text-text-primary",
              )}
            >
              {step.label}
            </span>
            {i < STEPS.length - 1 && (
              <span
                aria-hidden
                className={cn(
                  "mx-2 h-px flex-1 min-w-6",
                  state === "complete" ? "bg-green-500/40" : "bg-border",
                )}
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
