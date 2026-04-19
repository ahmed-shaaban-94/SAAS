-- Migration: 089 — POS vouchers (discount code engine)
-- Layer: POS operational (phase 1 of the discount system)
-- Idempotent.
--
-- Redeemable discount codes. Phase 1 of the discount system; Phase 2 will add
-- pos.promotions for automatic seasonal campaigns. Vouchers are tenant-scoped
-- and must be atomically redeemed via SELECT ... FOR UPDATE from
-- datapulse.pos.voucher_repository.VoucherRepository.lock_and_redeem().

CREATE TABLE IF NOT EXISTS pos.vouchers (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       INTEGER NOT NULL REFERENCES bronze.tenants(tenant_id),
    code            TEXT NOT NULL,
    discount_type   TEXT NOT NULL CHECK (discount_type IN ('amount', 'percent')),
    value           NUMERIC(18, 4) NOT NULL CHECK (value > 0),
    max_uses        INTEGER NOT NULL DEFAULT 1 CHECK (max_uses >= 1),
    uses            INTEGER NOT NULL DEFAULT 0 CHECK (uses >= 0),
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'redeemed', 'expired', 'void')),
    starts_at       TIMESTAMPTZ,
    ends_at         TIMESTAMPTZ,
    min_purchase    NUMERIC(18, 4),
    redeemed_txn_id BIGINT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, code)
);

CREATE INDEX IF NOT EXISTS idx_pos_vouchers_tenant_code
    ON pos.vouchers (tenant_id, code);

CREATE INDEX IF NOT EXISTS idx_pos_vouchers_status
    ON pos.vouchers (tenant_id, status)
    WHERE status = 'active';

ALTER TABLE pos.vouchers ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.vouchers FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.vouchers
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.vouchers
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE pos.vouchers TO datapulse;
GRANT SELECT ON TABLE pos.vouchers TO datapulse_reader;
GRANT USAGE ON SEQUENCE pos.vouchers_id_seq TO datapulse;

COMMENT ON TABLE pos.vouchers IS
    'Redeemable discount codes. Phase 1 of the discount system; Phase 2 adds '
    'pos.promotions for automatic seasonal campaigns.';
