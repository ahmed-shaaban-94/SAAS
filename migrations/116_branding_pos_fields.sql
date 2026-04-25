-- ============================================================
-- Migration 116 — POS letterhead fields on tenant_branding
--
-- Adds POS-specific branding columns needed to display the
-- pharmacy name, address, and legal IDs on invoices, receipts,
-- and stocktaking worksheets. These replace the NEXT_PUBLIC_POS_*
-- env-var approach used in the pilot era.
-- ============================================================

ALTER TABLE public.tenant_branding
    ADD COLUMN IF NOT EXISTS pos_branch_name     TEXT,
    ADD COLUMN IF NOT EXISTS pos_branch_address  TEXT,
    ADD COLUMN IF NOT EXISTS pos_tax_number      TEXT,
    ADD COLUMN IF NOT EXISTS pos_cr_number       TEXT,
    ADD COLUMN IF NOT EXISTS pos_invoice_label   TEXT;

COMMENT ON COLUMN public.tenant_branding.pos_branch_name    IS 'Pharmacy / branch display name on stocktaking sheets and POS receipts.';
COMMENT ON COLUMN public.tenant_branding.pos_branch_address IS 'Street address printed under the branch name on invoices.';
COMMENT ON COLUMN public.tenant_branding.pos_tax_number     IS 'VAT / tax-registration number shown on simplified tax invoices.';
COMMENT ON COLUMN public.tenant_branding.pos_cr_number      IS 'Commercial-registration (CR) number shown on stocktaking worksheets.';
COMMENT ON COLUMN public.tenant_branding.pos_invoice_label  IS 'Short label for the invoice header; falls back to pos_branch_name when NULL.';
