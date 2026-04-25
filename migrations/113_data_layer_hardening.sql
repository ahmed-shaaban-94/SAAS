-- Migration: 113 — data layer hardening
-- Layer: cross-cutting (pharma, insurance, rx, webhooks)
-- Idempotent.
--
-- Fixes from data-layer review (2026-04-25):
--   1. Missing GRANT SELECT to datapulse_reader on pharma/insurance/rx/webhooks
--      schemas (migrations 107-111 only granted to datapulse_api).
--   2. Webhook RLS policies missing the `, true` fallback in current_setting()
--      (raises ERROR instead of returning NULL when GUC unset).
--   3. Trigram index on pharma.drug_master.name_en / name_ar (ILIKE on
--      a leading-% pattern triggers seq scan; pg_trgm available since #018).
--   4. NUMERIC(10,2) financial cols in insurance.claims/claim_items widened
--      to NUMERIC(18,4) per project hard rule (CLAUDE.md: financial = 18,4).
--   5. Index on insurance.claims.transaction_id and rx.dispense_events.transaction_id
--      (heavily filtered, currently unindexed).

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. GRANT datapulse_reader on tables created in 107-111
-- ─────────────────────────────────────────────────────────────────────────────

DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'datapulse_reader') THEN
        -- pharma (migration 107)
        GRANT SELECT ON TABLE pharma.drug_master      TO datapulse_reader;
        GRANT SELECT ON TABLE pharma.eda_exports      TO datapulse_reader;

        -- insurance (migration 108)
        GRANT SELECT ON TABLE insurance.insurance_companies TO datapulse_reader;
        GRANT SELECT ON TABLE insurance.insurance_plans     TO datapulse_reader;
        GRANT SELECT ON TABLE insurance.claims              TO datapulse_reader;
        GRANT SELECT ON TABLE insurance.claim_items         TO datapulse_reader;

        -- rx (migration 109)
        GRANT SELECT ON TABLE rx.prescriptions    TO datapulse_reader;
        GRANT SELECT ON TABLE rx.dispense_events  TO datapulse_reader;

        -- webhooks (migration 111)
        GRANT SELECT ON TABLE webhooks.subscriptions  TO datapulse_reader;
        GRANT SELECT ON TABLE webhooks.delivery_log   TO datapulse_reader;
    END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. Fix webhook RLS policies (add `, true` fallback)
-- ─────────────────────────────────────────────────────────────────────────────
-- Without `, true` second arg, current_setting() raises ERROR when the GUC
-- is not set (e.g., in admin sessions or background jobs that haven't yet
-- called open_tenant_session). The `, true` arg returns NULL instead, and
-- the `tenant_id = NULL` predicate evaluates to NULL (no rows), which is
-- the safe behavior under RLS.

DROP POLICY IF EXISTS tenant_isolation ON webhooks.subscriptions;
CREATE POLICY tenant_isolation ON webhooks.subscriptions
    USING (tenant_id = current_setting('app.tenant_id', true)::BIGINT);

DROP POLICY IF EXISTS tenant_isolation ON webhooks.delivery_log;
CREATE POLICY tenant_isolation ON webhooks.delivery_log
    USING (tenant_id = current_setting('app.tenant_id', true)::BIGINT);

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. Trigram indexes for fuzzy search on drug names
-- ─────────────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_drug_master_name_en_trgm -- migration-safety: ok
    ON pharma.drug_master USING GIN (name_en gin_trgm_ops);

-- name_ar may be NULL; partial index avoids indexing nulls
CREATE INDEX IF NOT EXISTS idx_drug_master_name_ar_trgm -- migration-safety: ok
    ON pharma.drug_master USING GIN (name_ar gin_trgm_ops)
    WHERE name_ar IS NOT NULL;

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. Widen NUMERIC(10,2) -> NUMERIC(18,4) on financial columns
-- ─────────────────────────────────────────────────────────────────────────────
-- Idempotent: only fires if precision is still 10. NUMERIC widening is a
-- non-rewrite operation (catalog-only change for precision increase).

DO $$ BEGIN
    -- pharma.drug_master.default_price_egp
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'pharma' AND table_name = 'drug_master'
          AND column_name = 'default_price_egp' AND numeric_precision = 10
    ) THEN
        ALTER TABLE pharma.drug_master
            ALTER COLUMN default_price_egp TYPE NUMERIC(18,4);
    END IF;

    -- insurance.claims.{total_egp, copay_egp, insurance_due_egp}
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'insurance' AND table_name = 'claims'
          AND column_name = 'total_egp' AND numeric_precision = 10
    ) THEN
        ALTER TABLE insurance.claims
            ALTER COLUMN total_egp        TYPE NUMERIC(18,4),
            ALTER COLUMN copay_egp        TYPE NUMERIC(18,4),
            ALTER COLUMN insurance_due_egp TYPE NUMERIC(18,4);
    END IF;

    -- insurance.claim_items.{unit_price, line_total}
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'insurance' AND table_name = 'claim_items'
          AND column_name = 'unit_price' AND numeric_precision = 10
    ) THEN
        ALTER TABLE insurance.claim_items
            ALTER COLUMN unit_price TYPE NUMERIC(18,4),
            ALTER COLUMN line_total TYPE NUMERIC(18,4);
    END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. Indexes on transaction_id (claims & dispense events)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_claims_transaction_id -- migration-safety: ok
    ON insurance.claims (transaction_id)
    WHERE transaction_id IS NOT NULL;

-- rx.dispense_events.transaction_id (only index if column exists; some
-- older deployments may not yet have migration 109 applied)
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'rx' AND table_name = 'dispense_events'
          AND column_name = 'transaction_id'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_dispense_events_transaction_id
            ON rx.dispense_events (transaction_id)
            WHERE transaction_id IS NOT NULL;
    END IF;
END $$;
