import { LoadingCard } from "@/components/loading-card";

export default function SitesLoading() {
  return (
    <div>
      <div className="mb-6">
        <div className="h-8 w-48 animate-pulse rounded bg-divider" />
        <div className="mt-2 h-4 w-72 animate-pulse rounded bg-divider" />
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {Array.from({ length: 2 }).map((_, i) => (
          <LoadingCard key={i} lines={2} />
        ))}
      </div>
      <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2">
        <LoadingCard lines={6} className="h-64" />
        <LoadingCard lines={6} className="h-64" />
      </div>
    </div>
  );
}
