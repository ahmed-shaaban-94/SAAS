import { LoadingCard } from "@/components/loading-card";

export default function PurchaseOrdersLoading() {
  return (
    <div>
      <div className="mb-6">
        <div className="h-8 w-52 animate-pulse rounded bg-divider" />
        <div className="mt-2 h-4 w-80 animate-pulse rounded bg-divider" />
      </div>
      <div className="grid grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <LoadingCard key={i} lines={1} />
        ))}
      </div>
      <div className="mt-6">
        <LoadingCard lines={10} className="h-80" />
      </div>
    </div>
  );
}
