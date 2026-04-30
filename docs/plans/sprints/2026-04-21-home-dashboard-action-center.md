# Home Dashboard Action-Center Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure `/dashboard` into a four-zone action-center layout: AttentionQueue (hero) → KpiStrip → two evidence rows → plumbing footer. No new backend endpoints.

**Architecture:** Three new presentational components (`AttentionQueue`, `KpiStrip`, `DashboardFooterBar`) and two pure helper modules (`attention-queue.ts` for merge/rank, `branch-rollup.ts` for per-site aggregation from existing hooks). `/dashboard/page.tsx` is rewritten to compose the new zone layout. Three obsolete widgets (`AlertBanner`, `AnomalyFeed`, `PipelineHealthCard`) are deleted after the migration because `/dashboard` is their only consumer.

**Tech Stack:** Next.js 14 + TypeScript + Tailwind + Recharts + SWR + Vitest + Playwright.

**Spec:** `docs/plans/specs/2026-04-21-home-dashboard-action-center-design.md`

---

## Resolved open questions (from the spec)

| Question | Resolution |
|---|---|
| Does `useSites` include per-site revenue and risk counts? | Returns `RankingResult` (`{ items: [{ key, name, value, pct_of_total }] }`). Revenue = `value`. Risk + expiry **derived client-side** in new `branch-rollup.ts` from already-loaded `useReorderAlerts` + `useExpiryCalendar`. **No backend change.** |
| Does `/anomalies` page exist? | No. "All anomalies →" footer link points to existing `/insights`. No new page. |
| Other consumers of `AlertBanner`, `AnomalyFeed`, `PipelineHealthCard`? | None — only `/dashboard/page.tsx`. **Delete all three** in Task 11 after migration. |
| Which Playwright specs change? | `frontend/e2e/dashboard.spec.ts` only (selectors for widget headings). `dashboard-v2-redirect.spec.ts` untouched. |

---

## File structure (decomposition lock-in)

### New files

| Path | Purpose | Approx LOC |
|---|---|---|
| `frontend/src/lib/attention-queue.ts` | Pure merge + rank logic. No React, no SWR. | ~150 |
| `frontend/src/lib/branch-rollup.ts` | Pure per-site aggregation from RankingItems + reorder alerts + expiry calendar. | ~80 |
| `frontend/src/__tests__/lib/attention-queue.test.ts` | Vitest unit tests for merge/rank. | ~200 |
| `frontend/src/__tests__/lib/branch-rollup.test.ts` | Vitest unit tests for branch rollup. | ~100 |
| `frontend/src/components/dashboard/new/AttentionQueue.tsx` | Hero widget composing merged alerts. | ~250 |
| `frontend/src/components/dashboard/new/AttentionRow.tsx` | One alert row. | ~90 |
| `frontend/src/components/dashboard/new/AttentionChips.tsx` | Filter chip bar. | ~60 |
| `frontend/src/components/dashboard/new/KpiStrip.tsx` | Dense 4-pill KPI strip. | ~180 |
| `frontend/src/components/dashboard/new/DashboardFooterBar.tsx` | Footer chips: pipeline + channels popover + links. | ~140 |
| `frontend/src/components/dashboard/new/BranchListRollup.tsx` | Enhanced branch list with risk/exposure columns. | ~140 |

### Modified files

| Path | Change |
|---|---|
| `frontend/src/components/dashboard/new/index.ts` | Add new exports; remove deleted-widget exports at end of plan. |
| `frontend/src/app/dashboard/page.tsx` | Full rewrite of the JSX body (hooks block kept as-is; imports change). |
| `frontend/e2e/dashboard.spec.ts` | Update widget-heading selectors to match new layout. |

### Deleted files (Task 11)

- `frontend/src/components/dashboard/new/alert-banner.tsx`
- `frontend/src/components/dashboard/new/anomaly-feed.tsx`
- `frontend/src/components/dashboard/new/pipeline-health.tsx` (only `PipelineHealthCard` — the inline chip lives in `DashboardFooterBar`)

---

## Type contracts (referenced across tasks)

Defined in `frontend/src/lib/attention-queue.ts` — reused by `AttentionQueue.tsx`, `AttentionRow.tsx`, and tests.

```typescript
export type AttentionType = "expiry" | "stock" | "anomaly" | "pipeline";
export type AttentionSeverity = "red" | "amber" | "blue";

export interface AttentionAlert {
  id: string;
  type: AttentionType;
  severity: AttentionSeverity;
  title: string;
  impactEgp?: number;        // when monetary impact is known
  impactCount?: number;      // alternative: row/SKU count
  where?: string;            // branch name or "All branches"
  detectedAt?: string;       // ISO timestamp
  drillHref: string;         // deep-link target
}
```

And in `frontend/src/lib/branch-rollup.ts`:

```typescript
export interface BranchRollupRow {
  key: number;
  name: string;
  revenue: number;
  riskCount: number;         // reorder alerts grouped by site
  expiryExposureEgp: number; // summed from calendar buckets ≤30 days
  trend: "up" | "down" | "flat";
}
```

---

## Task 0: Baseline — verify the worktree is green before we start

**Files:** none modified.

- [ ] **Step 1: Confirm working tree is clean and on the right branch**

Run:
```bash
git status
git log --oneline -1
```

Expected: clean tree, HEAD is the design-spec commit (`6249c29f docs: home dashboard action-center redesign spec`).

- [ ] **Step 2: Run frontend typecheck**

Run:
```bash
cd frontend && npx tsc --noEmit
```

Expected: exit 0.

- [ ] **Step 3: Run existing Vitest suite**

Run:
```bash
cd frontend && npm run test -- --run
```

Expected: all passing. Record pass count for regression comparison at the end.

- [ ] **Step 4: (Optional) Run dashboard E2E in headed mode to eyeball current layout**

Run:
```bash
cd frontend && npx playwright test e2e/dashboard.spec.ts
```

Expected: passes (skipped tests when `CI` env unset is expected). Record which tests ran.

---

## Task 1: Attention-queue merge/rank pure module (TDD — tests first)

**Files:**
- Create: `frontend/src/__tests__/lib/attention-queue.test.ts`
- Create: `frontend/src/lib/attention-queue.ts`

- [ ] **Step 1: Write failing tests for score calculation and merge**

