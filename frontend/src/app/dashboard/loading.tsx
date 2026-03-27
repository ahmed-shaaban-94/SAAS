import { LoadingCard } from "@/components/loading-card";

export default function DashboardLoading() {
  return (
    <div>
      <div className="mb-6">
        <div className="h-8 w-48 animate-pulse rounded bg-divider" />
        <div className="mt-2 h-4 w-72 animate-pulse rounded bg-divider" />
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-7">
        {Array.from({ length: 7 }).map((_, i) => (
          <LoadingCard key={i} lines={2} />
        ))}
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <LoadingCard lines={8} className="h-80" />
        <LoadingCard lines={8} className="h-80" />
      </div>
    </div>
  );
}
