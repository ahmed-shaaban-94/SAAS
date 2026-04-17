import { CalendarClock } from "lucide-react";

export function EmptyExpiry() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <CalendarClock className="h-12 w-12 text-muted-foreground mb-4" />
      <h3 className="text-lg font-semibold">No batch data yet</h3>
      <p className="text-muted-foreground mt-2 max-w-sm">
        Import batch records with expiry dates to enable expiry tracking,
        FEFO ordering, and near-expiry alerts.
      </p>
    </div>
  );
}