Create `frontend/src/__tests__/lib/attention-queue.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import {
  rankAlerts,
  mergeAttentionAlerts,
  scoreAlert,
  type AttentionAlert,
} from "@/lib/attention-queue";

const nowIso = () => new Date().toISOString();
const hoursAgo = (h: number) =>
  new Date(Date.now() - h * 60 * 60 * 1000).toISOString();

describe("scoreAlert", () => {
  it("weights severity: red=100, amber=50, blue=10", () => {
    const base = { id: "a", type: "anomaly", title: "t", drillHref: "/x" } as const;
    expect(scoreAlert({ ...base, severity: "red" } as AttentionAlert)).toBeGreaterThan(
      scoreAlert({ ...base, severity: "amber" } as AttentionAlert),
    );
    expect(scoreAlert({ ...base, severity: "amber" } as AttentionAlert)).toBeGreaterThan(
      scoreAlert({ ...base, severity: "blue" } as AttentionAlert),
    );
  });

  it("adds impact weight capped at 50 (EGP 500K saturates)", () => {
    const base = {
      id: "a",
      type: "stock" as const,
      severity: "amber" as const,
      title: "t",
      drillHref: "/x",
    };
    const small: AttentionAlert = { ...base, impactEgp: 10_000 };
    const huge: AttentionAlert = { ...base, impactEgp: 10_000_000 };
    expect(scoreAlert(huge) - scoreAlert(small)).toBeCloseTo(49, 0);
  });

  it("adds recency weight up to 15 (detectedAt within 30h)", () => {
    const base = {
      id: "a",
      type: "anomaly" as const,
      severity: "amber" as const,
      title: "t",
      drillHref: "/x",
    };
    const fresh: AttentionAlert = { ...base, detectedAt: nowIso() };
    const stale: AttentionAlert = { ...base, detectedAt: hoursAgo(48) };
    expect(scoreAlert(fresh)).toBeGreaterThan(scoreAlert(stale));
  });
});

describe("rankAlerts", () => {
  it("sorts red before amber before blue", () => {
    const alerts: AttentionAlert[] = [
      { id: "1", type: "stock", severity: "blue", title: "b", drillHref: "/" },
      { id: "2", type: "stock", severity: "red", title: "r", drillHref: "/" },
      { id: "3", type: "stock", severity: "amber", title: "a", drillHref: "/" },
    ];
    expect(rankAlerts(alerts).map((x) => x.severity)).toEqual(["red", "amber", "blue"]);
  });

  it("tie-breaks stably by id", () => {
    const alerts: AttentionAlert[] = [
      { id: "b", type: "anomaly", severity: "amber", title: "x", drillHref: "/" },
      { id: "a", type: "anomaly", severity: "amber", title: "x", drillHref: "/" },
    ];
    expect(rankAlerts(alerts).map((x) => x.id)).toEqual(["a", "b"]);
  });
});

describe("mergeAttentionAlerts", () => {
  it("maps expiry buckets ≤30 days into one row per bucket; red if ≤14d", () => {
    const calendar = [
      { bucket: "0-7", days_out: 7, exposure_egp: 12_000, batch_count: 3 },
      { bucket: "15-30", days_out: 30, exposure_egp: 8_000, batch_count: 2 },
      { bucket: "31+", days_out: 60, exposure_egp: 99_999, batch_count: 9 },
    ];
    const merged = mergeAttentionAlerts({
      calendar,
      exposure: undefined,
      reorder: [],
      anomalies: [],
      pipeline: null,
    });
    const expiryAlerts = merged.filter((a) => a.type === "expiry");
    expect(expiryAlerts).toHaveLength(2);
    expect(expiryAlerts.find((a) => a.title.includes("7"))?.severity).toBe("red");
    expect(expiryAlerts.find((a) => a.title.includes("30"))?.severity).toBe("amber");
  });

  it("groups reorder alerts by drug_code, red if on_hand<=0, amber otherwise", () => {
    const reorder = [
      { drug_code: "AMX500", drug_name: "Amox", on_hand: 0, reorder_point: 10, site_name: "B1", margin_impact_egp: 500 },
      { drug_code: "AMX500", drug_name: "Amox", on_hand: 0, reorder_point: 10, site_name: "B2", margin_impact_egp: 300 },
      { drug_code: "PAN40", drug_name: "Pan", on_hand: 3, reorder_point: 10, site_name: "B1", margin_impact_egp: 100 },
    ];
    const merged = mergeAttentionAlerts({
      calendar: [],
      exposure: undefined,
      reorder,
      anomalies: [],
      pipeline: null,
    });
    const stockAlerts = merged.filter((a) => a.type === "stock");
    expect(stockAlerts).toHaveLength(2);
    const amx = stockAlerts.find((a) => a.id === "stock-AMX500")!;
    expect(amx.severity).toBe("red");
    expect(amx.where).toBe("2 branches");
    expect(amx.impactEgp).toBe(800);
  });

  it("maps anomaly cards preserving server severity", () => {
    const anomalies = [
      { id: "an1", title: "Revenue dip", severity: "red", impact_egp: 20_000, detected_at: nowIso() },
      { id: "an2", title: "Minor noise", severity: "blue", impact_egp: null, detected_at: nowIso() },
    ];
    const merged = mergeAttentionAlerts({
      calendar: [],
      exposure: undefined,
      reorder: [],
      anomalies,
      pipeline: null,
    });
    expect(merged.filter((a) => a.type === "anomaly")).toHaveLength(2);
  });

  it("surfaces pipeline only when failed or checks_failed>0", () => {
    const merged1 = mergeAttentionAlerts({
      calendar: [],
      exposure: undefined,
      reorder: [],
      anomalies: [],
      pipeline: { last_run: { status: "success", at: nowIso() }, checks_failed: 0 },
    });
    expect(merged1.filter((a) => a.type === "pipeline")).toHaveLength(0);

    const merged2 = mergeAttentionAlerts({
      calendar: [],
      exposure: undefined,
      reorder: [],
      anomalies: [],
      pipeline: { last_run: { status: "failed", at: nowIso() }, checks_failed: 2 },
    });
    expect(merged2.filter((a) => a.type === "pipeline")).toHaveLength(1);
  });

  it("returns empty array when no inputs have data", () => {
    expect(
      mergeAttentionAlerts({
        calendar: [],
        exposure: undefined,
        reorder: [],
        anomalies: [],
        pipeline: null,
      }),
    ).toEqual([]);
  });
});
```

- [ ] **Step 2: Run the tests to confirm they fail with "module not found"**

Run:
```bash
cd frontend && npm run test -- --run src/__tests__/lib/attention-queue.test.ts
```

Expected: all tests fail with "Cannot find module '@/lib/attention-queue'" or similar.

- [ ] **Step 3: Write the minimal implementation**

Create `frontend/src/lib/attention-queue.ts`:

```typescript
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
  drillHref: string;
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
    const hoursSince = Math.max(0, (Date.now() - new Date(a.detectedAt).getTime()) / 3_600_000);
    recency = Math.max(0, 30 - hoursSince) / 2;
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
      drillHref: "/expiry",
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
    .sort((a, b) => b.totalImpact - a.totalImpact)
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
      drillHref: `/inventory?filter=below-reorder`,
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
      drillHref: `/insights`,
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
```

- [ ] **Step 4: Run tests to confirm they pass**

Run:
```bash
cd frontend && npm run test -- --run src/__tests__/lib/attention-queue.test.ts
```

Expected: all 10 tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/attention-queue.ts frontend/src/__tests__/lib/attention-queue.test.ts
git commit -m "feat(frontend): attention-queue merge+rank pure module with tests"
```

---

## Task 2: Branch rollup pure module (TDD — tests first)

Derives per-site `revenue / riskCount / expiryExposureEgp / trend` from already-loaded hooks. Replaces the "extend `/api/v1/analytics/sites`" option with a client-side join.

**Files:**
- Create: `frontend/src/__tests__/lib/branch-rollup.test.ts`
- Create: `frontend/src/lib/branch-rollup.ts`

- [ ] **Step 1: Write failing tests**

Create `frontend/src/__tests__/lib/branch-rollup.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { buildBranchRollup, type BranchRollupRow } from "@/lib/branch-rollup";

