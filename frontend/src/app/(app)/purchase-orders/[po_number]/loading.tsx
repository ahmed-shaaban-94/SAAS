import { LoadingCard } from "@/components/loading-card";

export default function PODetailLoading() {
  return (
    <div>
      <div className="mb-4 h-4 w-36 animate-pulse rounded bg-divider" />
      <div className="mb-6">
        <div className="h-8 w-52 animate-pulse rounded bg-divider" />
        <div className="mt-2 h-4 w-72 animate-pulse rounded bg-divider" />
      </div>
      <LoadingCard lines={2} />
      <div className="mt-4">
        <LoadingCard lines={4} />
      </div>
      <div className="mt-6">
        <LoadingCard lines={10} className="h-72" />
      </div>
    </div>
  );
}
