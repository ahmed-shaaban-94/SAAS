"use client";

import { cn } from "@/lib/utils";
import { Check } from "lucide-react";

const STEPS = ["draft", "submitted", "partial", "received"] as const;
type Step = (typeof STEPS)[number];

const STEP_LABELS: Record<Step, string> = {
  draft: "Draft",
  submitted: "Submitted",
  partial: "Partial",
  received: "Received",
};

const STEP_ACTIVE_CLASSES: Record<Step, string> = {
  draft: "bg-gray-500 text-white",
  submitted: "bg-blue-500 text-white",
  partial: "bg-amber-500 text-white",
  received: "bg-green-500 text-white",
};

interface POStatusPipelineProps {
  currentStatus: string;
}

export function POStatusPipeline({ currentStatus }: POStatusPipelineProps) {
  if (currentStatus === "cancelled") {
    return (
      <div className="flex items-center gap-2 rounded-lg bg-red-500/10 px-4 py-3 text-sm font-medium text-red-500">
        <span className="h-2 w-2 rounded-full bg-red-500" />
        Order Cancelled
      </div>
    );
  }

  const currentIndex = STEPS.indexOf(currentStatus as Step);

  return (
    <div className="flex items-center gap-1 overflow-x-auto pb-1">
      {STEPS.map((step, i) => {
        const isCompleted = currentIndex > i;
        const isActive = currentIndex === i;

        return (
          <div key={step} className="flex items-center gap-1">
            <div className="flex flex-col items-center gap-1">
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition-colors",
                  isCompleted
                    ? "bg-green-500 text-white"
                    : isActive
                      ? STEP_ACTIVE_CLASSES[step]
                      : "bg-muted text-muted-foreground",
                )}
              >
                {isCompleted ? <Check className="h-3.5 w-3.5" /> : i + 1}
              </div>
              <span
                className={cn(
                  "whitespace-nowrap text-[11px]",
                  isActive ? "font-semibold text-text-primary" : "text-muted-foreground",
                )}
              >
                {STEP_LABELS[step]}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div
                className={cn(
                  "mb-5 h-0.5 w-10 flex-shrink-0 transition-colors",
                  isCompleted ? "bg-green-500" : "bg-muted",
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
