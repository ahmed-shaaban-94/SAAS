import { LoadingCard } from "@/components/loading-card";

export default function BrandingLoading() {
  return (
    <div>
      <div className="mb-6">
        <div className="h-8 w-48 animate-pulse rounded bg-divider" />
        <div className="mt-2 h-4 w-72 animate-pulse rounded bg-divider" />
      </div>
      <div className="space-y-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <LoadingCard key={i} lines={4} />
        ))}
      </div>
    </div>
  );
}
