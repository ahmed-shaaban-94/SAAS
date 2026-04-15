export interface BatchInfo {
  batch_key: number;
  drug_code: string;
  drug_name: string;
  site_code: string;
  batch_number: string;
  expiry_date: string;
  current_quantity: number;
  days_to_expiry: number;
  alert_level: "expired" | "critical" | "warning" | "caution" | "safe";
  computed_status?: string;
}

export interface ExpirySummary {
  site_code: string;
  site_name: string;
  expired_count: number;
  critical_count: number;
  warning_count: number;
  caution_count: number;
  total_expired_value: number;
}

export interface ExpiryCalendarDay {
  date: string;
  batch_count: number;
  total_quantity: number;
  alert_level: string;
}

export interface ExpiryAlert {
  drug_code: string;
  drug_name: string;
  drug_brand: string | null;
  batch_number: string;
  site_code: string;
  expiry_date: string;
  current_quantity: number;
  days_to_expiry: number;
  alert_level: "expired" | "critical" | "warning" | "caution" | "safe";
}

export interface QuarantinePayload {
  drug_code: string;
  site_code: string;
  batch_number: string;
  reason: string;
}

export interface WriteOffPayload extends QuarantinePayload {
  quantity: number;
}
