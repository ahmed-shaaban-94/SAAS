import { LoadingCard } from "@/components/loading-card";

export default function InsightsLoading() {
  return (
    <div>
      {/* Header skeleton */}
      <div className="mb-6">
        <div className="h-8 w-36 animate-pulse rounded bg-divider" />
        <div className="mt-2 h-4 w-72 animate-pulse rounded bg-divider" />
      </div>

      {/* AI Summary skeleton */}
      <LoadingCard lines={5} className="h-64" />

      {/* Anomaly list skeleton */}
      <div className="mt-6">
        <LoadingCard lines={6} className="h-72" />
      </div>
    </div>
  );
}