describe("buildBranchRollup", () => {
  it("maps ranking items into rollup rows, preserving name/revenue/order", () => {
    const rollup = buildBranchRollup({
      sites: {
        items: [
          { rank: 1, key: 10, name: "Branch 1", value: 500_000, pct_of_total: 0.4 },
          { rank: 2, key: 11, name: "Branch 2", value: 300_000, pct_of_total: 0.24 },
        ],
        total: 1_250_000,
      },
      reorder: [],
      calendar: [],
    });
    expect(rollup.map((r) => r.name)).toEqual(["Branch 1", "Branch 2"]);
    expect(rollup[0].revenue).toBe(500_000);
  });

  it("counts reorder alerts per site", () => {
    const rollup = buildBranchRollup({
      sites: {
        items: [
          { rank: 1, key: 10, name: "Branch 1", value: 1, pct_of_total: 0 },
          { rank: 2, key: 11, name: "Branch 2", value: 1, pct_of_total: 0 },
        ],
        total: 2,
      },
      reorder: [
        { drug_code: "A", drug_name: "a", on_hand: 0, reorder_point: 10, site_name: "Branch 1" },
        { drug_code: "B", drug_name: "b", on_hand: 1, reorder_point: 10, site_name: "Branch 1" },
        { drug_code: "C", drug_name: "c", on_hand: 0, reorder_point: 10, site_name: "Branch 2" },
      ],
      calendar: [],
    });
    expect(rollup.find((r) => r.name === "Branch 1")!.riskCount).toBe(2);
    expect(rollup.find((r) => r.name === "Branch 2")!.riskCount).toBe(1);
  });

  it("sums expiry exposure from calendar buckets ≤30 days per site", () => {
    const rollup = buildBranchRollup({
      sites: {
        items: [
          { rank: 1, key: 10, name: "Branch 1", value: 1, pct_of_total: 0 },
        ],
        total: 1,
      },
      reorder: [],
      calendar: [
        { bucket: "0-7", days_out: 7, exposure_egp: 5_000, batch_count: 1, site_name: "Branch 1" },
        { bucket: "15-30", days_out: 30, exposure_egp: 3_000, batch_count: 1, site_name: "Branch 1" },
        { bucket: "31+", days_out: 60, exposure_egp: 99_999, batch_count: 1, site_name: "Branch 1" },
      ],
    });
    expect(rollup[0].expiryExposureEgp).toBe(8_000);
  });

  it("returns empty array when sites payload is undefined", () => {
    expect(buildBranchRollup({ sites: undefined, reorder: [], calendar: [] })).toEqual([]);
  });

  it("assigns trend='flat' as default when no trend source provided", () => {
    const rollup = buildBranchRollup({
      sites: {
        items: [{ rank: 1, key: 10, name: "Branch 1", value: 1, pct_of_total: 0 }],
        total: 1,
      },
      reorder: [],
      calendar: [],
    });
    expect(rollup[0].trend).toBe("flat");
  });
});
```

- [ ] **Step 2: Run to confirm failure**

Run:
```bash
cd frontend && npm run test -- --run src/__tests__/lib/branch-rollup.test.ts
```

Expected: fails with module not found.

- [ ] **Step 3: Implement**

Create `frontend/src/lib/branch-rollup.ts`:

```typescript
/**
 * Pure client-side per-site aggregation.
 * Joins useSites (RankingResult) with useReorderAlerts and useExpiryCalendar
 * so BranchList can display revenue + risk + expiry without a backend change.
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
```

- [ ] **Step 4: Run tests — expect pass**

Run:
```bash
cd frontend && npm run test -- --run src/__tests__/lib/branch-rollup.test.ts
```

Expected: all 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/branch-rollup.ts frontend/src/__tests__/lib/branch-rollup.test.ts
git commit -m "feat(frontend): branch-rollup pure module with tests"
```

---

## Task 3: AttentionRow component

A single alert row. Purely presentational — no data fetching.

**Files:**
- Create: `frontend/src/components/dashboard/new/AttentionRow.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/dashboard/new/AttentionRow.tsx`:

```tsx
"use client";

import Link from "next/link";
import {
  AlertTriangle,
  PackageMinus,
  Activity,
  Database,
  ArrowUpRight,
} from "lucide-react";
import type {
  AttentionAlert,
  AttentionSeverity,
  AttentionType,
} from "@/lib/attention-queue";

const TYPE_ICON: Record<AttentionType, typeof AlertTriangle> = {
  expiry: AlertTriangle,
  stock: PackageMinus,
  anomaly: Activity,
  pipeline: Database,
};

const DOT_COLOR: Record<AttentionSeverity, string> = {
  red: "bg-red-500",
  amber: "bg-amber-400",
  blue: "bg-sky-400",
};

const DOT_LABEL: Record<AttentionSeverity, string> = {
  red: "critical",
  amber: "warning",
  blue: "info",
};

function formatEgp(value: number): string {
  if (value >= 1_000_000) return `EGP ${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `EGP ${(value / 1_000).toFixed(0)}K`;
  return `EGP ${value.toFixed(0)}`;
}

export function AttentionRow({ alert }: { alert: AttentionAlert }) {
  const Icon = TYPE_ICON[alert.type];
  const impactText =
    alert.impactEgp !== undefined
      ? formatEgp(alert.impactEgp)
      : alert.impactCount !== undefined
      ? `${alert.impactCount} SKUs`
      : "";

  return (
    <li className="flex items-center gap-3 px-4 py-2 hover:bg-elevated/40 rounded-md">
      <span
        className={`w-2 h-2 rounded-full shrink-0 ${DOT_COLOR[alert.severity]}`}
        role="img"
        aria-label={DOT_LABEL[alert.severity]}
      />
      <Icon className="w-3.5 h-3.5 text-ink-secondary shrink-0" aria-hidden />
      <span className="flex-1 text-sm text-ink-primary truncate">{alert.title}</span>
      {impactText && (
        <span className="text-xs text-ink-secondary font-mono shrink-0">{impactText}</span>
      )}
      {alert.where && (
        <span className="text-xs text-ink-secondary shrink-0">{alert.where}</span>
      )}
      <Link
        href={alert.drillHref}
        className="inline-flex items-center gap-1 text-xs text-accent-strong hover:underline shrink-0
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded"
        aria-label={`Drill into ${alert.title}`}
      >
        <ArrowUpRight className="w-3 h-3" aria-hidden />
        Drill
      </Link>
    </li>
  );
}
```

- [ ] **Step 2: Typecheck**

Run:
```bash
cd frontend && npx tsc --noEmit
```

Expected: exit 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dashboard/new/AttentionRow.tsx
git commit -m "feat(frontend): AttentionRow component"
```

---

## Task 4: AttentionChips component

**Files:**
- Create: `frontend/src/components/dashboard/new/AttentionChips.tsx`

- [ ] **Step 1: Create**

Create `frontend/src/components/dashboard/new/AttentionChips.tsx`:

```tsx
"use client";

import type { AttentionType } from "@/lib/attention-queue";

export type ChipFilter = "all" | "critical" | AttentionType;

interface Chip {
  key: ChipFilter;
  label: string;
  count: number;
}

interface Props {
  chips: Chip[];
  active: ChipFilter;
  onChange: (next: ChipFilter) => void;
}

export function AttentionChips({ chips, active, onChange }: Props) {
  return (
    <div
      role="tablist"
      aria-label="Attention filter"
      className="flex gap-2 flex-wrap overflow-x-auto md:flex-nowrap"
    >
      {chips.map((c) => (
        <button
          key={c.key}
          role="tab"
          aria-selected={active === c.key}
          onClick={() => onChange(c.key)}
          className={[
            "px-3 py-1.5 rounded-full text-xs inline-flex items-center gap-1.5",
            "border transition focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60",
            active === c.key
              ? "bg-elevated text-ink-primary border-accent/50"
              : "bg-card/80 text-ink-secondary border-border/40 hover:text-ink-primary",
          ].join(" ")}
        >
          <span>{c.label}</span>
          <span className="text-[10px] text-ink-secondary font-mono">{c.count}</span>
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Typecheck & commit**

```bash
cd frontend && npx tsc --noEmit
git add frontend/src/components/dashboard/new/AttentionChips.tsx
git commit -m "feat(frontend): AttentionChips filter component"
```

---

## Task 5: AttentionQueue component (integrates 1+3+4)

**Files:**
- Create: `frontend/src/components/dashboard/new/AttentionQueue.tsx`

- [ ] **Step 1: Create**

Create `frontend/src/components/dashboard/new/AttentionQueue.tsx`:

```tsx
"use client";

import { useMemo, useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { AttentionRow } from "./AttentionRow";
import { AttentionChips, type ChipFilter } from "./AttentionChips";
import {
  mergeAttentionAlerts,
  type AttentionAlert,
  type MergeInputs,
} from "@/lib/attention-queue";
import { trackEvent } from "@/lib/analytics-events";

interface Props {
  inputs: MergeInputs;
  loading: boolean;
  syncedLabel?: string;
  maxVisible?: number;
}

export function AttentionQueue({ inputs, loading, syncedLabel, maxVisible = 8 }: Props) {
  const [active, setActive] = useState<ChipFilter>("all");

  const alerts = useMemo(() => mergeAttentionAlerts(inputs), [inputs]);

  const counts = useMemo(() => {
    return {
      all: alerts.length,
      critical: alerts.filter((a) => a.severity === "red").length,
      expiry: alerts.filter((a) => a.type === "expiry").length,
      stock: alerts.filter((a) => a.type === "stock").length,
      anomaly: alerts.filter((a) => a.type === "anomaly").length,
      pipeline: alerts.filter((a) => a.type === "pipeline").length,
    };
  }, [alerts]);

  const filtered = useMemo(() => {
    if (active === "all") return alerts;
    if (active === "critical") return alerts.filter((a) => a.severity === "red");
    return alerts.filter((a) => a.type === active);
  }, [alerts, active]);

  const chips = (
    [
      { key: "all" as const, label: "All", count: counts.all },
      { key: "critical" as const, label: "Critical", count: counts.critical },
      { key: "expiry" as const, label: "Expiry", count: counts.expiry },
      { key: "stock" as const, label: "Stock", count: counts.stock },
      { key: "anomaly" as const, label: "Anomaly", count: counts.anomaly },
      { key: "pipeline" as const, label: "Pipeline", count: counts.pipeline },
    ] satisfies Array<{ key: ChipFilter; label: string; count: number }>
  ).filter((c) => c.key === "all" || c.count > 0);

  if (loading) {
    return (
      <section
        role="region"
        aria-label="Attention queue"
        className="rounded-[14px] bg-card border border-border/40 p-5 h-[364px] animate-pulse"
        aria-busy="true"
      />
    );
  }

  if (alerts.length === 0) {
    return (
      <section
        role="region"
        aria-label="Attention queue"
        className="rounded-[14px] bg-card border border-border/40 p-5 h-[364px]
                   flex flex-col items-center justify-center text-center gap-2"
      >
        <CheckCircle2 className="w-7 h-7 text-accent-strong" aria-hidden />
        <h2 className="text-base font-semibold text-ink-primary">All clear</h2>
        <p className="text-sm text-ink-secondary">
          No attention needed right now{syncedLabel ? ` · ${syncedLabel}` : ""}.
        </p>
      </section>
    );
  }

  return (
    <section
      role="region"
      aria-label="Attention queue"
      className="rounded-[14px] bg-card border border-border/40 p-4"
    >
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-ink-primary">
          Needs your attention
        </h2>
        {syncedLabel && (
          <span className="text-[11px] text-ink-secondary">{syncedLabel}</span>
        )}
      </div>
      <AttentionChips chips={chips} active={active} onChange={setActive} />
      <ul
        className="mt-3 overflow-y-auto"
        style={{ maxHeight: `${maxVisible * 40}px` }}
        onClickCapture={(e) => {
          const target = (e.target as HTMLElement).closest("a[href]");
          if (!target) return;
          const href = target.getAttribute("href") ?? "";
          const alert = filtered.find((a) => a.drillHref === href);
          if (alert) {
            trackEvent("attention_queue_drill", {
              type: alert.type,
              severity: alert.severity,
              alert_id: alert.id,
            });
          }
        }}
      >
        {filtered.map((a: AttentionAlert) => (
          <AttentionRow key={a.id} alert={a} />
        ))}
      </ul>
    </section>
  );
}
```

> **Note:** if `trackEvent` doesn't exist in `@/lib/analytics-events`, fall back to `console.debug(...)` OR import the existing named exports (`trackFirstDashboardView` is referenced in `page.tsx`). Before committing, inspect that file to find the correct function name. If there is no generic `trackEvent` helper, add one in the same module:
> ```typescript
> export function trackEvent(name: string, props: Record<string, unknown>) {
>   // delegate to existing analytics shim if present, else no-op
>   if (typeof window !== "undefined" && (window as unknown as { posthog?: { capture: (n: string, p: unknown) => void } }).posthog) {
>     (window as unknown as { posthog: { capture: (n: string, p: unknown) => void } }).posthog.capture(name, props);
>   }
> }
> ```

- [ ] **Step 2: Verify or add `trackEvent` in analytics-events**

Run:
```bash
grep -n "export" frontend/src/lib/analytics-events.ts
```

If `trackEvent` is missing, add the helper shown above to `frontend/src/lib/analytics-events.ts`.

- [ ] **Step 3: Typecheck**

Run:
```bash
cd frontend && npx tsc --noEmit
```

Expected: exit 0.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/dashboard/new/AttentionQueue.tsx frontend/src/lib/analytics-events.ts
git commit -m "feat(frontend): AttentionQueue hero component"
```

---

## Task 6: KpiStrip component

**Files:**
- Create: `frontend/src/components/dashboard/new/KpiStrip.tsx`

- [ ] **Step 1: Create**

Create `frontend/src/components/dashboard/new/KpiStrip.tsx`:

```tsx
"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

export interface KpiPill {
  id: string;
  label: string;
  value: string;
  valueSuffix?: string;
  deltaDir: "up" | "down" | "flat";
  deltaText: string;
  sub: string;
  sparkline: number[];
  href: string;
}

function DeltaIcon({ dir }: { dir: KpiPill["deltaDir"] }) {
  if (dir === "up") return <TrendingUp className="w-3 h-3" aria-hidden />;
  if (dir === "down") return <TrendingDown className="w-3 h-3" aria-hidden />;
  return <Minus className="w-3 h-3" aria-hidden />;
}

function Sparkline({ points }: { points: number[] }) {
  if (!points.length) return null;
  const w = 120;
  const h = 16;
  const step = w / Math.max(1, points.length - 1);
  const d = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${(i * step).toFixed(1)} ${p.toFixed(1)}`)
    .join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-4 text-accent/70" aria-hidden>
      <path d={d} fill="none" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}

function Pill({ pill, children }: { pill: KpiPill; children?: ReactNode }) {
  const deltaColor =
    pill.deltaDir === "up"
      ? "text-accent-strong"
      : pill.deltaDir === "down"
      ? "text-red-400"
      : "text-ink-secondary";
  return (
    <Link
      href={pill.href}
      className="block p-4 hover:bg-elevated/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
      aria-label={`${pill.label}: ${pill.value}${pill.valueSuffix ? " " + pill.valueSuffix : ""}. ${pill.deltaText} ${pill.sub}`}
    >
      <div className="text-[11px] uppercase tracking-wider text-ink-secondary">
        {pill.label}
      </div>
      <div className="flex items-baseline gap-2 mt-1">
        <span className="text-xl font-semibold text-ink-primary">{pill.value}</span>
        {pill.valueSuffix && (
          <span className="text-[11px] text-ink-secondary">{pill.valueSuffix}</span>
        )}
        <span className={`text-xs inline-flex items-center gap-1 ${deltaColor}`}>
          <DeltaIcon dir={pill.deltaDir} />
          {pill.deltaText}
        </span>
      </div>
      <Sparkline points={pill.sparkline} />
      <div className="text-[11px] text-ink-secondary mt-0.5">{pill.sub}</div>
      {children}
    </Link>
  );
}

export function KpiStrip({ pills, loading }: { pills: KpiPill[]; loading: boolean }) {
  if (loading) {
    return (
      <section
        aria-label="Key performance indicators"
        className="rounded-[14px] bg-card border border-border/40 h-[88px] animate-pulse"
      />
    );
  }
  return (
    <section
      aria-label="Key performance indicators"
      className="rounded-[14px] bg-card border border-border/40
                 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-border/40"
    >
      {pills.map((p) => (
        <Pill key={p.id} pill={p} />
      ))}
    </section>
  );
}
```

- [ ] **Step 2: Typecheck & commit**

```bash
cd frontend && npx tsc --noEmit
git add frontend/src/components/dashboard/new/KpiStrip.tsx
git commit -m "feat(frontend): KpiStrip dense pill component"
```

---

## Task 7: BranchListRollup component

Replaces the existing 1/3-width `BranchList` for Zone 3 Row B. Accepts the richer `BranchRollupRow[]` from Task 2.

**Files:**
- Create: `frontend/src/components/dashboard/new/BranchListRollup.tsx`

- [ ] **Step 1: Create**

```tsx
"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import type { BranchRollupRow } from "@/lib/branch-rollup";

function formatEgp(value: number): string {
  if (value >= 1_000_000) return `EGP ${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `EGP ${(value / 1_000).toFixed(0)}K`;
  return `EGP ${value.toFixed(0)}`;
}

export function BranchListRollup({
  rows,
  loading,
}: {
  rows: BranchRollupRow[];
  loading: boolean;
}) {
  if (loading) {
    return (
      <section
        aria-label="Branches"
        className="rounded-[14px] bg-card border border-border/40 h-[360px] animate-pulse"
      />
    );
  }

  const sorted = [...rows].sort((a, b) => b.revenue - a.revenue);

  return (
    <section
      aria-label="Branches"
      className="rounded-[14px] bg-card border border-border/40 p-4 h-[360px] flex flex-col"
    >
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-ink-primary">Branches</h2>
        <Link
          href="/sites"
          className="text-xs text-accent-strong inline-flex items-center gap-1 hover:underline"
        >
          <ArrowUpRight className="w-3 h-3" aria-hidden />
          All
        </Link>
      </div>
      <ul className="flex-1 overflow-y-auto">
        {sorted.map((r) => (
          <li
            key={r.key}
            className="grid grid-cols-[1fr_auto_auto_auto] items-center gap-3 py-1.5
                       text-sm text-ink-primary border-b border-border/20 last:border-0"
          >
            <Link
              href={`/sites/${r.key}`}
              className="truncate hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded"
            >
              {r.name}
            </Link>
            <span className="text-xs text-ink-secondary font-mono">{formatEgp(r.revenue)}</span>
            <span
              className={`text-xs font-mono ${r.riskCount > 0 ? "text-amber-400" : "text-ink-secondary"}`}
              aria-label={`${r.riskCount} stock risk items`}
            >
              {r.riskCount}⚠
            </span>
            <span
              className={`text-xs font-mono ${r.expiryExposureEgp > 0 ? "text-red-400" : "text-ink-secondary"}`}
              aria-label={`${formatEgp(r.expiryExposureEgp)} expiry exposure`}
            >
              {formatEgp(r.expiryExposureEgp)}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

- [ ] **Step 2: Typecheck & commit**

```bash
cd frontend && npx tsc --noEmit
git add frontend/src/components/dashboard/new/BranchListRollup.tsx
git commit -m "feat(frontend): BranchListRollup with risk+expiry columns"
```

---

## Task 8: DashboardFooterBar component (Zone 4)

**Files:**
- Create: `frontend/src/components/dashboard/new/DashboardFooterBar.tsx`

- [ ] **Step 1: Create**

Create `frontend/src/components/dashboard/new/DashboardFooterBar.tsx`:

```tsx
"use client";

import { useState } from "react";
import Link from "next/link";
import { ChevronDown, Database, Activity, FileText } from "lucide-react";
import type { ReactNode } from "react";

interface PipelineSummary {
  status: "success" | "failed" | "running" | string;
  lastRunAt?: string;
  checksTotal?: number;
  checksFailed?: number;
}

interface Props {
  pipeline: PipelineSummary | null;
  channelsSlot: ReactNode;
}

function relativeTime(iso?: string): string {
  if (!iso) return "just now";
  const d = new Date(iso).getTime();
  if (Number.isNaN(d)) return "just now";
  const diff = Math.max(0, Date.now() - d);
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function DashboardFooterBar({ pipeline, channelsSlot }: Props) {
  const [channelsOpen, setChannelsOpen] = useState(false);

  const pipeColor =
    pipeline?.status === "success"
      ? "bg-accent"
      : pipeline?.status === "failed"
      ? "bg-red-500"
      : "bg-amber-400";

  return (
    <footer className="flex flex-wrap items-center gap-3 py-3 text-xs text-ink-secondary">
      <span className="inline-flex items-center gap-2">
        <span className={`w-1.5 h-1.5 rounded-full ${pipeColor}`} aria-hidden />
        <Database className="w-3 h-3" aria-hidden />
        Pipeline {pipeline?.status ?? "unknown"} · last run {relativeTime(pipeline?.lastRunAt)}
        {typeof pipeline?.checksTotal === "number" && typeof pipeline?.checksFailed === "number" && (
          <span className="font-mono ml-1">
            {pipeline.checksTotal - pipeline.checksFailed}/{pipeline.checksTotal} checks
          </span>
        )}
      </span>

      <div className="relative">
        <button
          type="button"
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-border/40
                     hover:bg-elevated/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
          aria-expanded={channelsOpen}
          aria-controls="channels-popover"
          onClick={() => setChannelsOpen((v) => !v)}
        >
          Channels <ChevronDown className="w-3 h-3" aria-hidden />
        </button>
        {channelsOpen && (
          <div
            id="channels-popover"
            role="dialog"
            className="absolute bottom-full mb-2 w-[360px] max-w-[90vw] rounded-xl border border-border/40
                       bg-card shadow-xl p-3 z-10"
          >
            {channelsSlot}
          </div>
        )}
      </div>

      <Link
        href="/insights"
        className="inline-flex items-center gap-1.5 hover:text-ink-primary
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded"
      >
        <Activity className="w-3 h-3" aria-hidden />
        All anomalies →
      </Link>
      <Link
        href="/reports"
        className="inline-flex items-center gap-1.5 hover:text-ink-primary
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded"
      >
        <FileText className="w-3 h-3" aria-hidden />
        All reports →
      </Link>
    </footer>
  );
}
```

- [ ] **Step 2: Typecheck & commit**

```bash
cd frontend && npx tsc --noEmit
git add frontend/src/components/dashboard/new/DashboardFooterBar.tsx
git commit -m "feat(frontend): DashboardFooterBar with pipeline chip + channels popover"
```

---

## Task 9: Export new components + provisional index entries

**Files:**
- Modify: `frontend/src/components/dashboard/new/index.ts`

- [ ] **Step 1: Read current exports**

```bash
cat frontend/src/components/dashboard/new/index.ts
```

- [ ] **Step 2: Add new exports (leave old ones in place for now)**

Open `frontend/src/components/dashboard/new/index.ts` and add these lines at the end (do NOT remove existing exports yet — Task 11 handles that):

```typescript
export { AttentionQueue } from "./AttentionQueue";
export { AttentionRow } from "./AttentionRow";
export { AttentionChips } from "./AttentionChips";
export { KpiStrip } from "./KpiStrip";
export { DashboardFooterBar } from "./DashboardFooterBar";
export { BranchListRollup } from "./BranchListRollup";
```

- [ ] **Step 3: Typecheck**

```bash
cd frontend && npx tsc --noEmit
```

Expected: exit 0.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/dashboard/new/index.ts
git commit -m "feat(frontend): export new dashboard zone components"
```

---

## Task 10: Rewrite `/dashboard/page.tsx` — compose the four zones

This is the biggest task. The file currently imports the old widgets and composes them in the pre-redesign layout. We'll rewrite the JSX body while reusing the existing hook block (no API contract changes).

**Files:**
- Modify: `frontend/src/app/dashboard/page.tsx`

- [ ] **Step 1: Read the current page to confirm hook block**

```bash
cat frontend/src/app/dashboard/page.tsx
```

Confirm these hooks are present (they should not change): `useDashboard`, `useRevenueForecast`, `useChannels`, `useReorderAlerts`, `useExpiryCalendar`, `useExpiryExposure`, `useAnomalyCards`, `usePipelineHealth`, `useTopInsight`, `useSites`.

- [ ] **Step 2: Replace the file entirely**

Overwrite `frontend/src/app/dashboard/page.tsx`:

```tsx
"use client";

/**
 * /dashboard — Action-Center redesign (2026-04-21).
 *
 * Four vertical zones: AttentionQueue (hero) -> KpiStrip -> Evidence rows
 * (RevenueChart + ExpiryHeatmap, then InventoryTable + BranchListRollup)
 * -> DashboardFooterBar. Spec:
 * docs/plans/specs/2026-04-21-home-dashboard-action-center-design.md
 *
 * All data bindings use existing SWR hooks — no new endpoints.
 * Golden-Path telemetry (#398/#399) retained via trackFirstDashboardView.
 */

