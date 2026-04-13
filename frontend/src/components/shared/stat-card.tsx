import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string;
  className?: string;
}

export function StatCard({ label, value, className }: StatCardProps) {
  return (
    <div className={cn("viz-panel viz-card-hover glow-card rounded-[1.4rem] p-4", className)}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
        {label}
      </p>
      <p className="mt-2 text-2xl font-bold tracking-tight text-text-primary" data-kpi-value>{value}</p>
    </div>
  );
}
