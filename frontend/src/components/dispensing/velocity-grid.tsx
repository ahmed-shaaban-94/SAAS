"use client";

import { useVelocity } from "@/hooks/use-velocity";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { UploadDataAction } from "@/components/shared/empty-state-actions";
import { cn } from "@/lib/utils";
import type { VelocityClassification } from "@/types/dispensing";

type VelocityClass = VelocityClassification["velocity_class"];

const QUADRANT_CONFIG: Record<
  VelocityClass,
  { label: string; description: string; bg: string; text: string; badge: string }
> = {
  fast_mover: {
    label: "Fast Movers",
    description: "High dispense velocity",
    bg: "bg-green-500/10 border-green-500/30",
    text: "text-green-400",
    badge: "bg-green-500/20 text-green-400",
  },
  normal_mover: {
    label: "Normal Movers",
    description: "Average dispense velocity",
    bg: "bg-blue-500/10 border-blue-500/30",
    text: "text-blue-400",
    badge: "bg-blue-500/20 text-blue-400",
  },
  slow_mover: {
    label: "Slow Movers",
    description: "Below-average velocity",
    bg: "bg-amber-500/10 border-amber-500/30",
    text: "text-amber-400",
    badge: "bg-amber-500/20 text-amber-400",
  },
  dead_stock: {
    label: "Dead Stock",
    description: "No recent movement",
    bg: "bg-red-500/10 border-red-500/30",
    text: "text-red-400",
    badge: "bg-red-500/20 text-red-400",
  },
};

const QUADRANT_ORDER: VelocityClass[] = [
  "fast_mover",
  "normal_mover",
  "slow_mover",
  "dead_stock",
];

export function VelocityGrid() {
  const { data, isLoading } = useVelocity();

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <LoadingCard key={i} lines={3} className="h-48" />
        ))}
      </div>
    );
  }

  if (!data.length) return <EmptyState title="No velocity data" action={<UploadDataAction />} />;

  const grouped = QUADRANT_ORDER.reduce<Record<VelocityClass, VelocityClassification[]>>(
    (acc, cls) => {
      acc[cls] = data.filter((d) => d.velocity_class === cls);
      return acc;
    },
    {} as Record<VelocityClass, VelocityClassification[]>,
  );

  return (
    <div className="grid grid-cols-2 gap-4">
      {QUADRANT_ORDER.map((cls) => {
        const config = QUADRANT_CONFIG[cls];
        const items = grouped[cls];
        const topItems = items.slice(0, 5);

        return (
          <div
            key={cls}
            className={cn(
              "rounded-xl border p-4",
              config.bg,
            )}
          >
            <div className="mb-3 flex items-start justify-between">
              <div>
                <p className={cn("text-sm font-semibold", config.text)}>{config.label}</p>
                <p className="text-xs text-text-secondary">{config.description}</p>
              </div>
              <span
                className={cn(
                  "rounded-full px-2.5 py-1 text-xs font-bold",
                  config.badge,
                )}
              >
                {items.length}
              </span>
            </div>

            <ul className="space-y-1.5">
              {topItems.map((item) => (
                <li
                  key={item.product_key}
                  className="flex items-center justify-between text-xs"
                >
                  <span className="truncate text-text-secondary">{item.drug_name}</span>
                  <span className="ml-2 flex-shrink-0 font-medium text-text-primary">
                    {item.avg_daily_dispense.toFixed(1)}/d
                  </span>
                </li>
              ))}
              {items.length > 5 && (
                <li className="text-xs text-text-secondary/60">
                  +{items.length - 5} more
                </li>
              )}
            </ul>
          </div>
        );
      })}
    </div>
  );
}
