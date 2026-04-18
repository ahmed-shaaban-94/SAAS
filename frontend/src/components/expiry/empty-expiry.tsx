import { CalendarClock } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import {
  LoadSampleAction,
  UploadDataAction,
} from "@/components/shared/empty-state-actions";

export function EmptyExpiry() {
  return (
    <EmptyState
      icon={<CalendarClock className="h-10 w-10 text-accent" aria-hidden="true" />}
      title="No batch data yet"
      description="Expiry tracking, FEFO ordering, and near-expiry alerts light up once batch records are loaded. Start with sample data to explore, or bring your own file."
      action={
        <div className="flex flex-wrap items-center justify-center gap-3">
          <LoadSampleAction />
          <UploadDataAction />
        </div>
      }
    />
  );
}
