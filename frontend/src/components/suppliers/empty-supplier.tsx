import { Truck } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { UploadDataAction } from "@/components/shared/empty-state-actions";

export function EmptySupplier() {
  return (
    <EmptyState
      icon={<Truck className="h-10 w-10 text-accent" aria-hidden="true" />}
      title="No suppliers on record"
      description="Supplier performance, lead times, and fill rates appear once supplier data is linked to purchase orders."
      action={
        <div className="flex flex-wrap items-center justify-center gap-3">
          <UploadDataAction />
        </div>
      }
    />
  );
}
