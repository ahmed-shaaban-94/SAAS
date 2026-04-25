-- Migration 117: upgrade pharmacist PIN hash to scrypt format
-- Adds pin_salt and pin_hash_algo columns to tenant_members.
-- Existing hashes (SHA-256, no salt) are marked 'legacy'; they will be
-- auto-upgraded to scrypt on each user's next successful login (zero-downtime).

BEGIN;

ALTER TABLE public.tenant_members
    ADD COLUMN IF NOT EXISTS pharmacist_pin_salt      TEXT,
    ADD COLUMN IF NOT EXISTS pharmacist_pin_hash_algo TEXT DEFAULT 'legacy';

-- Mark rows that already have a hash as 'legacy' so the verifier knows to
-- fall back to SHA-256 comparison and then upgrade on first successful login.
UPDATE public.tenant_members
SET    pharmacist_pin_hash_algo = 'legacy'
WHERE  pharmacist_pin_hash IS NOT NULL
  AND  pharmacist_pin_hash_algo IS NULL;

COMMENT ON COLUMN public.tenant_members.pharmacist_pin_salt IS
    'base64-encoded 32-byte random salt used by scrypt; NULL for legacy SHA-256 rows';

COMMENT ON COLUMN public.tenant_members.pharmacist_pin_hash_algo IS
    'scrypt | legacy — legacy rows require a PIN-reset/re-hash on next login';

COMMIT;
