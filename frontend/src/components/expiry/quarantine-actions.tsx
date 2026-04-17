"use client";

import { useState } from "react";
import { postAPI } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { useToast } from "@/components/ui/toast";
import type { ExpiryAlert } from "@/types/expiry";

interface QuarantineActionsProps {
  batch: ExpiryAlert;
  onComplete?: () => void;
}

export function QuarantineActions({ batch, onComplete }: QuarantineActionsProps) {
  const { success, error } = useToast();
  const [mode, setMode] = useState<"quarantine" | "writeoff" | null>(null);
  const [isPending, setIsPending] = useState(false);

  async function handleConfirm() {
    if (!mode) return;
    setIsPending(true);

    try {
      if (mode === "quarantine") {
        await postAPI("/api/v1/expiry/quarantine", {
          drug_code: batch.drug_code,
          site_code: batch.site_code,
          batch_number: batch.batch_number,
          reason: "Quarantined from expiry dashboard",
        });
        success(`Batch ${batch.batch_number} quarantined`);
      } else {
        await postAPI("/api/v1/expiry/write-off", {
          drug_code: batch.drug_code,
          site_code: batch.site_code,
          batch_number: batch.batch_number,
          quantity: batch.current_quantity,
          reason: "Written off from expiry dashboard",
        });
        success(`Batch ${batch.batch_number} written off`);
      }

      setMode(null);
      onComplete?.();
    } catch (actionError) {
      error(actionError instanceof Error ? actionError.message : "Expiry action failed");
    } finally {
      setIsPending(false);
    }
  }

  return (
    <>
      <div className="flex items-center justify-end gap-2">
        <Button variant="outline" size="sm" onClick={() => setMode("quarantine")}>
          Quarantine
        </Button>
        <Button variant="destructive" size="sm" onClick={() => setMode("writeoff")}>
          Write Off
        </Button>
      </div>

      <ConfirmDialog
        open={mode !== null}
        title={mode === "quarantine" ? "Quarantine batch?" : "Write off batch?"}
        description={
          mode === "quarantine"
            ? `Batch ${batch.batch_number} will be moved to quarantine status.`
            : `Batch ${batch.batch_number} will be fully written off using its current quantity.`
        }
        confirmLabel={isPending ? "Working..." : mode === "quarantine" ? "Confirm quarantine" : "Confirm write-off"}
        variant={mode === "writeoff" ? "danger" : "default"}
        onConfirm={handleConfirm}
        onCancel={() => !isPending && setMode(null)}
      />
    </>
  );
}
