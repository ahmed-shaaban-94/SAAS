/**
 * POS letterhead — static fallback via NEXT_PUBLIC_POS_* env vars.
 *
 * @deprecated Since issue #680 the POS pages fetch branding dynamically from
 * the `tenant_branding` API via `usePosBranding` (hooks/use-pos-branding.ts).
 * This module is kept for backwards compatibility with Electron packaging
 * scripts that still read env vars at build time; it is no longer called by
 * any page component.
 *
 * Do NOT add new callers. Use `usePosBranding` instead.
 */

export interface PosBranding {
  /** Branch/pharmacy display name on stocktaking sheets and general surfaces. */
  branchName: string;
  /** Shorter invoice-specific label; falls back to `branchName`. */
  invoiceLabel: string;
  /** Street address printed under the branch name. */
  branchAddress: string;
  /** Tax (VAT) registration number — shown on tax invoices. */
  taxNumber: string;
  /** Commercial registration (CR) number — shown on stocktaking worksheets. */
  crNumber: string;
}

/** @deprecated Use `usePosBranding` hook instead (see hooks/use-pos-branding.ts). */
export function getPosBranding(): PosBranding {
  const branchName = process.env.NEXT_PUBLIC_POS_BRANCH_NAME ?? "Pharmacy Branch";
  return {
    branchName,
    invoiceLabel: process.env.NEXT_PUBLIC_POS_INVOICE_LABEL ?? branchName,
    branchAddress: process.env.NEXT_PUBLIC_POS_BRANCH_ADDRESS ?? "",
    taxNumber: process.env.NEXT_PUBLIC_POS_TAX_NUMBER ?? "",
    crNumber: process.env.NEXT_PUBLIC_POS_CR_NUMBER ?? "",
  };
}
