import { Activity } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { LoadSampleAction, UploadDataAction } from "@/components/shared/empty-state-actions";

export function EmptyDispensing() {
  return (
    <EmptyState
      icon={<Activity className="h-10 w-10 text-accent" aria-hidden="true" />}
      title="No dispensing data yet"
      description="Dispense velocity, stockout risk, and reconciliation signals light up once transaction data is loaded. Start with a curated sample or bring your own files."
      action={
        <div className="flex flex-wrap items-center justify-center gap-3">
          <LoadSampleAction />
          <UploadDataAction />
        </div>
      }
    />
  );
}
