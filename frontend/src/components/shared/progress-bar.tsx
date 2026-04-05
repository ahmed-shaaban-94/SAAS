import { cn } from "@/lib/utils";

interface ProgressBarProps {
  value: number;
  label?: string;
  className?: string;
}

export function ProgressBar({ value, label, className }: ProgressBarProps) {
  const clampedValue = Math.min(Math.max(value, 0), 100);
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div
        className="h-2 flex-1 overflow-hidden rounded-full bg-divider"
        role="progressbar"
        aria-valuenow={Math.round(clampedValue)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label ? `${label} progress` : "Progress"}
      >
        <div
          className="h-full rounded-full bg-gradient-to-r from-accent to-accent/60 transition-all duration-500"
          style={{ width: `${clampedValue}%` }}
        />
      </div>
      {label && (
        <span className="w-12 text-right text-xs font-medium text-text-secondary">
          {label}
        </span>
      )}
    </div>
  );
}
