import { LoadingCard } from "@/components/loading-card";

export default function SQLLabLoading() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48 animate-pulse rounded-lg bg-divider" />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[220px_1fr]">
        <LoadingCard />
        <div className="space-y-4">
          <LoadingCard />
          <LoadingCard />
        </div>
      </div>
    </div>
  );
}
