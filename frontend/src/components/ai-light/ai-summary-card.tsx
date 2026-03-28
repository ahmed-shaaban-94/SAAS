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
      <div className="rounded-lg border border-border bg-card p-6">
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
    <div className="rounded-lg border border-border bg-card p-6">
      <div className="mb-4 flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-accent" />
        <h3 className="text-lg font-semibold text-text-primary">AI Summary</h3>
        <span className="ml-auto text-xs text-text-secondary">{data.period}</span>
      </div>
      <p className="text-sm leading-relaxed text-text-secondary">{data.narrative}</p>
      {data.highlights.length > 0 && (
        <ul className="mt-4 space-y-2">
          {data.highlights.map((highlight, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-text-secondary">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
              <span>{highlight}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
