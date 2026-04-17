-- Migration: 075 — Add `platform` subscription plan tier + schema comment
-- Layer: Billing / POS
-- Idempotent.
-- Context: The `platform` tier is the Pro→POS upsell path ($49→$99/mo).
--          `enterprise` already has pos_integration=True (no change needed).
--          This migration seeds billing plan metadata and documents the tier.

-- Seed the platform plan into subscription_plans if the table exists.
-- (Table may not exist in all environments; skip gracefully.)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name   = 'subscription_plans'
    ) THEN
        INSERT INTO public.subscription_plans
            (plan_key, display_name, monthly_price_usd, pos_integration, description)
        VALUES
            ('platform', 'Platform', 99.00, true,
             'Analytics + POS + Inventory for pharmaceutical operations. Upsell from Pro.')
        ON CONFLICT (plan_key) DO UPDATE
            SET pos_integration = true,
                description     = EXCLUDED.description;

        RAISE NOTICE 'platform plan seeded/updated in subscription_plans';
    ELSE
        RAISE NOTICE 'subscription_plans table not found — skipping plan seed (handled in application code)';
    END IF;
END $$;

-- Document the POS schema with an authoritative comment.
COMMENT ON SCHEMA pos IS
    'Point-of-Sale operational tables for the pharmaceutical POS module. '
    'All tables are tenant-scoped with RLS enabled and FORCE ROW LEVEL SECURITY. '
    'Financial values use NUMERIC(18,4). '
    'Available on platform ($99/mo) and enterprise tiers (pos_integration=true).';
