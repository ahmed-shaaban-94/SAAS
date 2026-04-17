import { ClipboardList } from "lucide-react";

export function EmptyPurchaseOrders() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <ClipboardList className="h-12 w-12 text-muted-foreground mb-4" />
      <h3 className="text-lg font-semibold">No purchase orders yet</h3>
      <p className="text-muted-foreground mt-2 max-w-sm">
        Create your first purchase order or import PO data from Excel to
        start tracking supplier orders and deliveries.
      </p>
    </div>
  );
}
