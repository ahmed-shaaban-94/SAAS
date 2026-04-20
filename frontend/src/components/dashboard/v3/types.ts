export interface KpiData {
  id: "revenue" | "orders" | "stock" | "expiry";
  label: string;
  value: string;
  valueSuffix?: string;
  delta: { dir: "up" | "down"; text: string };
  sub: string;
  color: "accent" | "purple" | "amber" | "red";
  sparkline: number[];
}

export interface AlertData {
  title: string;
  body: string;
  action: string;
  actionHref?: string;
}

export interface GreetingData {
  name: string;
  dateLabel: string;
  syncedAgo: string;
}

export type PeriodId = "Day" | "Week" | "Month" | "Quarter" | "YTD";
