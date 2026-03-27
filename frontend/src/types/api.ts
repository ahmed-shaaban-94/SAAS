export interface KPISummary {
  today_net: number;
  mtd_net: number;
  ytd_net: number;
  mom_growth_pct: number | null;
  yoy_growth_pct: number | null;
  daily_transactions: number;
  daily_customers: number;
}

export interface TimeSeriesPoint {
  period: string;
  value: number;
}

export interface TrendResult {
  points: TimeSeriesPoint[];
  total: number;
  average: number;
  minimum: number;
  maximum: number;
  growth_pct: number | null;
}

export interface RankingItem {
  rank: number;
  key: number;
  name: string;
  value: number;
  pct_of_total: number;
}

export interface RankingResult {
  items: RankingItem[];
  total: number;
}

export interface ReturnAnalysis {
  drug_name: string;
  customer_name: string;
  return_quantity: number;
  return_amount: number;
  return_count: number;
}

export interface HealthStatus {
  status: "ok" | "degraded";
  db: "connected" | "disconnected";
}
