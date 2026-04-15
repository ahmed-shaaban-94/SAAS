export interface DispenseRate {
  product_key: number;
  drug_code: string;
  drug_name: string;
  drug_brand: string;
  site_code: string;
  site_name: string;
  avg_daily_dispense: number;
  avg_weekly_dispense: number;
  avg_monthly_dispense: number;
  active_days: number;
}

export interface DaysOfStock {
  product_key: number;
  drug_code: string;
  drug_name: string;
  site_code: string;
  current_quantity: number;
  days_of_stock: number | null;
  avg_daily_dispense: number;
}

export interface VelocityClassification {
  product_key: number;
  drug_code: string;
  drug_name: string;
  drug_brand: string;
  lifecycle_stage: string | null;
  velocity_class: "fast_mover" | "normal_mover" | "slow_mover" | "dead_stock";
  avg_daily_dispense: number;
}

export interface StockoutRisk {
  product_key: number;
  drug_code: string;
  drug_name: string;
  site_code: string;
  current_quantity: number;
  days_of_stock: number | null;
  risk_level: "stockout" | "critical" | "at_risk";
  suggested_reorder_qty: number;
}

export interface ReconciliationEntry {
  drug_code: string;
  drug_name: string;
  site_code: string;
  calculated_qty: number;
  physical_qty: number | null;
  variance: number | null;
  variance_pct: number | null;
  last_count_date: string | null;
}

export interface ReconciliationData {
  total_items: number;
  items_with_variance: number;
  total_variance_value: number;
  entries: ReconciliationEntry[];
}
