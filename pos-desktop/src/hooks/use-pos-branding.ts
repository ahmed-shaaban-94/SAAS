"use client";

/**
 * usePosBranding — dynamic POS letterhead from the tenant_branding API.
 *
 * Replaces the static `getPosBranding()` helper that read NEXT_PUBLIC_POS_*
 * env vars baked in at build time.  In multi-tenant mode each tenant has its
 * own row in `public.tenant_branding`; this hook fetches the authenticated
 * tenant's row and maps the pos_* columns to the PosBranding shape.
 *
 * The shape intentionally matches `PosBranding` from `@/lib/pos-branding` so
 * that call-sites can switch from the static helper to this hook with minimal
 * changes.
 *
 * Loading / error behaviour:
 *   - While loading: returns safe placeholder strings (empty or generic label)
 *     so components never render `undefined` inside JSX.
 *   - On error: same safe defaults; POS remains fully functional.
 */

import { useBranding } from "@shared/hooks/use-branding";

export interface PosBranding {
  /** Pharmacy / branch display name on stocktaking sheets and receipts. */
  branchName: string;
  /** Short label for the invoice header; falls back to branchName. */
  invoiceLabel: string;
  /** Street address printed under the branch name. */
  branchAddress: string;
  /** VAT / tax-registration number shown on tax invoices. */
  taxNumber: string;
  /** Commercial-registration (CR) number shown on stocktaking worksheets. */
  crNumber: string;
  /** Resolved company name — used on receipts where tenant name is shown. */
  companyName: string;
}

const FALLBACK: PosBranding = {
  branchName: "",
  invoiceLabel: "",
  branchAddress: "",
  taxNumber: "",
  crNumber: "",
  companyName: "Pharmacy",
};

export function usePosBranding(): {
  branding: PosBranding;
  isLoading: boolean;
} {
  const { data, isLoading } = useBranding();

  if (!data) {
    return { branding: FALLBACK, isLoading };
  }

  const branchName = data.pos_branch_name ?? data.company_name ?? FALLBACK.branchName;

  return {
    isLoading,
    branding: {
      branchName,
      invoiceLabel: data.pos_invoice_label ?? branchName,
      branchAddress: data.pos_branch_address ?? FALLBACK.branchAddress,
      taxNumber: data.pos_tax_number ?? FALLBACK.taxNumber,
      crNumber: data.pos_cr_number ?? FALLBACK.crNumber,
      companyName: data.company_name ?? FALLBACK.companyName,
    },
  };
}