import { useEffect, useMemo, useState } from "react";
import { Download, Plus } from "lucide-react";
import { useSession } from "next-auth/react";

import {
  DashboardSidebar,
  AttentionQueue,
  KpiStrip,
  DashboardFooterBar,
  BranchListRollup,
  RevenueChart,
  ChannelDonut,
  InventoryTable,
  ExpiryHeatmap,
  type KpiPill,
} from "@/components/dashboard/new";
import { OnboardingStrip } from "@/components/dashboard/onboarding-strip";
import { FirstInsightCard } from "@/components/dashboard/first-insight-card";
import { useDashboard } from "@/hooks/use-dashboard";
import { useRevenueForecast, type RevenueForecastPeriod } from "@/hooks/use-revenue-forecast";
import { useChannels } from "@/hooks/use-channels";
import { useReorderAlerts } from "@/hooks/use-reorder-alerts";
import { useExpiryCalendar } from "@/hooks/use-expiry-calendar";
import { useExpiryExposure } from "@/hooks/use-expiry-exposure";
import { useAnomalyCards } from "@/hooks/use-anomaly-cards";
import { usePipelineHealth } from "@/hooks/use-pipeline-health";
import { useSites } from "@/hooks/use-sites";
import { buildBranchRollup } from "@/lib/branch-rollup";
import { trackFirstDashboardView } from "@/lib/analytics-events";
import type { KPISparkline, KPISummary, TimeSeriesPoint } from "@/types/api";

