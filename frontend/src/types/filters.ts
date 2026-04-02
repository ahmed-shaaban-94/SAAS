export interface FilterParams {
  start_date?: string; // "YYYY-MM-DD"
  end_date?: string; // "YYYY-MM-DD"
  target_date?: string; // "YYYY-MM-DD" — used by /summary endpoint
  category?: string;
  brand?: string;
  site_key?: number;
  staff_key?: number;
  limit?: number;
  entity_type?: string; // "product" | "customer" | "staff" — used by /top-movers
  // Index signature for extra API params (year, granularity, entity, etc.)
  [key: string]: string | number | boolean | undefined;
}

export interface FilterOption {
  key: number;
  label: string;
}

export interface FilterOptions {
  categories: string[];
  brands: string[];
  sites: FilterOption[];
  staff: FilterOption[];
}
