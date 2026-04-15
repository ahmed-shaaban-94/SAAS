import { LoadingCard } from "@/components/loading-card";

export default function SuppliersLoading() {
  return (
    <div>
      <div className="mb-6">
        <div className="h-8 w-36 animate-pulse rounded bg-divider" />
        <div className="mt-2 h-4 w-56 animate-pulse rounded bg-divider" />
      </div>
      <LoadingCard lines={8} className="h-72" />
      <div className="mt-6">
        <LoadingCard lines={6} className="h-80" />
      </div>
    </div>
  );
}
