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
        "viz-panel viz-card-hover group rounded-[1.75rem] border border-border/80 p-4 sm:p-6",
        className,
      )}
    >
      <div className="absolute inset-x-6 top-0 h-1 rounded-b-full bg-gradient-to-r from-chart-blue via-accent to-chart-amber opacity-90" />
      <div className="relative mb-5 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary/90">
            {title}
          </p>
          {subtitle && (
            <p className="mt-2 text-2xl font-bold tracking-tight text-text-primary sm:text-[2rem]" data-kpi-value>
              {subtitle}
            </p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {onAnnotate && (
            <button
              onClick={onAnnotate}
              title="Add annotation"
              className="viz-panel-soft rounded-xl p-2 text-text-secondary transition-colors hover:text-accent"
            >
              <MessageSquarePlus className="h-4 w-4" />
            </button>
          )}
          {actions}
          {badge}
        </div>
      </div>
      <div className="viz-panel-soft relative rounded-[1.4rem] p-3 sm:p-4">
        <div className="viz-grid-surface absolute inset-0 rounded-[1.4rem] opacity-30" />
        <div className="relative">{children}</div>
      </div>
    </section>
  );
}
