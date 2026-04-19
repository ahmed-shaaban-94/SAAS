-- Migration: 091 — POS promotions (admin-managed seasonal discount campaigns)
-- Layer: POS operational (phase 2 of the discount system)
-- Idempotent.
--
-- Admin-managed seasonal discount campaigns (e.g. "Ramadan 15% off
-- antibiotics"). Cashiers explicitly pick a promotion at checkout — there
-- is no auto-application. Eligibility scopes: all | items | category.
--
-- Lifecycle: promotions default to status='paused' on creation so admins
-- can preview before going live. Only 'active' promotions are returned by
-- the eligibility endpoint, and only when current time falls inside
-- [starts_at, ends_at].
--
-- Atomicity: an application row is inserted inside the same transaction as
-- pos.transactions by datapulse.pos.commit.atomic_commit. One transaction
-- may carry at most one applied discount (voucher OR promotion, never both).

CREATE TABLE IF NOT EXISTS pos.promotions (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       INTEGER NOT NULL REFERENCES bronze.tenants(tenant_id),
    name            TEXT NOT NULL,
    description     TEXT,
    discount_type   TEXT NOT NULL CHECK (discount_type IN ('amount', 'percent')),
    value           NUMERIC(18, 4) NOT NULL CHECK (value > 0),
    scope           TEXT NOT NULL CHECK (scope IN ('all', 'items', 'category')),
    starts_at       TIMESTAMPTZ NOT NULL,
    ends_at         TIMESTAMPTZ NOT NULL,
    min_purchase    NUMERIC(18, 4),
    max_discount    NUMERIC(18, 4),
    status          TEXT NOT NULL DEFAULT 'paused'
                    CHECK (status IN ('active', 'paused', 'expired')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (ends_at > starts_at),
    UNIQUE (tenant_id, name)
);

CREATE INDEX IF NOT EXISTS idx_pos_promotions_tenant_status
    ON pos.promotions (tenant_id, status)
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_pos_promotions_tenant_window
    ON pos.promotions (tenant_id, starts_at, ends_at);

-- Scope-specific joins: a promotion may point at a list of drug codes
-- (scope='items') or a list of drug clusters (scope='category'). For
-- scope='all' neither table has rows for the promotion.

CREATE TABLE IF NOT EXISTS pos.promotion_items (
    promotion_id    BIGINT NOT NULL REFERENCES pos.promotions(id) ON DELETE CASCADE,
    drug_code       TEXT NOT NULL,
    PRIMARY KEY (promotion_id, drug_code)
);

CREATE INDEX IF NOT EXISTS idx_pos_promotion_items_drug
    ON pos.promotion_items (drug_code);

CREATE TABLE IF NOT EXISTS pos.promotion_categories (
    promotion_id    BIGINT NOT NULL REFERENCES pos.promotions(id) ON DELETE CASCADE,
    drug_cluster    TEXT NOT NULL,
    PRIMARY KEY (promotion_id, drug_cluster)
);

CREATE INDEX IF NOT EXISTS idx_pos_promotion_categories_cluster
    ON pos.promotion_categories (drug_cluster);

-- Audit log of actual applications. Inserted atomically with the owning
-- pos.transactions row so we can reconcile usage counts without scanning
-- all transactions.

CREATE TABLE IF NOT EXISTS pos.promotion_applications (
    id                  BIGSERIAL PRIMARY KEY,
    tenant_id           INTEGER NOT NULL REFERENCES bronze.tenants(tenant_id),
    promotion_id        BIGINT NOT NULL REFERENCES pos.promotions(id),
    transaction_id      BIGINT NOT NULL,
    cashier_staff_id    TEXT NOT NULL,
    discount_applied    NUMERIC(18, 4) NOT NULL CHECK (discount_applied >= 0),
    applied_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pos_promotion_applications_promo
    ON pos.promotion_applications (promotion_id, applied_at DESC);

CREATE INDEX IF NOT EXISTS idx_pos_promotion_applications_tenant
    ON pos.promotion_applications (tenant_id, applied_at DESC);

-- One application per (promotion, transaction) — doubles as an idempotency
-- guard if atomic_commit is retried after a partial failure.
CREATE UNIQUE INDEX IF NOT EXISTS uq_pos_promotion_applications_txn
    ON pos.promotion_applications (promotion_id, transaction_id);

-- ── RLS ──────────────────────────────────────────────────────────────────

ALTER TABLE pos.promotions              ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.promotions              FORCE  ROW LEVEL SECURITY;
ALTER TABLE pos.promotion_applications  ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.promotion_applications  FORCE  ROW LEVEL SECURITY;

-- promotion_items / promotion_categories do not carry tenant_id — they are
-- child rows of promotions and inherit tenant scope via the FK + RLS on
-- pos.promotions. Enabling RLS with a permissive policy keeps grants
-- consistent with the rest of the schema.
ALTER TABLE pos.promotion_items         ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.promotion_items         FORCE  ROW LEVEL SECURITY;
ALTER TABLE pos.promotion_categories    ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.promotion_categories    FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.promotions
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.promotions
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.promotion_applications
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.promotion_applications
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.promotion_items
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.promotion_items
        FOR SELECT TO datapulse_reader USING (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.promotion_categories
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.promotion_categories
        FOR SELECT TO datapulse_reader USING (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ── Grants ───────────────────────────────────────────────────────────────

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE pos.promotions              TO datapulse;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE pos.promotion_items         TO datapulse;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE pos.promotion_categories    TO datapulse;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE pos.promotion_applications  TO datapulse;
GRANT SELECT ON TABLE pos.promotions              TO datapulse_reader;
GRANT SELECT ON TABLE pos.promotion_items         TO datapulse_reader;
GRANT SELECT ON TABLE pos.promotion_categories    TO datapulse_reader;
GRANT SELECT ON TABLE pos.promotion_applications  TO datapulse_reader;
GRANT USAGE ON SEQUENCE pos.promotions_id_seq              TO datapulse;
GRANT USAGE ON SEQUENCE pos.promotion_applications_id_seq  TO datapulse;

COMMENT ON TABLE pos.promotions IS
    'Admin-managed seasonal discount campaigns. Cashier explicitly picks '
    'an eligible promotion at checkout (never auto-applied). Phase 2 of '
    'the POS discount system.';
COMMENT ON TABLE pos.promotion_applications IS
    'Audit of promotions applied at checkout. Inserted atomically with '
    'pos.transactions by datapulse.pos.commit.atomic_commit.';
