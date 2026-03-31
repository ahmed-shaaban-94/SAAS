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
  customer_name: string;
  return_quantity: number;
  return_amount: number;
  return_count: number;
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
  billing_way: string;
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
