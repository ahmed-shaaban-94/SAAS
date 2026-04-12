import { LoadingCard } from "@/components/loading-card";

export default function BriefingLoading() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-56 animate-pulse rounded-lg bg-divider" />
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <LoadingCard key={i} lines={4} />
        ))}
      </div>
    </div>
  );
}
