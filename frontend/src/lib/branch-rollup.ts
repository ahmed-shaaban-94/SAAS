/**
 * Pure client-side per-site aggregation.
 * Joins useSites (RankingResult) with useReorderAlerts and useExpiryCalendar
 * so BranchListRollup can display revenue + risk + expiry without a backend change.
 */

export interface BranchRollupRow {
  key: number;
  name: string;
  revenue: number;
  riskCount: number;
  expiryExposureEgp: number;
  trend: "up" | "down" | "flat";
}

interface RankingItem {
  rank: number;
  key: number;
  name: string;
  value: number;
  pct_of_total: number;
}

interface RankingResult {
  items: RankingItem[];
  total: number;
}

interface ReorderRow {
  drug_code: string;
  drug_name: string;
  on_hand: number;
  reorder_point: number;
  site_name: string;
}

interface CalendarBucket {
  bucket: string;
  days_out: number;
  exposure_egp: number;
  batch_count: number;
  site_name?: string;
}

export interface BranchRollupInputs {
  sites: RankingResult | undefined;
  reorder: ReorderRow[] | undefined;
  calendar: CalendarBucket[] | undefined;
}

export function buildBranchRollup(input: BranchRollupInputs): BranchRollupRow[] {
  if (!input.sites?.items?.length) return [];

  const riskBySite = new Map<string, number>();
  for (const r of input.reorder ?? []) {
    riskBySite.set(r.site_name, (riskBySite.get(r.site_name) ?? 0) + 1);
  }

  const expiryBySite = new Map<string, number>();
  for (const b of input.calendar ?? []) {
    if (b.days_out > 30 || !b.site_name) continue;
    expiryBySite.set(b.site_name, (expiryBySite.get(b.site_name) ?? 0) + b.exposure_egp);
  }

  return input.sites.items.map((item) => ({
    key: item.key,
    name: item.name,
    revenue: item.value,
    riskCount: riskBySite.get(item.name) ?? 0,
    expiryExposureEgp: expiryBySite.get(item.name) ?? 0,
    trend: "flat" as const,
  }));
}
