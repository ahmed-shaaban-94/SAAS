// POS module type definitions — mirrors src/datapulse/pos/models.py

export type TransactionStatus = "draft" | "completed" | "voided" | "returned";
export type TerminalStatus = "open" | "active" | "paused" | "closed";
export type PaymentMethod = "cash" | "card" | "insurance" | "voucher" | "mixed";
export type ReturnReason = "defective" | "wrong_drug" | "expired" | "customer_request";
export type ReceiptFormat = "thermal" | "pdf" | "email";
export type RefundMethod = "cash" | "credit_note";

// ---- Terminal ----

export interface TerminalSessionResponse {
  id: number;
  tenant_id: number;
  site_code: string;
  staff_id: string;
  terminal_name: string;
  status: TerminalStatus;
  opened_at: string;
  closed_at: string | null;
  opening_cash: number;
  closing_cash: number | null;
}

export interface TerminalOpenRequest {
  site_code: string;
  terminal_name: string;
  opening_cash: number;
}

export interface TerminalCloseRequest {
  closing_cash: number;
}

// ---- Cart / Transaction Items ----

export interface PosCartItem {
  drug_code: string;
  drug_name: string;
  batch_number: string | null;
  expiry_date: string | null;
  quantity: number;
  unit_price: number;
  discount: number;
  line_total: number;
  is_controlled: boolean;
}

// ---- Transactions ----

export interface TransactionResponse {
  id: number;
  tenant_id: number;
  terminal_id: number;
  staff_id: string;
  pharmacist_id: string | null;
  customer_id: string | null;
  site_code: string;
  subtotal: number;
  discount_total: number;
  tax_total: number;
  grand_total: number;
  payment_method: PaymentMethod | null;
  status: TransactionStatus;
  receipt_number: string | null;
  created_at: string;
}

export interface TransactionDetailResponse extends TransactionResponse {
  items: PosCartItem[];
}

export interface TransactionCreateRequest {
  terminal_id: number;
  site_code: string;
  customer_id?: string;
}

export interface AddItemRequest {
  drug_code: string;
  drug_name: string;
  batch_number?: string;
  expiry_date?: string;
  quantity: number;
  unit_price: number;
  discount?: number;
  is_controlled?: boolean;
  pharmacist_id?: string;
}

export interface UpdateItemRequest {
  quantity?: number;
  discount?: number;
  override_price?: number;
}

// ---- Checkout ----

export interface CheckoutRequest {
  payment_method: PaymentMethod;
  cash_tendered?: number;
  insurance_no?: string;
  split_cash?: number;
  split_insurance?: number;
  // Optional voucher code to redeem atomically at checkout
  voucher_code?: string;
}

export interface CheckoutResponse {
  transaction: TransactionResponse;
  change_amount: number;
  receipt_number: string;
}

// ---- Void ----

export interface VoidRequest {
  reason: string;
}

export interface VoidResponse {
  id: number;
  transaction_id: number;
  tenant_id: number;
  voided_by: string;
  reason: string;
  voided_at: string;
}

// ---- Product Search ----

export interface PosProductResult {
  drug_code: string;
  drug_name: string;
  drug_brand: string | null;
  is_controlled: boolean;
  unit_price: number;
  stock_available: number;
}

export interface PosStockInfo {
  drug_code: string;
  drug_name: string;
  quantity_available: number;
  batches: PosStockBatch[];
}

export interface PosStockBatch {
  batch_number: string;
  expiry_date: string;
  quantity_available: number;
}

// ---- Receipts ----

export interface EmailReceiptRequest {
  email: string;
}

// ---- Shifts ----

export interface ShiftSummaryResponse {
  id: number;
  terminal_id: number;
  staff_id: string;
  shift_date: string;
  opened_at: string;
  closed_at: string | null;
  opening_cash: number;
  closing_cash: number | null;
  expected_cash: number | null;
  variance: number | null;
  total_sales: number;
  total_transactions: number;
  total_returns: number;
}

export interface CashCountRequest {
  amount: number;
}

export interface CashDrawerEventResponse {
  id: number;
  terminal_id: number;
  event_type: string;
  amount: number;
  timestamp: string;
}

// ---- Returns ----

export interface ReturnRequest {
  original_transaction_id: number;
  items: PosCartItem[];
  reason: ReturnReason;
  refund_method: RefundMethod;
  notes?: string;
}

export interface ReturnResponse {
  id: number;
  original_transaction_id: number;
  return_transaction_id: number | null;
  staff_id: string;
  reason: ReturnReason;
  refund_amount: number;
  refund_method: RefundMethod;
  notes: string | null;
  created_at: string;
}

// ---- Pharmacist Verification ----

export interface PharmacistVerifyRequest {
  drug_code: string;
  pin: string;
}

export interface PharmacistVerifyResponse {
  verified: boolean;
  pharmacist_id: string;
}

// ---- Pagination ----

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
}
