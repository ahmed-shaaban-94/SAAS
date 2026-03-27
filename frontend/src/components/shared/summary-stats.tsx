import { cn } from "@/lib/utils";

interface StatItem {
  label: string;
  value: string;
}

interface SummaryStatsProps {
  stats: StatItem[];
  className?: string;
}

export function SummaryStats({ stats, className }: SummaryStatsProps) {
  return (
    <div className={cn("grid grid-cols-2 gap-4 md:grid-cols-4", className)}>
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="rounded-lg border border-border bg-card p-4"
        >
          <p className="text-sm text-text-secondary">{stat.label}</p>
          <p className="mt-1 text-lg font-bold text-text-primary">
            {stat.value}
          </p>
        </div>
      ))}
    </div>
  );
}
