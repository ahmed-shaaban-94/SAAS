# Handoff: DataPulse — Dashboard (Daily Operations Overview)

## Overview
High-fidelity dashboard for DataPulse (Egyptian pharmacy chain analytics). Single-page "Daily operations overview" view with sidebar nav, KPI row, AI alert banner, revenue trend with forecast, channel split donut, reorder watchlist, expiry heatmap, top branches, anomalies feed, and pipeline health.

## About the Design Files
These are **design references created in HTML/CSS** — a static prototype showing intended look, structure, and data shape. **Do not ship the HTML directly.** Recreate it in your target codebase using its existing component library, charting library, and design system. If no stack exists yet, use React + a lightweight chart library (Recharts, Visx, or Nivo).

## Fidelity
**High-fidelity (hifi).** All colors, type scale, spacing, component shapes, and copy are final.

## Layout
- Grid: `sidebar (248px) | main content`, main padding `28px 32px 64px`.
- Sidebar: sticky 100vh, branded logo mark, section labels (ALL-CAPS · 10.5px · 0.22em tracking), nav links (13.5px, pill with 2px inset-left accent when active).
- Content sections stacked vertically, separated by ~20px gaps:
  1. **Title row** — greeting + synced badge; on the right a segmented control (Day / Week / Month active / Quarter / YTD) + Export button + primary "New report" button.
  2. **AI alert banner** — full-width, cyan-tinted, with sparkle icon, bold AI insight copy, "Investigate →" action.
  3. **KPI row** — 4 equal cards (Total Revenue / Orders / Stock Risk / Expiry Exposure), each with colored accent (`--kpi-color`), icon chip, label, large tabular value, delta pill + meta, full-width sparkline SVG at bottom.
  4. **Revenue + Channel** — 2-col grid. Revenue card has 3 stat blocks (This month / Forecast / Target), legend row, and a 700×240 SVG area chart with actual (solid cyan with gradient fill), forecast (dashed purple with confidence band), target dashed line, TODAY marker, and x-axis date labels. Channel card has a donut (4 segments), row list with colored swatch / bar / %, and footer insight.
  5. **Inventory (2 cols) + Expiry calendar (1 col)** — reorder watchlist table with status pills (Critical red / Low amber / Healthy green) + per-row "Reorder →" action. Expiry card has copy summary, 14×7 cell heatmap (98 cells, amber→red gradient), legend, and 3-tier exposure rows.
  6. **Branches + Anomalies + Pipeline** — 3-col grid. Branches ranked list with gold #01. Anomalies feed with up/down/info icon badges + confidence tag. Pipeline shows Bronze/Silver/Gold medallion nodes (Silver "Running…"), quality gates counters, dbt tests, and a 7-day run history bar chart.

## Design Tokens

```
Surfaces
  --bg-page: #081826
  --bg-card: #102a43
  --bg-elevated: #163452
  --panel-soft: #1a3550
  --surface-strong: #243b53

Ink
  --text-primary: #f7fbff
  --text-secondary: #b8c0cc
  --text-tertiary: #8597a8

Lines
  --border-color: #33506b
  --divider: #46627c
  (hairline rgba variants used throughout)

Accents
  --accent: #00c7f2
  --accent-strong: #5cdfff
  --chart-blue: #20bce5
  --chart-purple: #7467f8
  --chart-amber: #ffab3d
  --growth-green: #1dd48b
  --growth-red: #ff7b7b

Page bg
  radial-gradient 20% 0% rgba(0,199,242,0.08) + 80% 100% rgba(116,103,248,0.06)
  + linear-gradient #061320 → #081826

Typography
  Inter 400/500/600/700/800 (body, numerals use tabular-nums)
  JetBrains Mono 400/500 (SKUs, dates, mono hints, axis labels)

Sizes
  h1.page-title: 30px / -0.025em / 700
  card h3: ~15px / 600
  KPI value: ~30px tabular
  body: 13–14px
  micro labels: 10.5px ALL-CAPS 0.18–0.22em

Radii
  cards: 14–16
  pills/chips: 999
  sparkline container: 8
```

## Data Shapes (for developer wiring)
```ts
KPI     { label, value, delta: { dir: 'up'|'down', pct }, sub, color, sparkline: number[] }
RevenueSeries { actual: Point[], forecast: Point[], target: number, today: Date }
Channel { label, color, value, pct }
InvRow  { name, sku, onHand, daysOfStock, velocity, status: 'critical'|'low'|'healthy' }
ExpiryHeat number[98]   // 14 weeks × 7 days, 0–5 severity
Branch  { rank, name, region, staff, revenue, deltaPct }
Anomaly { kind: 'up'|'down'|'info', title, body, timeAgo, confidence }
Pipeline{ bronzeRows, silverStatus, goldMarts, lastRunAt, duration, gates, tests, nextRunAt, history: number[7] }
```

## Interactions & Behavior
- Period segmented control swaps the revenue chart + KPI sparklines.
- Branch chips on Inventory card filter the table.
- "Reorder →" link opens a reorder flow (out of scope for this screen).
- Anomaly cards can be expanded (scope: title + body + confidence).
- Heatmap cells tooltip on hover with week/day/exposure EGP.
- All numbers animate in (count-up) on initial mount, 600ms ease-out.

## Assets
No bitmaps. All iconography inline SVG (Lucide/Feather style, 14–18px, stroke 2). Sparklines and charts are hand-rolled SVG in the prototype — replace with the codebase's chart library.

## Files
```
design_handoff_dashboard/
  README.md                    ← this file
  Dashboard v1.html            ← visual reference (open in a browser)
  tailwind.config.js           ← extended Tailwind theme with DataPulse tokens
  src/
    tokens.css                 ← CSS vars for effects Tailwind can't express (gradients)
    Dashboard.jsx              ← page shell + layout
    data/
      mock.js                  ← all mock data (swap for real API calls)
    components/
      Sidebar.jsx
      AlertBanner.jsx
      KpiCard.jsx
      RevenueChart.jsx
      ChannelDonut.jsx
      InventoryTable.jsx
      ExpiryHeatmap.jsx
      BranchList.jsx
      AnomalyFeed.jsx
      PipelineHealth.jsx
```

## Integration Notes for Claude Code
1. **Tailwind**: merge `tailwind.config.js` theme extensions into your existing config (colors, fontFamily, borderRadius, backgroundImage). If you use Tailwind v4, port tokens to `@theme` directives instead.
2. **Icons**: every component uses text glyphs (◆, ↗, ↘) as placeholders. Replace with your icon system (lucide-react, Heroicons, or custom SVG set). Target size 14–18px, stroke 2.
3. **Charts**: `RevenueChart` and `ChannelDonut` are hand-rolled SVG for the prototype. Prefer your chart library — signatures are annotated in each file.
4. **Data**: all mocks live in `src/data/mock.js`. Replace imports with React Query / SWR / RTK hooks that return the same shape.
5. **Layout**: `Dashboard.jsx` is the only component that knows the grid. Component cards don't set their own width — they fill the grid cell.
6. **Accessibility TODO**: add ARIA labels to sparklines + heatmap, keyboard focus styles on nav/segmented controls, `aria-live="polite"` on the AI alert banner.
