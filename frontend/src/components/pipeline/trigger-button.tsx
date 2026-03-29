"use client";

import { useState } from "react";
import { postAPI } from "@/lib/api-client";
import { usePipelineRuns } from "@/hooks/use-pipeline-runs";
import { useToast } from "@/components/ui/toast";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import type { TriggerResponse } from "@/types/api";

export function TriggerButton() {
  const [loading, setLoading] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const { mutate } = usePipelineRuns({ limit: 50 });
  const toast = useToast();

  async function executeTrigger() {
    if (loading) return;
    setLoading(true);
    setConfirmOpen(false);

    try {
      const res = await postAPI<TriggerResponse>("/api/v1/pipeline/trigger");
      toast.success(`Pipeline run started: ${res.run_id.slice(0, 8)}...`);
      await mutate();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Trigger failed";
      toast.error(`Pipeline trigger failed: ${message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <button
        onClick={() => setConfirmOpen(true)}
        disabled={loading}
        aria-label="Trigger data pipeline"
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

      <ConfirmDialog
        open={confirmOpen}
        title="Trigger Pipeline"
        description="This will start a full data pipeline run (Bronze → Silver → Gold). Are you sure?"
        confirmLabel="Start Pipeline"
        cancelLabel="Cancel"
        onConfirm={executeTrigger}
        onCancel={() => setConfirmOpen(false)}
      />
    </>
  );
}
