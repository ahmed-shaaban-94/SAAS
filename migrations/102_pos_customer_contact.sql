-- Migration: 102 — POS-owned customer contact (phone, #624 Phase D3)
-- Layer: POS operational
-- Idempotent.
--
-- Context
-- -------
-- `public_marts.dim_customer` is dbt-materialized (SCD Type 1) from
-- `stg_sales`; adding a column to it would be wiped on every dbt rebuild.
-- POS needs a mutable per-customer phone so the cashier can look a customer
-- up by typing a mobile number, so we keep that metadata here in a POS-owned
-- sidecar keyed by (tenant_id, customer_key) and LEFT JOIN it into the
-- dim_customer read path.
--
-- Why E.164 canonical
-- -------------------
-- Egyptian mobile numbers come in three wire formats (`01XXXXXXXXX`,
-- `201XXXXXXXXX`, `+201XXXXXXXXX`). We normalise to E.164 (`+201XXXXXXXXX`)
-- on every write; the UNIQUE index below enforces "one customer per phone
-- per tenant" on the canonical form so two cashiers can't accidentally
-- create two rows for the same number in different formats.

CREATE TABLE IF NOT EXISTS pos.customer_contact (
    tenant_id    INT    NOT NULL,
    customer_key BIGINT NOT NULL,
    phone_e164   TEXT   NOT NULL,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, customer_key),
    CONSTRAINT ck_pos_customer_contact_phone_e164
        CHECK (phone_e164 ~ '^\+20[0-9]{10}$')
);

-- One customer per phone per tenant — cross-tenant collisions are allowed
-- because phones aren't globally unique.
CREATE UNIQUE INDEX IF NOT EXISTS uq_pos_customer_contact_phone
    ON pos.customer_contact (tenant_id, phone_e164);

-- Btree on phone alone for the by-phone lookup hot path (the terminal hits
-- this endpoint on every customer search; needs to stay <150ms p95).
CREATE INDEX IF NOT EXISTS idx_pos_customer_contact_phone
    ON pos.customer_contact (phone_e164);

ALTER TABLE pos.customer_contact ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.customer_contact FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.customer_contact
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.customer_contact
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE pos.customer_contact TO datapulse;
GRANT SELECT ON TABLE pos.customer_contact TO datapulse_reader;

COMMENT ON TABLE pos.customer_contact IS
    'POS-owned per-customer contact metadata (phone, E.164-normalised). Keyed by dim_customer.customer_key. RLS-scoped per tenant. (#624)';
COMMENT ON COLUMN pos.customer_contact.phone_e164 IS
    'Egyptian mobile in E.164 canonical form (+201XXXXXXXXX). Normaliser in datapulse.pos.phone.normalize_egyptian_phone — CHECK constraint enforces the shape at the DB boundary. (#624)';
