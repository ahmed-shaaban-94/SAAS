import { cn } from "@/lib/utils";

interface SkeletonEnhancedProps {
  className?: string;
  lines?: number;
}

/**
 * Enhanced skeleton loading with shimmer + subtle breathing animation.
 */
export function SkeletonEnhanced({ className, lines = 3 }: SkeletonEnhancedProps) {
  return (
    <div className={cn("space-y-3", className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "h-4 rounded-md bg-divider animate-shimmer",
            i === lines - 1 ? "w-3/4" : "w-full",
          )}
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  );
}
