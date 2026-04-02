import { LoadingCard } from "@/components/loading-card";

export default function GoalsLoading() {
  return (
    <div className="space-y-6">
      <LoadingCard className="h-10 w-48" />
      <LoadingCard className="h-6 w-96" />
      <div className="grid gap-6 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <LoadingCard key={i} className="h-32" />
        ))}
      </div>
      <LoadingCard className="h-80" />
    </div>
  );
}
