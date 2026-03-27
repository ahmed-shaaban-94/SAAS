import { cn } from "@/lib/utils";

interface ProgressBarProps {
  value: number;
  label?: string;
  className?: string;
}

export function ProgressBar({ value, label, className }: ProgressBarProps) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-divider">
        <div
          className="h-full rounded-full bg-accent transition-all"
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
      {label && (
        <span className="w-12 text-right text-xs text-text-secondary">
          {label}
        </span>
      )}
    </div>
  );
}
