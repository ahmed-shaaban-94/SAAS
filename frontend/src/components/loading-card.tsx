import { cn } from "@/lib/utils";

interface LoadingCardProps {
  className?: string;
  lines?: number;
}

export function LoadingCard({ className, lines = 3 }: LoadingCardProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-xl border border-border bg-card/80 backdrop-blur-sm p-6",
        "animate-fade-in",
        className,
      )}
    >
      {/* Subtle top accent shimmer */}
      <div className="absolute inset-x-0 top-0 h-1 shimmer-accent" />

      <div className="shimmer-line mb-4 h-4 w-1/3 rounded-md" />
      <div className="shimmer-line mb-3 h-7 w-2/3 rounded-md" />
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="shimmer-line mb-2.5 h-3 rounded-md"
          style={{ width: `${90 - i * 12}%` }}
        />
      ))}

      {/* Pulse glow overlay */}
      <div className="absolute inset-0 rounded-xl loading-pulse-glow" />
    </div>
  );
}
