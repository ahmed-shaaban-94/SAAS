import { LoadingCard } from "@/components/loading-card";

export default function InventoryLoading() {
  return (
    <div className="space-y-6">
      <LoadingCard className="h-10 w-48" />
      <LoadingCard className="h-6 w-96" />
      <div className="grid gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <LoadingCard key={index} className="h-24" />
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <LoadingCard className="h-80" />
        <LoadingCard className="h-80" />
      </div>
      <LoadingCard className="h-80" />
    </div>
  );
}
