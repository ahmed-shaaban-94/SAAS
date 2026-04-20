import type { AlertData, GreetingData, KpiData } from "./types";

/**
 * Design-handoff fixtures, to be replaced by live SWR hooks once
 * backend endpoints #503, #504, #505, #506, #507, #508, #509, #510 land.
 * Shape matches frontend/design-handoff/dashboard/src/data/mock.js.
 */

export const greeting: GreetingData = {
  name: "Ahmed",
  dateLabel: "Apr 20, 2026",
  syncedAgo: "2m ago",
};

export const kpis: KpiData[] = [
  {
    id: "revenue",
    label: "Total Revenue",
    value: "EGP 4.28M",
    delta: { dir: "up", text: "12.5%" },
    sub: "vs last month",
    color: "accent",
    sparkline: [32, 28, 30, 22, 24, 18, 16, 20, 12, 10, 6],
  },
  {
    id: "orders",
    label: "Orders",
    value: "23,847",
    delta: { dir: "up", text: "8.3%" },
    sub: "1,245 today",
    color: "purple",
    sparkline: [24, 26, 20, 22, 18, 16, 20, 14, 16, 10, 12],
  },
  {
    id: "stock",
    label: "Stock Risk",
    value: "34",
    valueSuffix: "SKUs",
    delta: { dir: "down", text: "6 new" },
    sub: "needing reorder",
    color: "amber",
    sparkline: [30, 28, 26, 24, 22, 24, 20, 18, 22, 16, 14],
  },
  {
    id: "expiry",
    label: "Expiry Exposure",
    value: "EGP 142K",
    delta: { dir: "down", text: "30-day window" },
    sub: "12 batches",
    color: "red",
    sparkline: [14, 18, 16, 22, 20, 26, 24, 30, 28, 32, 34],
  },
];

export const alert: AlertData = {
  title: "AI insight",
  body:
    "Revenue in Maadi branch dropped 18% this week despite a 4% traffic increase — consistent with a stockout in top-5 SKUs. Expected impact: EGP 86K / week.",
  action: "Investigate",
  actionHref: "/dashboard/v3/anomalies",
};
