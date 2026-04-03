export interface KPISummary {
  today_net: number;
  mtd_net: number;
  ytd_net: number;
  mom_growth_pct: number | null;
  yoy_growth_pct: number | null;
  daily_transactions: number;
  daily_customers: number;
  avg_basket_size: number;
  daily_returns: number;
  mtd_transactions: number;
  ytd_transactions: number;
  sparkline?: TimeSeriesPoint[];
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
  product_name?: string;
  customer_name: string;
  return_quantity: number;
  return_amount: number;
  return_count: number;
  return_rate?: number;
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
