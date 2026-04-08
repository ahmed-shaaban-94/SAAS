import { LoadingCard } from "@/components/loading-card";

export default function UploadLoading() {
  return (
    <div className="space-y-6">
      <LoadingCard className="h-10 w-48" />
      <LoadingCard className="h-6 w-96" />
      <LoadingCard className="h-64" />
    </div>
  );
}
