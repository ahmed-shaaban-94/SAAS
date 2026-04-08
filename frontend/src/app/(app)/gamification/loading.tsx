import { LoadingCard } from "@/components/loading-card";

export default function GamificationLoading() {
  return (
    <div>
      <div className="mb-6">
        <div className="h-8 w-48 animate-pulse rounded bg-divider" />
        <div className="mt-2 h-4 w-72 animate-pulse rounded bg-divider" />
      </div>
      {/* Tab bar skeleton */}
      <div className="mb-6 flex gap-1 rounded-xl border border-border bg-card p-1">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex-1 h-10 animate-pulse rounded-lg bg-divider" />
        ))}
      </div>
      {/* Podium skeleton */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <LoadingCard key={i} lines={3} />
        ))}
      </div>
      <LoadingCard lines={8} className="h-64" />
    </div>
  );
}
