export interface TimeSeriesPoint {
  period: string;
  value: number;
}

export interface KPISparkline {
  metric: "revenue" | "orders" | "stock_risk" | "expiry_exposure";
  points: TimeSeriesPoint[];
}

export interface KPISummary {
  today_gross: number;
  mtd_gross: number;
  ytd_gross: number;
  period_gross: number;
  period_transactions: number;
  period_customers: number;
  today_discount: number;
  mom_growth_pct: number | null;
  yoy_growth_pct: number | null;
  daily_quantity: number;
  daily_transactions: number;
  daily_customers: number;
  avg_basket_size: number;
  daily_returns: number;
  mtd_transactions: number;
  ytd_transactions: number;
  sparkline?: TimeSeriesPoint[];
  sparklines?: KPISparkline[];
  mom_significance?: "significant" | "inconclusive" | "noise" | null;
  yoy_significance?: "significant" | "inconclusive" | "noise" | null;
  stock_risk_count?: number;
  stock_risk_delta?: number | null;
  expiry_exposure_egp?: number;
  expiry_batch_count?: number;
}

export interface HealthStatus {
  status: "ok" | "degraded";
  db: "connected" | "disconnected";
}

export interface ApiErrorShape {
  detail?: string;
}
