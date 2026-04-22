-- Migration: 108 — insurance schema, companies, plans, claims, and claim items
-- Layer: insurance (new schema)
-- Idempotent.
--
-- Creates:
--   1. insurance schema
--   2. insurance.insurance_companies — tenant-scoped insurer records
--   3. insurance.insurance_plans     — plan definitions per company
--   4. insurance.claims              — claim headers
--   5. insurance.claim_items         — line items per claim
--   RLS on all tables (tenant_id based)

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Schema
-- ─────────────────────────────────────────────────────────────────────────────

CREATE SCHEMA IF NOT EXISTS insurance;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. insurance.insurance_companies
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS insurance.insurance_companies (
    id             BIGSERIAL   PRIMARY KEY,
    tenant_id      BIGINT      NOT NULL,
    name           TEXT        NOT NULL,
    code           TEXT,
    contact_email  TEXT,
    is_active      BOOL        NOT NULL DEFAULT true,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_insurance_companies_tenant_id -- migration-safety: ok
    ON insurance.insurance_companies (tenant_id);

COMMENT ON TABLE insurance.insurance_companies IS
    'Insurance provider companies, scoped per tenant. Added in migration 108.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. insurance.insurance_plans
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS insurance.insurance_plans (
    id          BIGSERIAL       PRIMARY KEY,
    company_id  BIGINT          NOT NULL REFERENCES insurance.insurance_companies(id),
    name        TEXT,
    copay_pct   NUMERIC(5,2)    NOT NULL DEFAULT 0,
    plan_code   TEXT,
    is_active   BOOL            NOT NULL DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_insurance_plans_company_id -- migration-safety: ok
    ON insurance.insurance_plans (company_id);

COMMENT ON TABLE insurance.insurance_plans IS
    'Insurance plan definitions linked to a company. Added in migration 108.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. insurance.claims
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS insurance.claims (
    id               BIGSERIAL       PRIMARY KEY,
    tenant_id        BIGINT          NOT NULL,
    transaction_id   BIGINT,
    plan_id          BIGINT          REFERENCES insurance.insurance_plans(id),
    patient_name     TEXT,
    patient_id_no    TEXT,
    total_egp        NUMERIC(10,2),
    copay_egp        NUMERIC(10,2),
    insurance_due_egp NUMERIC(10,2),
    status           TEXT            NOT NULL DEFAULT 'draft'
                                     CHECK (status IN ('draft','submitted','approved','rejected','paid')),
    submitted_at     TIMESTAMPTZ,
    approved_at      TIMESTAMPTZ,
    created_at       TIMESTAMPTZ     NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_claims_tenant_id -- migration-safety: ok
    ON insurance.claims (tenant_id);

CREATE INDEX IF NOT EXISTS idx_claims_status -- migration-safety: ok
    ON insurance.claims (tenant_id, status);

COMMENT ON TABLE insurance.claims IS
    'Insurance claim headers. Status lifecycle: draft → submitted → approved/rejected → paid. '
    'Added in migration 108.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. insurance.claim_items
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS insurance.claim_items (
    id          BIGSERIAL       PRIMARY KEY,
    claim_id    BIGINT          NOT NULL REFERENCES insurance.claims(id) ON DELETE CASCADE,
    drug_code   TEXT,
    quantity    NUMERIC(10,3),
    unit_price  NUMERIC(10,2),
    line_total  NUMERIC(10,2)
);

CREATE INDEX IF NOT EXISTS idx_claim_items_claim_id -- migration-safety: ok
    ON insurance.claim_items (claim_id);

COMMENT ON TABLE insurance.claim_items IS
    'Line items for each insurance claim. Cascades on claim deletion. Added in migration 108.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. RLS (tenant_id based on all tables that carry it)
-- ─────────────────────────────────────────────────────────────────────────────

-- insurance.insurance_companies
ALTER TABLE insurance.insurance_companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE insurance.insurance_companies FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY tenant_isolation ON insurance.insurance_companies
        USING (tenant_id = current_setting('app.tenant_id', true)::bigint);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- insurance.insurance_plans (joined via company_id → tenant-scoped parent)
ALTER TABLE insurance.insurance_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE insurance.insurance_plans FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY tenant_isolation ON insurance.insurance_plans
        USING (
            EXISTS (
                SELECT 1
                  FROM insurance.insurance_companies c
                 WHERE c.id = company_id
                   AND c.tenant_id = current_setting('app.tenant_id', true)::bigint
            )
        );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- insurance.claims
ALTER TABLE insurance.claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE insurance.claims FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY tenant_isolation ON insurance.claims
        USING (tenant_id = current_setting('app.tenant_id', true)::bigint);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- insurance.claim_items (joined via claim_id → tenant-scoped parent)
ALTER TABLE insurance.claim_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE insurance.claim_items FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY tenant_isolation ON insurance.claim_items
        USING (
            EXISTS (
                SELECT 1
                  FROM insurance.claims cl
                 WHERE cl.id = claim_id
                   AND cl.tenant_id = current_setting('app.tenant_id', true)::bigint
            )
        );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. Grants (guarded — role may not exist in all environments)
-- ─────────────────────────────────────────────────────────────────────────────

DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'datapulse_api') THEN
        GRANT SELECT, INSERT, UPDATE ON TABLE insurance.insurance_companies       TO datapulse_api;
        GRANT SELECT, INSERT, UPDATE ON TABLE insurance.insurance_plans           TO datapulse_api;
        GRANT SELECT, INSERT, UPDATE ON TABLE insurance.claims                    TO datapulse_api;
        GRANT SELECT, INSERT, UPDATE ON TABLE insurance.claim_items               TO datapulse_api;
        GRANT USAGE, SELECT ON SEQUENCE insurance.insurance_companies_id_seq      TO datapulse_api;
        GRANT USAGE, SELECT ON SEQUENCE insurance.insurance_plans_id_seq          TO datapulse_api;
        GRANT USAGE, SELECT ON SEQUENCE insurance.claims_id_seq                   TO datapulse_api;
        GRANT USAGE, SELECT ON SEQUENCE insurance.claim_items_id_seq              TO datapulse_api;
    END IF;
END $$;
