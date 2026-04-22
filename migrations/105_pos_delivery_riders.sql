-- Migration: 105 — POS delivery dispatch + rider routing
-- Layer: POS operational.
-- Idempotent.
--
-- Adds:
--   1. pos.riders        — rider registry (name, phone, status, terminal assignment)
--   2. pos.deliveries    — delivery orders linked to transactions
--   3. delivery_fee col  — NUMERIC(18,4) on pos.transactions (default 0)
--
-- Designed for Phase C of POS v9 (issue #628).
-- ETA calculation is intentionally simple for v1: stored at creation time by
-- the service layer using a static offset. A future migration can add
-- geospatial columns and a routing-engine integration.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. pos.riders
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS pos.riders (
    id                  BIGSERIAL PRIMARY KEY,
    tenant_id           INT         NOT NULL,
    name                TEXT        NOT NULL,
    phone               TEXT        NOT NULL,
    status              TEXT        NOT NULL DEFAULT 'available'
                            CHECK (status IN ('available', 'busy', 'offline')),
    current_terminal_id BIGINT      REFERENCES pos.terminal_sessions(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, phone)
);

CREATE INDEX IF NOT EXISTS idx_pos_riders_tenant_status
    ON pos.riders (tenant_id, status);

ALTER TABLE pos.riders ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.riders FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.riders
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.riders
        FOR SELECT TO datapulse_reader
        USING (current_setting('app.tenant_id', true)::int = tenant_id);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE pos.riders TO datapulse;
GRANT SELECT                           ON TABLE pos.riders TO datapulse_reader;
GRANT USAGE, SELECT ON SEQUENCE pos.riders_id_seq TO datapulse;

COMMENT ON TABLE pos.riders IS
    'Delivery riders registered per tenant. Phone is the primary contact; '
    'status tracks availability for dispatch. Added in migration 105.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. delivery_fee column on pos.transactions
-- ─────────────────────────────────────────────────────────────────────────────

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM information_schema.columns
         WHERE table_schema = 'pos'
           AND table_name   = 'transactions'
           AND column_name  = 'delivery_fee'
    ) THEN
        ALTER TABLE pos.transactions
            ADD COLUMN delivery_fee NUMERIC(18,4) NOT NULL DEFAULT 0;
    END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. pos.deliveries
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS pos.deliveries (
    id              BIGSERIAL   PRIMARY KEY,
    tenant_id       INT         NOT NULL,
    transaction_id  BIGINT      NOT NULL REFERENCES pos.transactions(id) ON DELETE CASCADE,
    address         TEXT        NOT NULL,
    landmark        TEXT,
    channel         TEXT        NOT NULL DEFAULT 'phone'
                        CHECK (channel IN ('in_store', 'phone', 'app')),
    assigned_rider_id BIGINT    REFERENCES pos.riders(id) ON DELETE SET NULL,
    delivery_fee    NUMERIC(18,4) NOT NULL DEFAULT 0,
    eta_minutes     INT,
    status          TEXT        NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'dispatched', 'delivered', 'failed')),
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (transaction_id)
);

CREATE INDEX IF NOT EXISTS idx_pos_deliveries_tenant_status
    ON pos.deliveries (tenant_id, status);

CREATE INDEX IF NOT EXISTS idx_pos_deliveries_rider
    ON pos.deliveries (assigned_rider_id)
    WHERE assigned_rider_id IS NOT NULL;

ALTER TABLE pos.deliveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.deliveries FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.deliveries
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.deliveries
        FOR SELECT TO datapulse_reader
        USING (current_setting('app.tenant_id', true)::int = tenant_id);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE pos.deliveries TO datapulse;
GRANT SELECT                           ON TABLE pos.deliveries TO datapulse_reader;
GRANT USAGE, SELECT ON SEQUENCE pos.deliveries_id_seq TO datapulse;

COMMENT ON TABLE pos.deliveries IS
    'Delivery orders created from completed POS transactions. Each transaction '
    'may have at most one delivery record (UNIQUE constraint on transaction_id). '
    'Rider phone is stored on pos.riders and never duplicated here. '
    'Added in migration 105.';
