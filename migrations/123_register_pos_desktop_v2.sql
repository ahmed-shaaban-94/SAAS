-- Migration: 123 - Register POS desktop v2.0.0 in the staged-rollout table
-- Layer: POS operational / release management
-- Idempotent.
--
-- Activates the v2.0.0 desktop installer (built by tag pos-desktop-v2.0.0)
-- for all tenants on the stable channel / win32 platform. Without this row
-- the auto-updater's GET /api/v1/pos/updates/policy returns
-- {update_available: false} and cashier desktops never pull the new build.
--
-- Inserts:
--   • A single row in pos.desktop_update_releases for v2.0.0 with
--     rollout_scope='all' (every tenant on stable/win32 is eligible).
--   • No tenant rows in pos.desktop_update_release_targets — required only
--     when rollout_scope='selected'.
--
-- Idempotent: ON CONFLICT (version, channel, platform) DO UPDATE refreshes
-- active + release_notes if rerun, so repeated apply won't fail.

INSERT INTO pos.desktop_update_releases
    (version, channel, platform, rollout_scope, active, release_notes)
VALUES (
    '2.0.0',
    'stable',
    'win32',
    'all',
    true,
    'POS Desktop v2.0.0 — Gemini visual port + checkout robustness.'
    || E'\n\n'
    || 'Visual: macro-vibe upgrade (gradient halos, OrderTabs, ClinicalPanel '
    || 'gradient header, ChargeButton tactile lift); receipt visual uplift; '
    || 'micro-polish (wordmark, scan flash, voucher halo).'
    || E'\n\n'
    || 'Checkout / robustness: bulk-sync cart items to backend draft txn at '
    || 'Charge time (fixes "Transaction N has no items to check out"); auth '
    || 'idempotency + receipts hardening; addItem Idempotency-Key + drug_code '
    || 'string coercion.'
    || E'\n\n'
    || 'Refs: PRs #795, #796, #797, #798, #799, #800, #801. '
    || 'Tag pos-desktop-v2.0.0.'
)
ON CONFLICT (version, channel, platform) DO UPDATE
SET active        = EXCLUDED.active,
    rollout_scope = EXCLUDED.rollout_scope,
    release_notes = EXCLUDED.release_notes,
    updated_at    = now();

-- Optional: pause any prior v1.0.x rows so the policy resolver doesn't
-- accidentally suggest a downgrade. Idempotent — UPDATE on no rows is a no-op.
UPDATE pos.desktop_update_releases
SET active = false,
    updated_at = now()
WHERE channel = 'stable'
  AND platform = 'win32'
  AND version LIKE '1.%'
  AND active = true;
