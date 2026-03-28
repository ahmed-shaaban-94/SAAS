import { LoadingCard } from "@/components/loading-card";

export default function PipelineLoading() {
  return (
    <div>
      {/* Header skeleton */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <div className="h-8 w-40 animate-pulse rounded bg-divider" />
          <div className="mt-2 h-4 w-72 animate-pulse rounded bg-divider" />
        </div>
        <div className="h-9 w-36 animate-pulse rounded-lg bg-divider" />
      </div>

      {/* KPI cards skeleton */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <LoadingCard key={i} lines={2} />
        ))}
      </div>

      {/* Table skeleton */}
      <div className="mt-6">
        <LoadingCard lines={6} className="h-64" />
      </div>
    </div>
  );
}
