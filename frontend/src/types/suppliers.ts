export interface SupplierInfo {
  supplier_code: string;
  supplier_name: string;
  contact_name: string | null;
  contact_phone: string | null;
  contact_email: string | null;
  address: string | null;
  payment_terms_days: number;
  lead_time_days: number;
  is_active: boolean;
}

export interface SupplierPerformance {
  supplier_name: string;
  total_orders: number;
  avg_lead_days: number | null;
  fill_rate: number | null;
  total_spend: number;
  cancelled_count: number;
}
