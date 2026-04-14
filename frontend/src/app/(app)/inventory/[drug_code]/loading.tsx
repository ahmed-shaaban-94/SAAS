import { LoadingCard } from "@/components/loading-card";

export default function InventoryProductLoading() {
  return (
    <div className="space-y-6">
      <LoadingCard lines={2} />
      <div className="grid gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <LoadingCard key={index} lines={2} />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-2">
        <LoadingCard lines={8} className="h-[24rem]" />
        <LoadingCard lines={6} className="h-[24rem]" />
      </div>
    </div>
  );
}
