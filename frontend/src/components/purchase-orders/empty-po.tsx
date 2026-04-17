import { ClipboardList } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { UploadDataAction } from "@/components/shared/empty-state-actions";

export function EmptyPurchaseOrders() {
  return (
    <EmptyState
      icon={<ClipboardList className="h-10 w-10 text-accent" aria-hidden="true" />}
      title="No purchase orders yet"
      description="Track supplier orders and deliveries once you import PO data from Excel."
      action={<UploadDataAction label="Import PO data" />}
    />
  );
}
