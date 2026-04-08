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
