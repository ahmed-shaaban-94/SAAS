export interface BillingStatus {
  plan: string;
  plan_name: string;
  price_display: string;
  subscription_status: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  data_sources_used: number;
  data_sources_limit: number; // -1 = unlimited
  total_rows_used: number;
  total_rows_limit: number; // -1 = unlimited
  ai_insights: boolean;
  pipeline_automation: boolean;
  quality_gates: boolean;
}

export interface CheckoutRequest {
  price_id: string;
  success_url?: string;
  cancel_url?: string;
}

export interface CheckoutResponse {
  checkout_url: string;
}

export interface PortalResponse {
  portal_url: string;
}
