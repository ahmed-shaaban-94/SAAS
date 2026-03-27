import { cn } from "@/lib/utils";

interface LoadingCardProps {
  className?: string;
  lines?: number;
}

export function LoadingCard({ className, lines = 3 }: LoadingCardProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-lg border border-border bg-card p-6",
        className,
      )}
    >
      <div className="mb-4 h-4 w-1/3 rounded bg-divider" />
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="mb-2 h-3 rounded bg-divider"
          style={{ width: `${85 - i * 15}%` }}
        />
      ))}
    </div>
  );
}
