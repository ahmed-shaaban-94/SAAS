import { Inbox } from "lucide-react";

interface EmptyStateProps {
  title?: string;
  description?: string;
}

export function EmptyState({
  title = "No data available",
  description = "Try adjusting your filters or check back later.",
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-border bg-card p-12">
      <Inbox className="h-12 w-12 text-text-secondary/50" />
      <h3 className="mt-4 text-lg font-medium text-text-primary">{title}</h3>
      <p className="mt-1 text-sm text-text-secondary">{description}</p>
    </div>
  );
}
