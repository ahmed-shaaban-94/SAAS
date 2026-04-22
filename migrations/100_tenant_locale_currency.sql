-- 100: Add locale + currency to bronze.tenants for Egypt PMF (#604 Spec 1)
-- Idempotent: ADD COLUMN IF NOT EXISTS makes re-apply a no-op.

ALTER TABLE bronze.tenants
    ADD COLUMN IF NOT EXISTS locale   VARCHAR(10) NOT NULL DEFAULT 'en-US',
    ADD COLUMN IF NOT EXISTS currency CHAR(3)     NOT NULL DEFAULT 'USD';

COMMENT ON COLUMN bronze.tenants.locale IS
    'BCP-47 tag; controls next-intl locale + RTL direction. Set from Auth0 '
    'claim on signup (#604).';

COMMENT ON COLUMN bronze.tenants.currency IS
    'ISO-4217; routes BillingService to the right PaymentProvider. '
    'USD=Stripe, EGP=Paymob (post Spec 2) (#604).';
