import { MessageSquarePlus } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChartCardProps {
  title: string;
  subtitle?: string;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  /** Chart identifier for the annotations feature */
  chartId?: string;
  /** Callback when user clicks the annotate button */
  onAnnotate?: () => void;
}

export function ChartCard({ title, subtitle, badge, actions, children, className, chartId, onAnnotate }: ChartCardProps) {
  return (
    <section
      aria-label={title}
      className={cn(
        "group rounded-xl border border-border bg-card p-5",
        "transition-all duration-300 hover:border-accent/30 hover:shadow-lg hover:shadow-accent/5",
        className,
      )}
    >
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
            {title}
          </h3>
          {subtitle && (
            <p className="mt-1 text-xl font-bold text-text-primary" data-kpi-value>
              {subtitle}
            </p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {onAnnotate && (
            <button
              onClick={onAnnotate}
              title="Add annotation"
              className="rounded-md p-1.5 text-text-secondary transition-colors hover:bg-divider hover:text-accent"
            >
              <MessageSquarePlus className="h-4 w-4" />
            </button>
          )}
          {actions}
          {badge}
        </div>
      </div>
      {children}
    </section>
  );
}
