/**
 * POS letterhead — pharmacy branding shown on invoices, receipts, and
 * stocktaking worksheets.
 *
 * PILOT-ERA: values come from `NEXT_PUBLIC_POS_*` env vars with empty
 * defaults. Setting them at build time is the pilot's single source of
 * truth so the branch name, address, and legal identifiers are no longer
 * hardcoded into page files.
 *
 * Upgrade path (multi-tenant): replace this with an SWR fetch from the
 * `tenant_branding` table (see migration 027). The call signature stays
 * the same — consumers only read `getPosBranding()`, so the swap is
 * contained to this module.
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
