export interface StockLevel {
  product_key: number;
  drug_code: string;
  drug_name: string;
  drug_brand: string;
  site_key: number;
  site_code: string;
  site_name: string;
  current_quantity: number;
  total_received: number;
  total_dispensed: number;
  total_wastage: number;
  last_movement_date: string | null;
}

export interface StockMovement {
  movement_key: number;
  movement_date: string;
  movement_type: string;
  drug_code: string;
  drug_name: string;
  site_code: string;
  batch_number: string | null;
  quantity: number;
  unit_cost: number | null;
  reference: string | null;
}

export interface StockValuation {
  product_key: number;
  drug_code: string;
  drug_name: string;
  site_key: number;
  site_code: string;
  current_quantity: number;
  weighted_avg_cost: number;
  stock_value: number;
}

export interface ReorderAlert {
  product_key: number;
  drug_code: string;
  drug_name: string;
  site_code: string;
  site_name: string;
  current_quantity: number;
  reorder_point: number;
  risk_level: "stockout" | "critical" | "at_risk";
  suggested_reorder_qty: number;
  days_of_stock: number | null;
  /** trailing-30d avg units/day (#507) */
  velocity?: number | null;
  /** derived tier for the new dashboard watchlist (#507) */
  status?: "critical" | "low" | "healthy";
}

export interface ReorderConfig {
  id?: number;
  tenant_id?: number;
  drug_code: string;
  site_code: string;
  min_stock: number;
  reorder_point: number;
  max_stock: number;
  reorder_lead_days: number;
  is_active: boolean;
}

export interface StockHistoryPoint {
  movement_date: string;
  stock_level: number;
  net_change: number;
}
