"use client";

import { useState } from "react";
import { postAPI } from "@/lib/api-client";
import { usePipelineRuns } from "@/hooks/use-pipeline-runs";
import type { TriggerResponse } from "@/types/api";

export function TriggerButton() {
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const { mutate } = usePipelineRuns({ limit: 50 });

  async function handleTrigger() {
    if (loading) return;
    setLoading(true);
    setFeedback(null);

    try {
      const res = await postAPI<TriggerResponse>("/api/v1/pipeline/trigger");
      setFeedback(`Run started: ${res.run_id.slice(0, 8)}...`);
      await mutate();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Trigger failed";
      setFeedback(`Error: ${message}`);
    } finally {
      setLoading(false);
      // Clear feedback after 4 seconds
      setTimeout(() => setFeedback(null), 4000);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        onClick={handleTrigger}
        disabled={loading}
        className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-page transition-colors hover:bg-accent/80 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {loading ? (
          <>
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-page border-t-transparent" />
            Triggering...
          </>
        ) : (
          "Trigger Pipeline"
        )}
      </button>

      {feedback && (
        <p className="text-xs text-text-secondary">{feedback}</p>
      )}
    </div>
  );
}
