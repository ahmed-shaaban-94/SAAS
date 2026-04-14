import { LoadingCard } from "@/components/loading-card";

export default function ExpiryLoading() {
  return (
    <div className="space-y-6">
      <LoadingCard className="h-10 w-48" />
      <LoadingCard className="h-6 w-96" />
      <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
        <LoadingCard className="h-[30rem]" />
        <LoadingCard className="h-[30rem]" />
      </div>
      <LoadingCard className="h-[24rem]" />
      <LoadingCard className="h-[24rem]" />
    </div>
  );
}
