export interface PurchaseOrder {
  po_number: string;
  po_date: string;
  supplier_code: string;
  supplier_name: string;
  site_code: string;
  site_name: string;
  status: "draft" | "submitted" | "partial" | "received" | "cancelled";
  expected_date: string | null;
  total_ordered_value: number;
  total_received_value: number;
  line_count: number;
}

export interface POLine {
  po_number: string;
  line_number: number;
  drug_code: string;
  drug_name: string;
  ordered_quantity: number;
  unit_price: number;
  received_quantity: number;
  line_total: number;
  fulfillment_pct: number;
}

export interface PODetailResponse extends PurchaseOrder {
  lines: POLine[];
}

export interface POCreateRequest {
  po_date: string;
  supplier_code: string;
  site_code: string;
  expected_date?: string;
  lines: Array<{ drug_code: string; quantity: number; unit_price: number }>;
}
