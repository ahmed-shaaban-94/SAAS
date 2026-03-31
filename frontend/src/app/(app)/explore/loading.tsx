import { LoadingCard } from "@/components/loading-card";

export default function ExploreLoading() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48 animate-pulse rounded-lg bg-divider" />
      <div className="h-4 w-96 animate-pulse rounded-lg bg-divider" />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
        <div className="space-y-4">
          <LoadingCard />
          <LoadingCard />
        </div>
        <LoadingCard />
      </div>
    </div>
  );
}
