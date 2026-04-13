import { cn } from "@/lib/utils";

interface StatItem {
  label: string;
  value: string;
  icon?: React.ComponentType<{ className?: string }>;
  trend?: "up" | "down" | "neutral";
}

interface SummaryStatsProps {
  stats: StatItem[];
  className?: string;
}

export function SummaryStats({ stats, className }: SummaryStatsProps) {
  return (
    <div className={cn("grid grid-cols-2 gap-4 md:grid-cols-4", className)}>
      {stats.map((stat, index) => {
        const Icon = stat.icon;
        return (
          <div
            key={stat.label}
            className={cn(
              "viz-panel viz-card-hover group relative overflow-hidden rounded-[1.5rem] p-4",
            )}
          >
            <div className="absolute inset-x-5 top-0 h-1 rounded-b-full bg-gradient-to-r from-chart-blue via-accent to-chart-purple opacity-80" />

            <div className="flex items-start justify-between">
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
                {stat.label}
              </p>
              {Icon && (
                <div className="viz-panel-soft flex h-8 w-8 items-center justify-center rounded-xl transition-colors group-hover:bg-accent/15">
                  <Icon className="h-3.5 w-3.5 text-accent" />
                </div>
              )}
            </div>
            <p className="mt-3 text-xl font-bold tracking-tight text-text-primary truncate sm:text-2xl" data-kpi-value title={stat.value}>
              {stat.value}
            </p>
          </div>
        );
      })}
    </div>
  );
}
