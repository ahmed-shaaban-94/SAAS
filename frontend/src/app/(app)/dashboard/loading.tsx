import { LoadingCard } from "@/components/loading-card";

export default function DashboardLoading() {
  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <div className="h-8 w-48 animate-pulse rounded bg-divider" />
        <div className="mt-2 h-4 w-72 animate-pulse rounded bg-divider" />
      </div>

      {/* Day Hero placeholder */}
      <div className="mb-4 h-10 w-full animate-pulse rounded-lg bg-divider/50" />

      {/* KPI Grid — 6 cards, 2 cols mobile, 3 cols desktop */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <LoadingCard key={i} lines={3} className={`stagger-${i + 1}`} />
        ))}
      </div>

      {/* Narrative summary placeholder */}
      <div className="mt-6 h-20 w-full animate-pulse rounded-xl bg-divider/40" />

      {/* Insight chips placeholder */}
      <div className="mt-3 flex gap-2">
        <div className="h-6 w-40 animate-pulse rounded-full bg-divider/30" />
        <div className="h-6 w-36 animate-pulse rounded-full bg-divider/30" />
        <div className="h-6 w-44 animate-pulse rounded-full bg-divider/30" />
      </div>

      {/* Trend charts */}
      <div className="mt-10 grid gap-6 lg:grid-cols-2">
        <LoadingCard lines={8} className="h-80" />
        <LoadingCard lines={8} className="h-80" />
      </div>
    </div>
  );
}
