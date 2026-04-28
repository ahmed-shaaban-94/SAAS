/**
 * Pure merge + rank logic for the /dashboard AttentionQueue.
 * No React, no SWR — just transforms raw hook payloads into a ranked list.
 */

export type AttentionType = "expiry" | "stock" | "anomaly" | "pipeline";
export type AttentionSeverity = "red" | "amber" | "blue";

export interface AttentionAlert {
  id: string;
  type: AttentionType;
  severity: AttentionSeverity;
  title: string;
  impactEgp?: number;
  impactCount?: number;
  where?: string;
  detectedAt?: string;
  drillHref?: string;
}

const SEVERITY_WEIGHT: Record<AttentionSeverity, number> = {
  red: 100,
  amber: 50,
  blue: 10,
};

export function scoreAlert(a: AttentionAlert): number {
  const sev = SEVERITY_WEIGHT[a.severity];
  const impact = Math.min(50, (a.impactEgp ?? 0) / 10_000);
  let recency = 0;
  if (a.detectedAt) {
    const ms = new Date(a.detectedAt).getTime();
    if (Number.isFinite(ms)) {
      const hoursSince = Math.max(0, (Date.now() - ms) / 3_600_000);
      recency = Math.max(0, 30 - hoursSince) / 2;
    }
  }
  return sev + impact + recency;
}

export function rankAlerts(alerts: AttentionAlert[]): AttentionAlert[] {
  return [...alerts].sort((x, y) => {
    const sx = scoreAlert(x);
    const sy = scoreAlert(y);
    if (sy !== sx) return sy - sx;
    return x.id.localeCompare(y.id);
  });
}

// --- Raw payload shapes (kept loose — hooks evolve) ---

interface ExpiryCalendarBucket {
  bucket: string;
  days_out: number;
  exposure_egp: number;
  batch_count: number;
}

interface ReorderAlertRow {
  drug_code: string;
  drug_name: string;
  on_hand: number;
  reorder_point: number;
  site_name: string;
  margin_impact_egp?: number;
}

interface AnomalyCardRow {
  id: string;
  title: string;
  severity: string;
  impact_egp?: number | null;
  detected_at?: string;
  site_name?: string;
}

interface PipelinePayload {
  last_run?: { status?: string; at?: string } | null;
  checks_failed?: number;
}

export interface MergeInputs {
  calendar: ExpiryCalendarBucket[] | undefined;
  exposure: { total_egp?: number } | undefined;
  reorder: ReorderAlertRow[] | undefined;
  anomalies: AnomalyCardRow[] | undefined;
  pipeline: PipelinePayload | null | undefined;
}

export function mergeAttentionAlerts(input: MergeInputs): AttentionAlert[] {
  const out: AttentionAlert[] = [];

  // Expiry: one row per bucket with days_out <= 30 and exposure_egp > 0
  for (const b of input.calendar ?? []) {
    if (b.days_out > 30 || b.exposure_egp <= 0) continue;
    out.push({
      id: `expiry-${b.bucket}`,
      type: "expiry",
      severity: b.days_out <= 14 ? "red" : "amber",
      title: `${b.batch_count} batches expire within ${b.days_out} days`,
      impactEgp: b.exposure_egp,
      where: "All branches",
      drillHref: undefined,
    });
  }

  // Stock: group reorder alerts by drug_code
  const byDrug = new Map<string, ReorderAlertRow[]>();
  for (const r of input.reorder ?? []) {
    const arr = byDrug.get(r.drug_code) ?? [];
    arr.push(r);
    byDrug.set(r.drug_code, arr);
  }
  const stockGroups = Array.from(byDrug.entries())
    .map(([code, rows]) => ({
      code,
      rows,
      totalImpact: rows.reduce((s, r) => s + (r.margin_impact_egp ?? 0), 0),
    }))
    .sort((a, b) => {
      // Primary: EGP margin impact desc.
      if (b.totalImpact !== a.totalImpact) return b.totalImpact - a.totalImpact;
      // Tiebreaker: more affected branches = higher priority. Without this,
      // when margin_impact_egp is unavailable (current hook shape), ranking
      // would fall back to map-iteration order.
      return b.rows.length - a.rows.length;
    })
    .slice(0, 20);

  for (const g of stockGroups) {
    const sites = Array.from(new Set(g.rows.map((r) => r.site_name)));
    const worstOnHand = Math.min(...g.rows.map((r) => r.on_hand));
    out.push({
      id: `stock-${g.code}`,
      type: "stock",
      severity: worstOnHand <= 0 ? "red" : "amber",
      title: `${g.rows[0].drug_name} below reorder${worstOnHand <= 0 ? " — OUT OF STOCK" : ""}`,
      impactEgp: g.totalImpact > 0 ? g.totalImpact : undefined,
      where: sites.length === 1 ? sites[0] : `${sites.length} branches`,
      drillHref: undefined,
    });
  }

  // Anomaly: already server-ranked; map 1:1
  for (const a of input.anomalies ?? []) {
    const sev: AttentionSeverity =
      a.severity === "red" || a.severity === "critical" ? "red"
      : a.severity === "amber" || a.severity === "warning" ? "amber"
      : "blue";
    out.push({
      id: `anomaly-${a.id}`,
      type: "anomaly",
      severity: sev,
      title: a.title,
      impactEgp: a.impact_egp ?? undefined,
      where: a.site_name ?? "All branches",
      detectedAt: a.detected_at,
      drillHref: undefined,
    });
  }

  // Pipeline: surface only when failed or checks_failed > 0
  const p = input.pipeline;
  if (p && ((p.last_run?.status === "failed") || (p.checks_failed ?? 0) > 0)) {
    out.push({
      id: "pipeline-last-run",
      type: "pipeline",
      severity: "red",
      title:
        p.last_run?.status === "failed"
          ? "Pipeline last run failed"
          : `Pipeline quality: ${p.checks_failed} check(s) failing`,
      where: "Data plumbing",
      detectedAt: p.last_run?.at,
      drillHref: `/quality`,
    });
  }

  return rankAlerts(out);
}
