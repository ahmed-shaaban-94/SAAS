"use client";

import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { useAISummary } from "@/hooks/use-ai-summary";
import { Sparkles } from "lucide-react";

export function AISummaryCard() {
  const { data, error, isLoading } = useAISummary();

  if (isLoading) {
    return <LoadingCard lines={5} className="h-64" />;
  }

  if (error) {
    return (
      <div className="viz-panel rounded-[1.75rem] p-6">
        <p className="text-sm text-growth-red">
          Failed to load AI summary. Please try again later.
        </p>
      </div>
    );
  }

  if (!data) {
    return <EmptyState title="No summary available" description="AI summary will appear once data is processed." />;
  }

  return (
    <div className="viz-panel relative overflow-hidden rounded-[1.9rem] p-6 sm:p-7">
      <div className="absolute inset-x-8 top-0 h-1 rounded-b-full bg-gradient-to-r from-chart-blue via-accent to-chart-purple opacity-90" />
      <div className="mb-5 flex items-center gap-3">
        <div className="viz-panel-soft flex h-10 w-10 items-center justify-center rounded-2xl">
          <Sparkles className="h-4.5 w-4.5 text-accent" />
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
            AI Summary
          </p>
          <h3 className="mt-2 text-xl font-bold text-text-primary sm:text-2xl">Executive Narrative</h3>
        </div>
        <span className="viz-panel-soft ml-auto rounded-full px-3 py-1 text-xs text-text-secondary">{data.period}</span>
      </div>
      <p className="text-sm leading-7 text-text-secondary sm:text-[15px]">{data.narrative}</p>
      {data.highlights.length > 0 && (
        <ul className="mt-5 space-y-3">
          {data.highlights.map((highlight, i) => (
            <li key={i} className="viz-panel-soft flex items-start gap-3 rounded-[1.2rem] px-4 py-3 text-sm text-text-secondary">
              <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-accent" />
              <span>{highlight}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
