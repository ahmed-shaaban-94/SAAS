import { LoadingCard } from "@/components/loading-card";

export default function DispensingLoading() {
  return (
    <div>
      <div className="mb-6">
        <div className="h-8 w-52 animate-pulse rounded bg-divider" />
        <div className="mt-2 h-4 w-80 animate-pulse rounded bg-divider" />
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {Array.from({ length: 10 }).map((_, i) => (
          <LoadingCard key={i} lines={2} />
        ))}
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <LoadingCard lines={8} className="h-80" />
        <LoadingCard lines={8} className="h-80" />
      </div>
      <div className="mt-6">
        <LoadingCard lines={6} className="h-64" />
      </div>
    </div>
  );
}
