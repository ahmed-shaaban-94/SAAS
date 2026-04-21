# Home Dashboard — Action-Center Redesign (Design Spec)

- **Date:** 2026-04-21
- **Topic:** CEO-lens redesign of `/dashboard` for the pharma chain owner persona
- **Scope:** Home dashboard only; no other pages redesigned
- **Approach:** B — Inverted hierarchy (chosen over "Action-queue graft" and "New /today page")
- **Status:** Approved for implementation planning

## Context

The current `/dashboard` (shipped via PR #502) is a 10-widget "Daily Operations Overview" that already leans toward an action-center model but buries exceptions under four large KPI tiles. PRs #564 and #569 unified ~49 pages onto the V2 shell and made it responsive; this spec builds on that foundation rather than adding a second home.

### Locked persona & usage assumptions

| Dimension | Locked value |
|---|---|
| Persona | Pharma chain owner (end-customer), 5–10 branches |
| Scope | Home dashboard only |
| Primary job | Action center — "what needs my attention now?" |
| Usage pattern | Morning review, 3–5 minutes |
| Deliverable | Component-level spec |

## Goals

1. Surface ranked exceptions (expiry, stock, anomalies, pipeline) above KPIs.
2. Preserve all existing hooks and endpoints; **no new backend** required for v1 (one potential `useSites` extension flagged).
3. Fit a morning review into ~1.5 screens on desktop, single-column mobile.
4. Keep Golden-Path (#398) telemetry and V2 shell contracts intact.
5. Do not fork the dashboard surface — one home, not two.

## Non-goals

- No AI/narrative briefing (future spec).
- No role-based home variation.
- No redesign of other pages; they get kill/merge verdicts only where they intersect the home.
- No new backend endpoints beyond one possible `/api/v1/sites` extension.

## Page architecture — four zones

```
┌────────────────────────────────────────────────────────────┐
│ HEADER (unchanged)                                         │
│  Greeting + date + Synced badge + Period tabs + Export     │
├────────────────────────────────────────────────────────────┤
│ ZONE 1 — ACTION (~364px)                                   │
│  AttentionQueue (hero)                                     │
├────────────────────────────────────────────────────────────┤
│ ZONE 2 — STATUS (~88px)                                    │
│  KpiStrip: Revenue · Orders · Stock Risk · Expiry Exposure │
├────────────────────────────────────────────────────────────┤
│ ZONE 3 — EVIDENCE                                          │
│  Row A: RevenueChart (2fr) + ExpiryHeatmap (1fr) — 360px   │
│  Row B: InventoryTable (2fr) + BranchList (1fr) — 360px    │
├────────────────────────────────────────────────────────────┤
│ ZONE 4 — PLUMBING (~56px)                                  │
│  PipelineHealth chip · Channels popover · Anomalies link   │
└────────────────────────────────────────────────────────────┘
```

Zone ordering maps to the CEO's morning review flow: **act → confirm → explain → trust**.

Existing `V2Layout` shell, theme tokens, and dark/light support are all reused. Outer shell, max-width (1600px), padding (`px-8 py-7`), and gaps (`mt-5`, `gap-4`) are unchanged.

### What leaves the page

- `AlertBanner` — absorbed into AttentionQueue.
- `AnomalyFeed` card — its rows flow into AttentionQueue; a footer link replaces the card.
- `PipelineHealthCard` 1/3 card — collapses into a footer chip with a popover.
- `ChannelDonut` card — collapses into a footer popover button.

### What stays conditional above Zone 1

- `OnboardingStrip` and `FirstInsightCard` retain their current self-hide behavior; they render only when the tenant has not completed onboarding / first insight. For mature tenants they cost zero layout space.

## Zone 1 — Attention Queue

The new hero widget. A single card that merges and ranks alerts from four existing data sources.

### Component

- **File:** `frontend/src/components/dashboard/new/AttentionQueue.tsx`
- **Sub-components:**
  - `AttentionRow.tsx` — one alert row
  - `AttentionChips.tsx` — filter chip bar
- **Exported from:** `frontend/src/components/dashboard/new/index.ts`
- **Card shell:** reuses existing `Card` primitive + theme tokens
- **Fixed height:** 320px content area; internal scroll when >8 rows match filter

### Row anatomy

Each row is a `<li>` and renders:

- Severity dot (8px): red = critical, amber = warning, blue = info. Has `aria-label` ("critical", "warning", "info").
- Type icon (14px lucide): `AlertTriangle` (expiry), `PackageMinus` (stock), `Activity` (anomaly), `Database` (pipeline).
- Title (single line, ellipsis).
- Impact value (EGP where available, row count otherwise).
- Where (branch name, or "All branches" for global).
- Drill button — deep-links to the detail page in the same tab.

### Data sources (no new endpoints)

| Alert type | Hook | Mapping rule |
|---|---|---|
| Expiry risk | `useExpiryCalendar` + `useExpiryExposure` | One row per calendar bucket with `days_out ≤ 30` and `exposure_egp > 0`. Severity red if ≤14d, amber if 15–30d. |
| Stock risk | `useReorderAlerts` | Group by `drug_code`, top 20 by margin impact. Severity red if `on_hand ≤ 0`, amber if below reorder point. |
| Anomaly | `useAnomalyCards(10)` (limit bumped from 6) | Severity maps from server-provided `anomaly.severity`. |
| Pipeline | `usePipelineHealth` | Surface only when `last_run.status === 'failed'` OR `checks_failed > 0`. Severity always red. |

### Merge & ranking (client-side)

Pure function in `frontend/src/lib/attention-queue.ts`, unit-testable:

```
score = severity_weight + impact_weight + recency_weight
  severity_weight: red=100, amber=50, blue=10
  impact_weight:   min(50, egp_impact / 10_000)
  recency_weight:  max(0, 30 - hours_since_detected) / 2
```

Sort descending. Stable tie-break on `alert_id`. Red rows always precede amber.

### Filter chips

Above the row list:

```
[All (23)]  [Critical (5)]  [Expiry (8)]  [Stock (12)]  [Anomaly (2)]  [Pipeline (1)]
```

- Single-select; **All** by default.
- Count badges from the merged list.
- A chip renders only when its category has ≥1 alert.

### States

- **Loading:** skeleton chip row + 4 shimmering rows using existing `animate-pulse`.
- **Empty:** "All clear — no attention needed right now" with last-sync timestamp and a subtle checkmark. Zone is **not** hidden.
- **Error:** SWR default; the surrounding card stays, message `"Couldn't load alerts — retry"` with retry button.

### Accessibility

- `role="region"`, `aria-label="Attention queue"`.
- Rows are `<li>` elements; drill button is the focus target.
- Keyboard: arrow keys move focus between rows, `Enter` triggers drill.
- Severity conveyed via `aria-label` on the dot, not color alone.

### Telemetry

Fire `track("attention_queue_drill", { type, severity, alert_id })` on drill via the existing `analytics-events` plumbing. No new endpoint.

## Zone 2 — KPI Strip

Compresses the 4-tile KPI row (168px × 4) into a single strip (~88px) so KPIs confirm status without competing with Zone 1.

### Component

- **File:** `frontend/src/components/dashboard/new/KpiStrip.tsx`
- `KpiCard` is retained for detail pages; this is a denser sibling component.
- Shell: single card with 4 equal-width columns separated by vertical dividers (no outer border per pill).

### Pill anatomy

- Label (11px, uppercase, `text-ink-secondary`)
- Value (20px semibold) + delta chip (12px, `accent-strong` / `red-strong`, arrow icon)
- Sparkline (16px tall, full pill width) using the existing `sparklineFor()` helper
- Sub-label (11px, one line)

### The four KPIs (content unchanged)

| KPI | Value | Delta | Sub | Drill target |
|---|---|---|---|---|
| Total Revenue | `formatEgp(period_gross)` | `mom_growth_pct` | "vs last month" | `/sales-summary` |
| Orders | `formatInt(period_transactions)` | `daily_transactions` today | `period_customers` customers | `/sales-summary?tab=orders` |
| Stock Risk | `formatInt(stock_risk_count)` SKUs | `stock_risk_delta` new | "needing reorder" | `/inventory?filter=below-reorder` |
| Expiry Exposure | `formatEgp(expiry_exposure_egp)` | "30-day window" | `expiry_batch_count` batches | `/expiry` |

All fields already exist on `dashboard.kpi`. **No new API work.**

### Visual changes vs `KpiCard`

| Current | New | Reason |
|---|---|---|
| Big colored icon (32px) | Small icon (14px) in label row | Reduce visual weight |
| 32px value | 20px value | Reduce visual weight |
| 168px tall card | ~88px strip pill | ~50% vertical savings |
| Per-card color (`accent`/`purple`/`amber`/`red`) | Neutral treatment | Delta color carries direction; colors were competing with AttentionQueue |
| Separate cards | One strip with dividers | Reads as "one status line" |

### Interactions

- Each pill is clickable (drills to target above). Hover: subtle `bg-elevated/40`. Focus: existing `focus-visible:ring-accent/60`.
- No scale/fidget animation.

### States

- Loading: 4 shimmering pills at final height (no layout shift).
- Empty (summary undefined): pills render with `—` placeholders; delta + sparkline hidden.

## Zone 3 — Evidence

### Row A — Trend + Pharma-critical

```
┌──────────────────────────────────┬──────────────────────────┐
│ RevenueChart (2fr, ~66%)         │ ExpiryHeatmap (1fr, 33%) │
│ Period-aware, 360px              │ 12-week exposure, 360px  │
└──────────────────────────────────┴──────────────────────────┘
```

- `RevenueChart` — unchanged. Hook: `useRevenueForecast(period)`; period sourced from existing header tabs.
- `ExpiryHeatmap` — unchanged component, repositioned to Row A (was paired with InventoryTable). Rationale: expiry exposure is a pharma-specific CEO concern and belongs in the first evidence row. Hooks: `useExpiryCalendar` + `useExpiryExposure` (shared with AttentionQueue; SWR dedupes).

### Row B — Operational evidence

```
┌──────────────────────────────────┬──────────────────────────┐
│ InventoryTable (2fr)             │ BranchList (1fr)         │
│ Reorder risk, paginated, 360px   │ Per-branch rollup, 360px │
└──────────────────────────────────┴──────────────────────────┘
```

- `InventoryTable` — minor trim: remove the in-card branch filter dropdown. Filtering by branch is available from the AttentionQueue and from `/inventory`. Hook: `useReorderAlerts`.
- `BranchList` — promoted from a 1/3 slot in the current 3-up row into its own 1fr column. With 5–10 branches this fits inline. Hook: `useSites`. Columns: name, revenue (period), stock-risk count, expiry exposure, trend arrow. Default sort: revenue desc.

## Zone 4 — Plumbing footer (~56px)

Horizontal chip strip at the bottom, no card shells:

```
[● Healthy · Last run 3m ago · 12/12 checks] [Channels ▾] [All anomalies →] [All reports →]
```

- **`PipelineHealth`** chip — hook `usePipelineHealth`. Click opens a popover with the same content the current card shows (last run, checks, duration).
- **`Channels`** popover — hook `useChannels`, lazy-loaded on popover open. Content: the current `ChannelDonut`.
- **All anomalies →** — link to `/anomalies` (verify existence in implementation; create a thin list page if missing).
- **All reports →** — link to existing `/reports`.

## Widget verdict table (every current widget)

| Widget | Verdict | New location |
|---|---|---|
| `AlertBanner` | Kill | Absorbed into AttentionQueue |
| `OnboardingStrip` | Keep, conditional | Above Zone 1, self-hides |
| `FirstInsightCard` | Keep, conditional | Above Zone 1, self-hides |
| `KpiCard` × 4 | Demote into `KpiStrip` | Zone 2 |
| `RevenueChart` | Keep unchanged | Zone 3 Row A left |
| `ChannelDonut` | Demote to footer popover | Zone 4 |
| `InventoryTable` | Keep, remove in-card branch filter | Zone 3 Row B left |
| `ExpiryHeatmap` | Keep, promote to Row A | Zone 3 Row A right |
| `BranchList` | Keep, promote to Row B column | Zone 3 Row B right |
| `AnomalyFeed` card | Kill as card | Rows into queue; footer link replaces |
| `PipelineHealthCard` | Demote to footer chip | Zone 4 |
| `PageActions` | Keep unchanged | Header |

`AlertBanner` and `AnomalyFeed` component files are retained only if they have other consumers (grep required in implementation); otherwise delete.

## Responsive behavior

Uses existing Tailwind breakpoints: `sm:` 640, `md:` 768, `xl:` 1280. Base (unprefixed) styles target <640px; `md:` adds overrides from 768+; `xl:` from 1280+.

| Zone | ≥1280 (`xl:`) | 768–1279 (`md:`) | <768 (base, mobile) |
|---|---|---|---|
| Header | One row, all actions visible | Greeting wraps; Export/New-report move to overflow menu | Stacked: greeting → period tabs → action menu |
| Attention Queue | 8 rows, chip row | 6 rows | 5 rows; chips scroll horizontally; drill buttons ≥44px |
| KPI Strip | 4 pills in row | 2×2 grid | 1-column stack, ~76px per pill |
| Zone 3 Row A | 2fr/1fr | Stacked 1fr/1fr | Stacked, 320px each |
| Zone 3 Row B | 2fr/1fr | Stacked | Stacked; InventoryTable horizontal-scroll |
| Zone 4 | One chip row | Two rows | Vertical list |

### Mobile tap-target rule

Every interactive element ≥44px in its shortest dimension at `<768px`. Current code uses `h-8`/`h-9` on some buttons; PR-level fix bumps base to `h-11` and restores `md:h-8` at tablet/desktop.

### Theme

All new components use existing tokens (`bg-card`, `bg-page`, `text-ink-primary`, `text-ink-secondary`, `border-border`, `accent`, `accent-strong`). No new colors.

## Data bindings summary

| Binding | Hook | Endpoint | New? | Notes |
|---|---|---|---|---|
| Queue (expiry) | `useExpiryCalendar`, `useExpiryExposure` | existing | No | Client-side merge |
| Queue (stock) | `useReorderAlerts` | existing | No | Group by drug_code client-side |
| Queue (anomaly) | `useAnomalyCards(10)` | existing | No | Limit bumped from 6 |
| Queue (pipeline) | `usePipelineHealth` | existing | No | Only when failed |
| KPI Strip | `useDashboard` | existing | No | All fields on `dashboard.kpi` |
| RevenueChart | `useRevenueForecast(period)` | existing | No | Unchanged |
| ExpiryHeatmap | `useExpiryCalendar`, `useExpiryExposure` | existing | No | SWR dedupes with queue |
| InventoryTable | `useReorderAlerts` | existing | No | SWR dedupes with queue |
| BranchList | `useSites` | existing | **Maybe** | May need `revenue` and `risk_count` fields — verify in implementation |
| Pipeline chip | `usePipelineHealth` | existing | No | SWR dedupes with queue |
| Channels popover | `useChannels` | existing | No | Lazy-load on open |

**Potential backend work — single flagged item:** if `/api/v1/sites` doesn't include per-site `revenue` and `risk_count`, extend it with optional `?include=revenue,risk` query params OR join client-side against `/api/v1/sales-by-branch` + reorder-alerts. Resolution deferred to implementation plan.

## File inventory

### New files

- `frontend/src/components/dashboard/new/AttentionQueue.tsx` (~300 LOC)
- `frontend/src/components/dashboard/new/AttentionRow.tsx` (~80 LOC)
- `frontend/src/components/dashboard/new/AttentionChips.tsx` (~60 LOC)
- `frontend/src/components/dashboard/new/KpiStrip.tsx` (~180 LOC)
- `frontend/src/components/dashboard/new/DashboardFooterBar.tsx` (~120 LOC)
- `frontend/src/lib/attention-queue.ts` — pure merge + rank logic (~150 LOC)
- `frontend/src/lib/__tests__/attention-queue.test.ts` — Vitest

### Modified files

- `frontend/src/app/dashboard/page.tsx` — restructure layout; swap `KpiCard` → `KpiStrip`; mount `AttentionQueue`; mount `DashboardFooterBar`; remove direct card usage of `AlertBanner`, `AnomalyFeed`, `PipelineHealthCard`.
- `frontend/src/components/dashboard/new/index.ts` — export new components.

### Conditional deletions (grep in implementation)

- `AlertBanner` component — delete if zero other consumers.
- `AnomalyFeed` card — retain if used on another route (e.g. `/anomalies`); otherwise delete.
- `PipelineHealthCard` — retain if used elsewhere; otherwise delete.

## Acceptance criteria

1. **Layout.** On `≥1280px` with a mature tenant (OnboardingStrip hidden), zones appear in order Header → Zone 1 (AttentionQueue) → Zone 2 (KpiStrip) → Zone 3 Row A → Zone 3 Row B → Zone 4 (footer).
2. **AttentionQueue.**
   - Shows ≤8 rows by default; scrolls internally beyond 8.
   - Ranking follows the documented score formula; red precedes amber; ties broken on `alert_id`.
   - All four alert types appear when each has ≥1 qualifying row.
   - Clicking a row navigates to the matching drill target (see per-type rules above).
   - Empty state shows "All clear" with last-sync timestamp.
   - A filter chip renders only when its category count is ≥1.
3. **KpiStrip.** 4 pills in one row on desktop, 2×2 on tablet, stacked on mobile. Each pill drills to the correct page. Strip height ≤100px on desktop.
4. **Mobile (375px).** Zones 1–3A all readable without horizontal page scroll. Every interactive element has ≥44px shortest-side tap target.
5. **Performance.** Time-to-interactive ≤2s on the pharma sample dataset with cold SWR cache. AttentionQueue first paint within 500ms of hook resolution.
6. **Accessibility.** `axe` produces 0 critical/serious violations. Keyboard-only user can navigate the queue and drill any row.
7. **Telemetry preserved.** `trackFirstDashboardView` continues to fire on mount (Phase 2 #398/#399 contract).
8. **No regressions.**
   - Period tabs (Day/Week/Month/Quarter/YTD) still drive RevenueChart.
   - OnboardingStrip/FirstInsightCard still self-hide post-onboarding.
   - Dark/light theme applies to every new component.
   - Playwright E2E dashboard spec continues to pass after selector updates (updates are in-scope for this work).

## Open questions deferred to writing-plans

1. Does `useSites` already return `revenue` and `risk_count` per site? If not: extend endpoint vs client-side join — pick the cheaper path.
2. Does an `/anomalies` page exist? If not: does it need a full redesign, or is a thin list acceptable?
3. Grep for remaining consumers of `AlertBanner`, `AnomalyFeed` card, `PipelineHealthCard` before deciding delete vs keep.
4. Which Playwright specs reference dashboard selectors that will change? Estimate update cost.

## Out of scope

- Any other page redesign.
- AI/narrative briefing layer (future spec).
- Role-based home variation.
- Any new Python/FastAPI endpoint beyond the possible `useSites` extension.

## Related

- PR #502 — current `/dashboard` Daily Operations Overview (baseline).
- PR #564 — V2 shell unification (must remain intact).
- PR #569 — responsive V2 shell (must remain intact).
- Epic #398 / task #399 — Phase 2 Golden-Path telemetry (must remain intact).
