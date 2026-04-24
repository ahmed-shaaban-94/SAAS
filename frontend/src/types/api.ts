export interface KPISparkline {
  metric: "revenue" | "orders" | "stock_risk" | "expiry_exposure";
  points: TimeSeriesPoint[];
}

export interface KPISummary {
  // Gross sales (primary — net deliberately excluded)
  /** @deprecated Use period_gross. Legacy name kept for AI Light, n8n, and mobile app. */
  today_gross: number;
  mtd_gross: number;
  ytd_gross: number;
  // Period-aware aliases — preferred for new frontend consumers
  period_gross: number;
  period_transactions: number;
  period_customers: number;
  // Discount (kept for forecasting)
  today_discount: number;
  // Growth (based on gross)
  mom_growth_pct: number | null;
  yoy_growth_pct: number | null;
  // Units (quantity — returns are negative, so sum is net units)
  daily_quantity: number;
  /** @deprecated Use period_transactions. Legacy name kept for AI Light, n8n, and mobile app. */
  daily_transactions: number;
  /** @deprecated Use period_customers. Legacy name kept for AI Light, n8n, and mobile app. */
  daily_customers: number;
  avg_basket_size: number;
  daily_returns: number;
  mtd_transactions: number;
  ytd_transactions: number;
  sparkline?: TimeSeriesPoint[];
  /** Per-metric sparklines for the new dashboard KPI row (#503). */
  sparklines?: KPISparkline[];
  mom_significance?: "significant" | "inconclusive" | "noise" | null;
  yoy_significance?: "significant" | "inconclusive" | "noise" | null;
  // Dashboard KPI row additions (#503)
  stock_risk_count?: number;
  stock_risk_delta?: number | null;
  expiry_exposure_egp?: number;
  expiry_batch_count?: number;
}

export interface TimeSeriesPoint {
  period: string;
  value: number;
}

export interface StatisticalAnnotation {
  z_score: number | null;
  cv: number | null;
  significance: "significant" | "inconclusive" | "noise" | null;
}

export interface TrendResult {
  points: TimeSeriesPoint[];
  total: number;
  average: number;
  minimum: number;
  maximum: number;
  growth_pct: number | null;
  stats?: StatisticalAnnotation | null;
}

export interface RankingItem {
  rank: number;
  key: number;
  name: string;
  value: number;
  pct_of_total: number;
  /** Populated only for site rankings (#507). */
  staff_count?: number | null;
}

export interface RankingResult {
  items: RankingItem[];
  total: number;
  active_count?: number;
}

export interface ReturnAnalysis {
  drug_name: string;
  drug_brand: string;
  customer_name: string;
  origin: string;
  return_quantity: number;
  return_amount: number;
  return_count: number;
  return_rate?: number;
}

export interface FilterOptions {
  categories: string[];
  brands: string[];
  sites: Array<{ key: number; label: string }>;
  staff: Array<{ key: number; label: string }>;
}

export interface HealthStatus {
  status: "ok" | "degraded";
  db: "connected" | "disconnected";
}

export type FirstInsightKind =
  | "mom_change"
  | "expiry_risk"
  | "stock_risk"
  | "top_seller";

export interface FirstInsight {
  kind: FirstInsightKind;
  title: string;
  body: string;
  action_href: string;
  confidence: number;
}

export interface FirstInsightResponse {
  insight: FirstInsight | null;
}


// --- AI-Light types (Phase 2.8) ---

export interface AISummary {
  narrative: string;
  highlights: string[];
  period: string;
}

export interface Anomaly {
  date: string;
  metric: string;
  actual_value: number;
  expected_range_low: number;
  expected_range_high: number;
  severity: string;
  description: string;
}

export interface AnomalyReport {
  anomalies: Anomaly[];
  period: string;
  total_checked: number;
}

export interface ChangeDelta {
  metric: string;
  previous_value: number;
  current_value: number;
  change_pct: number;
  direction: string;
}

export interface ChangeNarrative {
  narrative: string;
  deltas: ChangeDelta[];
  current_period: string;
  previous_period: string;
}

export interface AIStatus {
  available: boolean;
}

// --- Detail types (Product & Customer) ---

export interface ProductPerformance {
  product_key: number;
  drug_code: string;
  drug_name: string;
  drug_brand: string;
  drug_category: string;
  total_quantity: number;
  total_sales: number;
  total_net_amount: number;
  return_rate: number;
  unique_customers: number;
  monthly_trend?: TimeSeriesPoint[];
}

export interface CustomerAnalytics {
  customer_key: number;
  customer_id: string;
  customer_name: string;
  total_quantity: number;
  total_net_amount: number;
  transaction_count: number;
  unique_products: number;
  return_count: number;
  monthly_trend?: TimeSeriesPoint[];
}

export interface StaffPerformance {
  staff_key: number;
  staff_id: string;
  staff_name: string;
  staff_position: string;
  total_net_amount: number;
  transaction_count: number;
  avg_transaction_value: number;
  unique_customers: number;
  monthly_trend?: TimeSeriesPoint[];
}

// --- Phase 2: Billing & Customer Type ---

// --- Phase 3: Comparative Analytics ---

export interface MoverItem {
  key: number;
  name: string;
  current_value: number;
  previous_value: number;
  change_pct: number;
  direction: "up" | "down";
}

export interface TopMovers {
  gainers: MoverItem[];
  losers: MoverItem[];
  entity_type: string;
}

// --- Phase 4: Site Detail & Product Hierarchy ---

export interface SiteDetail {
  site_key: number;
  site_code: string;
  site_name: string;
  area_manager: string;
  total_net_amount: number;
  transaction_count: number;
  unique_customers: number;
  unique_staff: number;
  walk_in_ratio: number;
  insurance_ratio: number;
  return_rate: number;
  monthly_trend?: TimeSeriesPoint[];
}

