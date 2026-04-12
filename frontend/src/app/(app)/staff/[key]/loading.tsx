import { LoadingCard } from "@/components/loading-card";

export default function StaffDetailLoading() {
  return (
    <div className="space-y-6">
      <LoadingCard lines={2} />
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <LoadingCard key={i} lines={2} />
        ))}
      </div>
      <LoadingCard lines={8} className="h-80" />
    </div>
  );
}
