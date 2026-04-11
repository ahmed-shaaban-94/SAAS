import { type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

const ACCENT_STYLES = {
  amber: {
    border: "border-amber-500/30 dark:border-amber-400/25",
    iconBg: "bg-amber-500/10 dark:bg-amber-400/10",
    iconText: "text-amber-600 dark:text-amber-400",
    glow: "shadow-amber-500/5 dark:shadow-amber-400/5",
  },
  blue: {
    border: "border-blue-500/30 dark:border-blue-400/25",
    iconBg: "bg-blue-500/10 dark:bg-blue-400/10",
    iconText: "text-blue-600 dark:text-blue-400",
    glow: "shadow-blue-500/5 dark:shadow-blue-400/5",
  },
  green: {
    border: "border-emerald-500/30 dark:border-emerald-400/25",
    iconBg: "bg-emerald-500/10 dark:bg-emerald-400/10",
    iconText: "text-emerald-600 dark:text-emerald-400",
    glow: "shadow-emerald-500/5 dark:shadow-emerald-400/5",
  },
} as const;

interface FeatureCardProps {
  title: string;
  icon?: LucideIcon;
  accent?: keyof typeof ACCENT_STYLES;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export function FeatureCard({
  title,
  icon: Icon,
  accent = "amber",
  actions,
  children,
  className,
}: FeatureCardProps) {
  const styles = ACCENT_STYLES[accent];

  return (
    <section
      aria-label={title}
      className={cn(
        "group rounded-xl border bg-card p-4 sm:p-6",
        "transition-all duration-300 hover:shadow-lg",
        styles.border,
        styles.glow,
        className,
      )}
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {Icon && (
            <div className={cn("flex h-7 w-7 items-center justify-center rounded-lg", styles.iconBg)}>
              <Icon className={cn("h-4 w-4", styles.iconText)} />
            </div>
          )}
          <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
            {title}
          </h3>
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>
      {children}
    </section>
  );
}
