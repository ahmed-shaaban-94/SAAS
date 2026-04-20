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

// --- Pipeline types (Phase 2.7) ---

export interface PipelineRun {
  id: string;
  tenant_id: number;
  run_type: string;
  status: string;
  trigger_source: string | null;
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  rows_loaded: number | null;
  error_message: string | null;
  metadata: Record<string, unknown>;
}

export interface PipelineRunList {
  items: PipelineRun[];
  total: number;
  offset: number;
  limit: number;
}

export interface QualityCheck {
  id: number;
  tenant_id: number;
  pipeline_run_id: string;
  check_name: string;
  stage: string;
  severity: string;
  passed: boolean;
  message: string | null;
  details: Record<string, unknown>;
  checked_at: string;
}

export interface QualityCheckList {
  items: QualityCheck[];
  total: number;
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

export interface QualityRunDetail {
  run_id: string;
  checks: QualityCheck[];
  total_checks: number;
  passed: number;
  failed: number;
  warned: number;
}

export interface TriggerResponse {
  run_id: string;
  status: string;
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

export interface BillingBreakdownItem {
  billing_group: string;
  transaction_count: number;
  total_net_amount: number;
  pct_of_total: number;
}

export interface BillingBreakdown {
  items: BillingBreakdownItem[];
  total_transactions: number;
  total_net_amount: number;
}

export interface CustomerTypeBreakdownItem {
  period: string;
  walk_in_count: number;
  insurance_count: number;
  other_count: number;
  total_count: number;
}

export interface CustomerTypeBreakdown {
  items: CustomerTypeBreakdownItem[];
}

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

export interface ProductInCategory {
  product_key: number;
  drug_name: string;
  total_net_amount: number;
  transaction_count: number;
}

export interface BrandGroup {
  brand: string;
  total_net_amount: number;
  products: ProductInCategory[];
}

export interface CategoryGroup {
  category: string;
  total_net_amount: number;
  brands: BrandGroup[];
}

export interface ProductHierarchy {
  categories: CategoryGroup[];
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

export interface ABCItem {
  rank: number;
  key: number;
  name: string;
  value: number;
  cumulative_pct: number;
  abc_class: "A" | "B" | "C";
}

export interface ABCAnalysis {
  items: ABCItem[];
  total: number;
  class_a_count: number;
  class_b_count: number;
  class_c_count: number;
  class_a_pct: number;
  class_b_pct: number;
  class_c_pct: number;
}

export interface HeatmapCell {
  date: string;
  value: number;
}

export interface HeatmapData {
  cells: HeatmapCell[];
  min_value: number;
  max_value: number;
}

export interface ReturnsTrendPoint {
  period: string;
  return_count: number;
  return_amount: number;
  return_rate: number;
}

export interface ReturnsTrend {
  points: ReturnsTrendPoint[];
  total_returns: number;
  total_return_amount: number;
  avg_return_rate: number;
}

export interface SegmentSummary {
  segment: string;
  count: number;
  total_revenue: number;
  avg_monetary: number;
  avg_frequency: number;
  pct_of_customers: number;
}

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

export interface RevenueDriver {
  dimension: string;
  entity_key: number;
  entity_name: string;
  current_value: number;
  previous_value: number;
  impact: number;
  impact_pct: number;
  direction: "positive" | "negative";
}

export interface WaterfallAnalysis {
  current_total: number;
  previous_total: number;
  total_change: number;
  total_change_pct: number | null;
  drivers: RevenueDriver[];
  unexplained: number;
}

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

/** #505 — single sales-channel segment of the donut. */
export interface ChannelShare {
  channel: "retail" | "wholesale" | "institution" | "online";
  label: string;
  value_egp: number;
  pct_of_total: number;
  source: "derived" | "unavailable";
}

export interface ChannelsBreakdown {
  items: ChannelShare[];
  total_egp: number;
  data_coverage: "partial" | "full";
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

/** #509 — composite /pipeline/health payload. */
export interface PipelineHealthNode {
  label: "Bronze" | "Silver" | "Gold";
  value: string;
  status: "ok" | "running" | "pending" | "failed";
}

export interface PipelineHealthRun {
  at: string;
  duration_seconds: number | null;
}

export interface PipelineHealthCounter {
  passed: number;
  total: number;
}

export interface PipelineHealthHistoryPoint {
  date: string;
  duration_seconds: number | null;
  status: "ok" | "warning" | "fail" | "none";
}

export interface PipelineHealth {
  nodes: PipelineHealthNode[];
  last_run: PipelineHealthRun | null;
  next_run_at: string | null;
  gates: PipelineHealthCounter;
  tests: PipelineHealthCounter;
  history_7d: PipelineHealthHistoryPoint[];
}

/** #504 — composite /analytics/revenue-forecast payload. */
export interface ForecastBandPoint {
  date: string;
  value: number;
  ci_low: number;
  ci_high: number;
}

export interface RevenueTarget {
  period_end: string;
  value: number;
  status: "on_track" | "behind" | "ahead" | "unknown";
}

export interface RevenueForecastStats {
  this_period_egp: number;
  delta_pct: number | null;
  confidence: number | null;
}

export interface RevenueForecast {
  actual: TimeSeriesPoint[];
  forecast: ForecastBandPoint[];
  target: RevenueTarget | null;
  today: string;
  period: "day" | "week" | "month" | "quarter" | "ytd";
  stats: RevenueForecastStats;
}

/**
 * #507 — enriched reorder-alert shape returned directly by the backend.
 *
 * Distinct from the legacy ``ReorderAlert`` in ``types/inventory.ts``,
 * which predates the velocity/status enrichment and is consumed by
 * older pages via an adapter hook. New widgets use this shape as-is.
 */
export interface ReorderWatchlistItem {
  product_key: number;
  site_key: number;
  drug_code: string;
  drug_name: string;
  site_code: string;
  current_quantity: number;
  reorder_point: number;
  reorder_quantity: number;
  daily_velocity: number;
  days_of_stock: number | null;
  status: "critical" | "low" | "healthy";
}
