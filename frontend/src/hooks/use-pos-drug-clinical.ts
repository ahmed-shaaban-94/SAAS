"use client";

import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";

export interface DrugDetail {
  drug_code: string;
  drug_name: string;
  drug_brand: string | null;
  drug_cluster: string | null;
  drug_category: string | null;
  unit_price: number;
  counseling_text: string | null;
  active_ingredient: string | null;
}

export interface CrossSellItem {
  drug_code: string;
  drug_name: string;
  reason: string;
  reason_tag: string;
  unit_price: number;
}

export interface AlternativeItem {
  drug_code: string;
  drug_name: string;
  unit_price: number;
  savings_egp: number;
}

export interface PosDrugClinical {
  detail: DrugDetail | null;
  crossSell: CrossSellItem[];
  alternatives: AlternativeItem[];
  isLoading: boolean;
  error: Error | null;
}

export function usePosDrugClinical(drugCode: string | null | undefined): PosDrugClinical {
  const base = drugCode ? `/api/v1/pos/drugs/${encodeURIComponent(drugCode)}` : null;

  const {
    data: detail,
    error: detailErr,
    isLoading: detailLoading,
  } = useSWR<DrugDetail>(
    base,
    (url: string) => fetchAPI<DrugDetail>(url),
    { revalidateOnFocus: false },
  );

  const {
    data: crossSell,
    error: crossSellErr,
    isLoading: crossSellLoading,
  } = useSWR<CrossSellItem[]>(
    base ? `${base}/cross-sell` : null,
    (url: string) => fetchAPI<CrossSellItem[]>(url),
    { revalidateOnFocus: false },
  );

  const {
    data: alternatives,
    error: altErr,
    isLoading: altLoading,
  } = useSWR<AlternativeItem[]>(
    base ? `${base}/alternatives` : null,
    (url: string) => fetchAPI<AlternativeItem[]>(url),
    { revalidateOnFocus: false },
  );

  return {
    detail: detail ?? null,
    crossSell: crossSell ?? [],
    alternatives: alternatives ?? [],
    isLoading: detailLoading || crossSellLoading || altLoading,
    error: (detailErr ?? crossSellErr ?? altErr) as Error | null,
  };
}
