import { LoadingCard } from "@/components/loading-card";

export default function ReportLoading() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48 animate-pulse rounded-lg bg-divider" />
      <LoadingCard lines={6} className="h-96" />
    </div>
  );
}
