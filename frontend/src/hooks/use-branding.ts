"use client";
import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";

export interface BrandingConfig {
  tenant_id: number;
  company_name: string;
  logo_url: string | null;
  favicon_url: string | null;
  primary_color: string;
  accent_color: string;
  sidebar_bg: string | null;
  font_family: string;
  custom_domain: string | null;
  subdomain: string | null;
  email_from_name: string | null;
  footer_text: string | null;
  support_email: string | null;
  support_url: string | null;
  hide_datapulse_branding: boolean;
  custom_login_bg: string | null;
  // POS letterhead fields (migration 116)
  pos_branch_name: string | null;
  pos_branch_address: string | null;
  pos_tax_number: string | null;
  pos_cr_number: string | null;
  pos_invoice_label: string | null;
}

export function useBranding() {
  const { data, error, isLoading, mutate } = useSWR<BrandingConfig>(
    "/api/v1/branding/",
    () => fetchAPI<BrandingConfig>("/api/v1/branding/"),
    {
      revalidateOnFocus: false,
      dedupingInterval: 60_000,
    },
  );
  return { data, error, isLoading, mutate };
}
