/**
 * Promotion types — mirror the Pydantic models in `src/datapulse/pos/models.py`.
 *
 * Phase 2 of the POS discount system. Promotions are admin-managed seasonal
 * campaigns that cashiers explicitly apply at checkout (never auto-applied).
 * Financial fields arrive as JSON numbers.
 */

export type PromotionDiscountType = "amount" | "percent";

export type PromotionScope =
  | "all"
  | "items"
  | "category"
  | "brand"
  | "active_ingredient";

export type PromotionStatus = "active" | "paused" | "expired";

export type AppliedDiscountSource = "voucher" | "promotion";

export interface AppliedDiscount {
  source: AppliedDiscountSource;
  ref: string;
}

export interface Promotion {
  id: number;
  tenant_id: number;
  name: string;
  description: string | null;
  discount_type: PromotionDiscountType;
  value: number;
  scope: PromotionScope;
  starts_at: string;
  ends_at: string;
  min_purchase: number | null;
  max_discount: number | null;
  status: PromotionStatus;
  scope_items: string[];
  scope_categories: string[];
  scope_brands: string[];
  scope_active_ingredients: string[];
  usage_count: number;
  total_discount_given: number;
  created_at: string;
}

export interface PromotionCreateInput {
  name: string;
  description?: string | null;
  discount_type: PromotionDiscountType;
  value: number;
  scope: PromotionScope;
  starts_at: string;
  ends_at: string;
  min_purchase?: number | null;
  max_discount?: number | null;
  scope_items?: string[];
  scope_categories?: string[];
  scope_brands?: string[];
  scope_active_ingredients?: string[];
}

export interface PromotionUpdateInput {
  name?: string;
  description?: string | null;
  discount_type?: PromotionDiscountType;
  value?: number;
  scope?: PromotionScope;
  starts_at?: string;
  ends_at?: string;
  min_purchase?: number | null;
  max_discount?: number | null;
  scope_items?: string[];
  scope_categories?: string[];
  scope_brands?: string[];
  scope_active_ingredients?: string[];
}

export interface EligibleCartItem {
  drug_code: string;
  drug_cluster: string | null;
  drug_brand: string | null;
  active_ingredient: string | null;
  quantity: number;
  unit_price: number;
}

export interface EligiblePromotionsRequest {
  items: EligibleCartItem[];
  subtotal: number;
}

export interface EligiblePromotion {
  id: number;
  name: string;
  description: string | null;
  discount_type: PromotionDiscountType;
  value: number;
  scope: PromotionScope;
  min_purchase: number | null;
  max_discount: number | null;
  ends_at: string;
  preview_discount: number;
}

export interface EligiblePromotionsResponse {
  promotions: EligiblePromotion[];
}

export interface PreviewMatchesRequest {
  scope: PromotionScope;
  values: string[];
}

export interface PreviewMatchesResponse {
  scope: PromotionScope;
  values: string[];
  matched_sku_count: number;
}
