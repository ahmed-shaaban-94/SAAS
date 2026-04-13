import { cn } from "@/lib/utils";

interface AnalyticsSectionHeaderProps {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  accentClassName?: string;
  className?: string;
}

export function AnalyticsSectionHeader({
  title,
  icon: Icon,
  accentClassName,
  className,
}: AnalyticsSectionHeaderProps) {
  return (
    <div className={cn("mb-4 flex items-center gap-2", className)}>
      <div className="viz-panel-soft flex h-8 w-8 items-center justify-center rounded-xl">
        <Icon className={cn("h-3.5 w-3.5 text-accent", accentClassName)} />
      </div>
      <h2 className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
        {title}
      </h2>
      <div className="flex-1 section-divider" />
    </div>
  );
}
