import { Package } from "lucide-react";

export function EmptyInventory() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Package className="h-12 w-12 text-muted-foreground mb-4" />
      <h3 className="text-lg font-semibold">No inventory data yet</h3>
      <p className="text-muted-foreground mt-2 max-w-sm">
        Upload stock receipt files or add inventory data manually to get
        started with inventory tracking.
      </p>
    </div>
  );
}