// --- Explore types (Phase 3: Self-serve analytics) ---

export interface ExploreDimension {
  name: string;
  label: string;
  description: string;
  dimension_type: "string" | "number" | "date" | "boolean";
  model: string;
}

export interface ExploreMetric {
  name: string;
  label: string;
  description: string;
  metric_type: "sum" | "average" | "count" | "count_distinct" | "min" | "max";
  column: string;
  model: string;
}

export interface ExploreJoinPath {
  join_model: string;
  sql_on: string;
}

export interface ExploreModel {
  name: string;
  label: string;
  description: string;
  schema_name: string;
  dimensions: ExploreDimension[];
  metrics: ExploreMetric[];
  joins: ExploreJoinPath[];
}

export interface ExploreCatalog {
  models: ExploreModel[];
}

export interface ExploreFilter {
  field: string;
  operator: string;
  value: string | number | boolean | string[];
}

export interface ExploreSortSpec {
  field: string;
  direction: "asc" | "desc";
}

export interface ExploreQueryRequest {
  model: string;
  dimensions: string[];
  metrics: string[];
  filters: ExploreFilter[];
  sorts: ExploreSortSpec[];
  limit: number;
}

export interface ExploreResult {
  columns: string[];
  rows: (string | number | boolean | null)[][];
  row_count: number;
  sql: string;
  truncated: boolean;
}

// --- Phase 5: CEO Review — Advanced Analytics ---

export interface CustomerSegment {
  customer_key: number;
  customer_id: string;
  customer_name: string;
  rfm_segment: string;
  r_score: number;
  f_score: number;
  m_score: number;
  days_since_last: number;
  frequency: number;
  monetary: number;
  avg_basket_size: number;
  return_rate: number;
}

export interface ForecastPoint {
  period: string;
  value: number;
  lower_bound: number;
  upper_bound: number;
}

export interface ForecastResult {
  entity_type: string;
  entity_key: number | null;
  method: string;
  horizon: number;
  granularity: string;
  points: ForecastPoint[];
  accuracy_metrics: {
    mape: number;
    mae: number;
    rmse: number;
    coverage: number;
  } | null;
}

export interface ForecastSummary {
  last_run_at: string | null;
  next_30d_revenue: number;
  next_3m_revenue: number;
  revenue_trend: string;
  mape: number | null;
  top_growing_products: { product_key: number; drug_name: string; forecast_change_pct: number }[];
  top_declining_products: { product_key: number; drug_name: string; forecast_change_pct: number }[];
}

export interface TargetVsActual {
  period: string;
  target_value: number;
  actual_value: number;
  variance: number;
  achievement_pct: number;
}

export interface TargetSummary {
  monthly_targets: TargetVsActual[];
  ytd_target: number;
  ytd_actual: number;
  ytd_achievement_pct: number;
}

export interface BudgetVsActualItem {
  month: number;
  month_name: string;
  origin: string;
  budget: number;
  actual: number;
  variance: number;
  achievement_pct: number;
}

export interface BudgetOriginSummary {
  origin: string;
  ytd_budget: number;
  ytd_actual: number;
  ytd_variance: number;
  ytd_achievement_pct: number;
}

export interface BudgetSummary {
  monthly: BudgetVsActualItem[];
  by_origin: BudgetOriginSummary[];
  ytd_budget: number;
  ytd_actual: number;
  ytd_achievement_pct: number;
}

export interface AlertLogItem {
  id: number;
  alert_config_id: number | null;
  alert_name: string;
  fired_at: string;
  metric_value: number | null;
  threshold_value: number | null;
  message: string | null;
  acknowledged: boolean;
}

// --- Enhancement 4: Analytics Intelligence ---

export interface CustomerHealthScore {
  customer_key: number;
  customer_name: string;
  health_score: number;
  health_band: "Thriving" | "Healthy" | "Needs Attention" | "At Risk" | "Critical";
  recency_days: number;
  frequency_3m: number;
  monetary_3m: number;
  return_rate: number;
  product_diversity: number;
  trend: "improving" | "stable" | "declining" | "new";
}

export interface HealthDistribution {
  thriving: number;
  healthy: number;
  needs_attention: number;
  at_risk: number;
  critical: number;
  total: number;
}

export interface AnomalyAlertItem {
  id: number;
  metric: string;
  period: string;
  actual_value: number;
  expected_value: number;
  z_score: number | null;
  severity: "critical" | "high" | "medium" | "low";
  direction: "spike" | "drop";
  is_suppressed: boolean;
  suppression_reason: string | null;
  acknowledged: boolean;
}

// ───────────────────────────────────────────────────────────────────────
// New dashboard design — composite / display-ready payloads
// ───────────────────────────────────────────────────────────────────────

/** #506 — exposure tier (30/60/90 days) for the expiry widget. */
export interface ExpiryExposureTier {
  tier: "30d" | "60d" | "90d";
  label: string;
  total_egp: number;
  batch_count: number;
  tone: "red" | "amber" | "green";
}

/** #508 — display projection for the dashboard anomaly feed. */
export interface AnomalyCard {
  id: number;
  kind: "up" | "down" | "info";
  title: string;
  body: string;
  time_ago: string;
  confidence: "high" | "medium" | "low" | "info";
}

/** #510 — single actionable insight for the dashboard alert banner. */
export interface TopInsight {
  title: string;
  body: string;
  expected_impact_egp: number | null;
  action_label: string;
  action_target: string;
  confidence: "high" | "medium" | "low" | "info";
  generated_at: string;
}

