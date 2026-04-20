"use client";

import { useExpiryExposure } from "@/hooks/use-expiry-exposure";
import type { ExpiryExposureTier } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SkeletonEnhanced } from "@/components/ui/skeleton-enhanced";
import { cn } from "@/lib/utils";

export interface ExpiryExposureCardProps {
  /** Override the hook — useful for Storybook / tests. */
  tiers?: ExpiryExposureTier[];
  siteCode?: string;
  className?: string;
}

const TONE_CLASSES: Record<ExpiryExposureTier["tone"], string> = {
  red: "border-red-500/30 bg-red-500/[0.04] text-red-200",
  amber: "border-amber-500/30 bg-amber-500/[0.04] text-amber-200",
  green: "border-cyan-500/30 bg-cyan-500/[0.04] text-cyan-200",
};

function formatEgp(value: number): string {
  if (value >= 1_000_000) return `EGP ${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `EGP ${Math.round(value / 1_000)}K`;
  return `EGP ${Math.round(value)}`;
}

/**
 * Three-tier expiry exposure card (#506). Always renders exactly three
 * tiers in 30d → 60d → 90d order; the backend zero-fills missing tiers
 * so the layout is stable even for tenants with no near-expiry stock.
 */
export function ExpiryExposureCard({
  tiers,
  siteCode,
  className,
}: ExpiryExposureCardProps) {
  const hookResult = useExpiryExposure(siteCode);
  const data = tiers !== undefined ? tiers : hookResult.data;
  const isLoading = tiers === undefined && hookResult.isLoading;

  return (
    <Card className={cn("flex flex-col", className)}>
      <CardHeader className="pb-3">
        <CardTitle>Expiry Exposure</CardTitle>
      </CardHeader>
      <CardContent className="p-4 pt-0">
        {isLoading && (
          <div role="status" aria-label="Loading expiry exposure">
            <SkeletonEnhanced className="h-20" lines={3} />
          </div>
        )}
        {!isLoading && data && (
          <div className="grid grid-cols-3 gap-2">
            {data.map((tier) => (
              <div
                key={tier.tier}
                className={cn(
                  "flex flex-col gap-1 rounded-xl border p-3",
                  TONE_CLASSES[tier.tone] ?? TONE_CLASSES.green,
                )}
              >
                <span className="text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
                  {tier.label}
                </span>
                <span className="text-lg font-semibold text-text-primary tabular-nums">
                  {formatEgp(Number(tier.total_egp))}
                </span>
                <span className="text-[11px] text-text-secondary">
                  {tier.batch_count} batch{tier.batch_count === 1 ? "" : "es"}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
