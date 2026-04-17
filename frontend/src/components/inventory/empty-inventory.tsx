import { Package } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import {
  LoadSampleAction,
  UploadDataAction,
} from "@/components/shared/empty-state-actions";

export function EmptyInventory() {
  return (
    <EmptyState
      icon={<Package className="h-10 w-10 text-accent" aria-hidden="true" />}
      title="No inventory data yet"
      description="Track stock levels, days-of-supply, and reorder signals once data is loaded. Start with a curated sample or bring your own files."
      action={
        <div className="flex flex-wrap items-center justify-center gap-3">
          <LoadSampleAction />
          <UploadDataAction />
        </div>
      }
    />
  );
}