type Period = "Day" | "Week" | "Month" | "Quarter" | "YTD";
const PERIODS: Period[] = ["Day", "Week", "Month", "Quarter", "YTD"];

const periodToApi: Record<Period, RevenueForecastPeriod> = {
  Day: "day",
  Week: "week",
  Month: "month",
  Quarter: "quarter",
  YTD: "ytd",
};

function formatEgp(value: number): string {
  if (value >= 1_000_000) return `EGP ${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `EGP ${(value / 1_000).toFixed(0)}K`;
  return `EGP ${value.toFixed(0)}`;
}

function formatInt(value: number): string {
  return value.toLocaleString();
}

function sparklineFor(
  metric: KPISparkline["metric"],
  summary: KPISummary | undefined,
): number[] {
  const series =
    summary?.sparklines?.find((s) => s.metric === metric)?.points ??
    (metric === "revenue" ? summary?.sparkline : undefined);
  if (!series?.length) return [];
  const values = series.map((p: TimeSeriesPoint) => Number(p.value) || 0);
  const max = Math.max(...values, 1);
  return values.map((v) => 32 - (v / max) * 28);
}

function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "just now";
  const d = new Date(iso).getTime();
  if (Number.isNaN(d)) return "just now";
  const diff = Math.max(0, Date.now() - d);
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function todayLabel(date = new Date()): string {
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function DashboardPage() {
  const [period, setPeriod] = useState<Period>("Month");
  const { data: session } = useSession();
  const firstName =
    session?.user?.name?.split(" ")[0] ||
    session?.user?.email?.split("@")[0] ||
    "there";

  useEffect(() => {
    trackFirstDashboardView();
  }, []);

  const { data: dashboard, isLoading: kpiLoading } = useDashboard();
  const { data: revenueForecast, isLoading: revenueLoading } =
    useRevenueForecast(periodToApi[period]);
  const { data: channels, isLoading: channelsLoading } = useChannels();
  const { data: reorder, isLoading: reorderLoading } = useReorderAlerts();
  const { data: expiryCalendar, isLoading: calendarLoading } = useExpiryCalendar();
  const { data: expiryExposure, isLoading: exposureLoading } = useExpiryExposure();
  const { data: anomalies, isLoading: anomaliesLoading } = useAnomalyCards(10);
  const { data: pipeline, isLoading: pipelineLoading } = usePipelineHealth();
  const { data: sites, isLoading: sitesLoading } = useSites();

  const summary = dashboard?.kpi;
  const syncedAgo = relativeTime(pipeline?.last_run?.at);

  const pills: KpiPill[] = useMemo(() => {
    if (!summary) return [];
    const momDir: KpiPill["deltaDir"] =
      (summary.mom_growth_pct ?? 0) > 0.1 ? "up"
      : (summary.mom_growth_pct ?? 0) < -0.1 ? "down"
      : "flat";
    const stockDir: KpiPill["deltaDir"] =
      (summary.stock_risk_delta ?? 0) <= 0 ? "up" : "down";
    return [
      {
        id: "revenue",
        label: "Total Revenue",
        value: formatEgp(summary.period_gross ?? summary.mtd_gross ?? 0),
        deltaDir: momDir,
        deltaText: `${Math.abs(summary.mom_growth_pct ?? 0).toFixed(1)}%`,
        sub: "vs last month",
        sparkline: sparklineFor("revenue", summary),
        href: "/sales-summary",
      },
      {
        id: "orders",
        label: "Orders",
        value: formatInt(summary.period_transactions ?? 0),
        deltaDir: "up",
        deltaText: `${formatInt(summary.daily_transactions ?? 0)} today`,
        sub: `${formatInt(summary.period_customers ?? 0)} customers`,
        sparkline: sparklineFor("orders", summary),
        href: "/sales-summary?tab=orders",
      },
      {
        id: "stock",
        label: "Stock Risk",
        value: formatInt(summary.stock_risk_count ?? 0),
        valueSuffix: "SKUs",
        deltaDir: stockDir,
        deltaText:
          summary.stock_risk_delta != null
            ? `${summary.stock_risk_delta > 0 ? "+" : ""}${summary.stock_risk_delta} new`
            : "needing reorder",
        sub: "needing reorder",
        sparkline: sparklineFor("stock_risk", summary),
        href: "/inventory?filter=below-reorder",
      },
      {
        id: "expiry",
        label: "Expiry Exposure",
        value: formatEgp(summary.expiry_exposure_egp ?? 0),
        deltaDir: "down",
        deltaText: "30-day window",
        sub: `${formatInt(summary.expiry_batch_count ?? 0)} batches`,
        sparkline: sparklineFor("expiry_exposure", summary),
        href: "/expiry",
      },
    ];
  }, [summary]);

  const branchRollup = useMemo(
    () => buildBranchRollup({ sites, reorder, calendar: expiryCalendar }),
    [sites, reorder, expiryCalendar],
  );

  const queueLoading =
    reorderLoading ||
    calendarLoading ||
    exposureLoading ||
    anomaliesLoading ||
    pipelineLoading;

  const pipelineSummary = pipeline
    ? {
        status: pipeline.last_run?.status ?? "unknown",
        lastRunAt: pipeline.last_run?.at ?? undefined,
        checksTotal: pipeline.checks_total ?? undefined,
        checksFailed: pipeline.checks_failed ?? 0,
      }
    : null;

  return (
    <div className="min-h-screen bg-page text-ink-primary font-sans grid grid-cols-1 xl:grid-cols-[248px_1fr]">
      <DashboardSidebar activeHref="/dashboard" />

      <main className="px-8 py-7 pb-10 max-w-[1600px]">
        <header className="flex flex-wrap items-end gap-5 mb-6">
          <div className="flex-1 min-w-[320px]">
            <div className="text-sm text-ink-secondary flex items-center gap-2 flex-wrap">
              Good morning, {firstName} — here&apos;s the pulse for{" "}
              <b className="text-ink-primary">{todayLabel()}</b>
              <LiveBadge label={`Synced ${syncedAgo}`} />
            </div>
            <h1 className="text-3xl font-bold tracking-tight mt-1">
              Daily operations overview
            </h1>
          </div>
          <PageActions period={period} onPeriodChange={setPeriod} />
        </header>

        {/* Phase 2 Golden-Path (#398) retained — strips self-hide when complete. */}
        <div className="flex flex-col gap-4 mb-5">
          <OnboardingStrip />
          <FirstInsightCard />
        </div>

        {/* ZONE 1 — Action */}
        <AttentionQueue
          inputs={{
            calendar: expiryCalendar,
            exposure: expiryExposure,
            reorder,
            anomalies,
            pipeline,
          }}
          loading={queueLoading}
          syncedLabel={`Synced ${syncedAgo}`}
        />

        {/* ZONE 2 — Status */}
        <div className="mt-5">
          <KpiStrip pills={pills} loading={kpiLoading || !summary} />
        </div>

        {/* ZONE 3 Row A — Trend + pharma-critical */}
        <section className="grid grid-cols-1 xl:grid-cols-[2fr_1fr] gap-4 mt-5">
          <RevenueChart data={revenueForecast} loading={revenueLoading} mode="Revenue" />
          <ExpiryHeatmap
            calendar={expiryCalendar}
            exposure={expiryExposure}
            loading={calendarLoading || exposureLoading}
          />
        </section>

        {/* ZONE 3 Row B — Ops evidence */}
        <section className="grid grid-cols-1 xl:grid-cols-[2fr_1fr] gap-4 mt-5">
          <InventoryTable data={reorder} loading={reorderLoading} branches={[]} />
          <BranchListRollup rows={branchRollup} loading={sitesLoading} />
        </section>

        {/* ZONE 4 — Plumbing */}
        <DashboardFooterBar
          pipeline={pipelineSummary}
          channelsSlot={<ChannelDonut data={channels} loading={channelsLoading} />}
        />
      </main>
    </div>
  );
}

function LiveBadge({ label }: { label: string }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 text-[11px] text-accent-strong font-mono uppercase tracking-wider"
      aria-live="polite"
    >
      <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" aria-hidden />
      {label}
    </span>
  );
}

function PageActions({
  period,
  onPeriodChange,
}: {
  period: Period;
  onPeriodChange: (p: Period) => void;
}) {
  return (
    <div className="flex items-center gap-3 ml-auto">
      <div
        role="tablist"
        aria-label="Period"
        className="inline-flex p-1 rounded-full bg-card/80 border border-border/40"
      >
        {PERIODS.map((p) => (
          <button
            key={p}
            role="tab"
            aria-selected={period === p}
            onClick={() => onPeriodChange(p)}
            className={[
              "px-3.5 py-1.5 rounded-full text-[13px] transition",
              "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60",
              period === p
                ? "bg-elevated text-ink-primary shadow-[inset_0_0_0_1px_rgba(0,199,242,0.3)]"
                : "text-ink-secondary hover:text-ink-primary",
            ].join(" ")}
          >
            {p}
          </button>
        ))}
      </div>
      <button
        type="button"
        className="px-3.5 py-2 rounded-lg border border-border/60 text-[13px] inline-flex items-center gap-2 hover:bg-elevated/60
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
      >
        <Download className="w-3.5 h-3.5" aria-hidden />
        Export
      </button>
      <button
        type="button"
        className="px-3.5 py-2 rounded-lg bg-accent text-page font-semibold text-[13px] inline-flex items-center gap-2 hover:bg-accent-strong
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
      >
        <Plus className="w-3.5 h-3.5" aria-hidden />
        New report
      </button>
    </div>
  );
}
```

- [ ] **Step 3: Typecheck**

```bash
cd frontend && npx tsc --noEmit
```

Expected: exit 0.

If `InventoryTable` rejects the `branches` prop being empty, check the existing signature with:
```bash
grep -n "InventoryTableProps\|interface .*InventoryTable" frontend/src/components/dashboard/new/inventory-table.tsx
```
and pass through the previous `branchNames` derivation if the prop is required. Inline fix.

- [ ] **Step 4: Run Vitest**

```bash
cd frontend && npm run test -- --run
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/dashboard/page.tsx
git commit -m "feat(frontend): rewrite /dashboard to four-zone action-center layout"
```

---

## Task 11: Update the dashboard Playwright spec

The existing spec expects widget headings like "Revenue trend", "Channel split", "Anomalies & insights", and "Pipeline health" at their old positions. After the redesign, some of those headings move or disappear.

**Files:**
- Modify: `frontend/e2e/dashboard.spec.ts`

- [ ] **Step 1: Read the current spec**

```bash
cat frontend/e2e/dashboard.spec.ts
```

- [ ] **Step 2: Replace the "all ten design widgets mount" test with a zone-based assertion**

Find this test:
```typescript
test("all ten design widgets mount", async ({ page }) => {
```
…and replace its body with:

```typescript
test("four action-center zones mount", async ({ page }) => {
  test.skip(needsBackend, "widget hydration uses API data — validate in staging");
  // Zone 1
  await expect(page.getByRole("region", { name: "Attention queue" })).toBeVisible({
    timeout: 15000,
  });
  // Zone 2
  await expect(page.getByRole("region", { name: "Key performance indicators" })).toBeVisible();
  // Zone 3 Row A — RevenueChart + ExpiryHeatmap
  await expect(page.getByRole("heading", { name: "Revenue trend" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Expiry calendar" })).toBeVisible();
  // Zone 3 Row B — InventoryTable + BranchListRollup
  await expect(
    page.getByRole("heading", { name: "Inventory — reorder watchlist" }),
  ).toBeVisible();
  await expect(page.getByRole("region", { name: "Branches" })).toBeVisible();
  // Zone 4 — footer chip strip
  await expect(page.getByRole("button", { name: /Channels/i })).toBeVisible();
  await expect(page.getByRole("link", { name: /All anomalies/i })).toBeVisible();
  await expect(page.getByRole("link", { name: /All reports/i })).toBeVisible();
});
```

If a widget heading does not match (e.g. InventoryTable's h2 differs) — check the current component's `<h2>`/`<h3>` text and adjust the selector accordingly. Do NOT loosen to a generic `page.locator("h2")` — role-based selectors are the existing convention.

- [ ] **Step 3: Run the E2E spec locally (headed or headless)**

```bash
cd frontend && npx playwright test e2e/dashboard.spec.ts
```

Expected: all tests pass (`needsBackend` tests skip unless CI is set).

- [ ] **Step 4: Commit**

```bash
git add frontend/e2e/dashboard.spec.ts
git commit -m "test(frontend): update dashboard E2E to four-zone action-center"
```

---

## Task 12: Delete obsolete widgets (AlertBanner, AnomalyFeed, PipelineHealthCard)

**Files:**
- Delete: `frontend/src/components/dashboard/new/alert-banner.tsx`
- Delete: `frontend/src/components/dashboard/new/anomaly-feed.tsx`
- Delete: `frontend/src/components/dashboard/new/pipeline-health.tsx`
- Modify: `frontend/src/components/dashboard/new/index.ts`

- [ ] **Step 1: Double-check no other consumers**

Run:
```bash
cd frontend && grep -rn "AlertBanner\|AnomalyFeed\|PipelineHealthCard" src/ app/ 2>/dev/null | grep -v "src/components/dashboard/new/"
```

Expected: no results outside the component folder itself.

If any consumer is found (e.g. inside `__tests__`), handle it inline before deleting. Do NOT proceed if production code still references these symbols.

- [ ] **Step 2: Delete the component files**

```bash
rm frontend/src/components/dashboard/new/alert-banner.tsx
rm frontend/src/components/dashboard/new/anomaly-feed.tsx
rm frontend/src/components/dashboard/new/pipeline-health.tsx
```

- [ ] **Step 3: Remove the dead exports from the index barrel**

Edit `frontend/src/components/dashboard/new/index.ts` and delete the lines:

```typescript
export { AlertBanner } from "./alert-banner";
export { AnomalyFeed } from "./anomaly-feed";
export { PipelineHealthCard } from "./pipeline-health";
```

Leave the `KpiCard` export in place — detail pages still use it.

- [ ] **Step 4: Typecheck and run tests**

```bash
cd frontend && npx tsc --noEmit && npm run test -- --run
```

Expected: exit 0 on both.

- [ ] **Step 5: Commit**

```bash
git add -A frontend/src/components/dashboard/new/
git commit -m "chore(frontend): drop AlertBanner/AnomalyFeed/PipelineHealthCard (superseded)"
```

---

## Task 13: Mobile tap-target pass

Acceptance criterion: every interactive element ≥44px shortest dimension at `<768px`. The new components follow the rule already; the risk is the existing header buttons (`h-8`/`h-9`).

**Files:**
- Modify: `frontend/src/app/dashboard/page.tsx` (PageActions buttons only)

- [ ] **Step 1: Adjust Export and New-report buttons**

In `frontend/src/app/dashboard/page.tsx`, change each `className` that currently reads `px-3.5 py-2 rounded-lg …` on the Export and New-report buttons to:

```tsx
className="h-11 md:h-9 px-3.5 rounded-lg border border-border/60 text-[13px] inline-flex items-center gap-2 hover:bg-elevated/60
           focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
```

and for the primary button:

```tsx
className="h-11 md:h-9 px-3.5 rounded-lg bg-accent text-page font-semibold text-[13px] inline-flex items-center gap-2 hover:bg-accent-strong
           focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
```

Leave period tabs as-is (already meet the rule at current size thanks to `py-1.5` + text padding — verify visually).

- [ ] **Step 2: Typecheck**

```bash
cd frontend && npx tsc --noEmit
```

Expected: exit 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/dashboard/page.tsx
git commit -m "feat(frontend): bump dashboard header button tap targets on mobile"
```

---

## Task 14: Final verification pass

- [ ] **Step 1: Typecheck**

```bash
cd frontend && npx tsc --noEmit
```

Expected: exit 0.

- [ ] **Step 2: Lint**

```bash
cd frontend && npm run lint
```

Expected: exit 0 (or only pre-existing unrelated warnings). Fix any new warning introduced by this work.

- [ ] **Step 3: Vitest (full suite)**

```bash
cd frontend && npm run test -- --run
```

Expected: all passing. Pass count ≥ Task 0 baseline + 15 (10 attention-queue + 5 branch-rollup).

- [ ] **Step 4: Playwright (dashboard + redirect specs)**

```bash
cd frontend && npx playwright test e2e/dashboard.spec.ts e2e/dashboard-v2-redirect.spec.ts
```

Expected: all tests pass (skipped tests under `needsBackend` guard are acceptable).

- [ ] **Step 5: Manual smoke (if dev server available)**

```bash
cd frontend && npm run dev
# open http://localhost:3000/dashboard in a browser
```

Verify manually:
- Zone ordering matches spec.
- AttentionQueue shows alerts (or "All clear" state).
- KpiStrip pills are clickable and drill correctly.
- Channels popover opens/closes.
- Dark/light theme toggle applies to all new components.
- Mobile (resize to 375px): no horizontal page scroll, all text readable, all buttons tappable.

If any regression: open a follow-up task; don't mask it in this plan.

- [ ] **Step 6: Final commit (only if any fixups were made above)**

```bash
git status
# If working tree clean, no commit needed.
# Else:
git commit -am "chore(frontend): post-verification fixups for dashboard redesign"
```

---

## Self-review (plan vs spec)

- [x] Spec §"Zone 1 — Attention Queue" covered by Tasks 1, 3, 4, 5 (queue + row + chips + merge).
- [x] Spec §"Zone 2 — KPI Strip" covered by Task 6.
- [x] Spec §"Zone 3 — Evidence" covered by Task 10 (reuses RevenueChart / ExpiryHeatmap / InventoryTable; adds BranchListRollup in Task 7).
- [x] Spec §"Zone 4 — Plumbing footer" covered by Task 8.
- [x] Spec §"Widget verdict table" — Kill verdicts covered by Task 12; Demote verdicts covered by Task 10 composing into new zones.
- [x] Spec §"Responsive behavior" covered by the Tailwind class names in Tasks 3–8 and Task 13.
- [x] Spec §"Data bindings summary" — no new endpoints; `useSites` gap resolved via Task 2 `branch-rollup.ts`.
- [x] Spec §"File inventory" — all listed files created or modified.
- [x] Spec §"Acceptance criteria" — verified in Task 14.
- [x] Spec §"Open questions deferred to writing-plans" — all four resolved at the top of this plan.

**Type-name consistency:** `AttentionAlert`, `AttentionType`, `AttentionSeverity`, `MergeInputs`, `BranchRollupRow`, `KpiPill`, `ChipFilter` — all defined in Tasks 1/2/4/6 and reused consistently in later tasks. No function name drift.

**No placeholders:** all test bodies, component bodies, and commands are full — no "TBD", no "similar to Task N" backrefs without the code. Ambiguity around `trackEvent` in Task 5 has an explicit resolution step with fallback code.

---

**Plan complete and saved to `docs/plans/sprints/2026-04-21-home-dashboard-action-center.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
