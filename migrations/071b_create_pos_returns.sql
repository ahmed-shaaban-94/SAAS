-- Migration: 071b — Create `pos.returns` table
-- Layer: POS operational
-- Idempotent. (H4 fix: added after adversarial review)

CREATE TABLE IF NOT EXISTS pos.returns (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id               INT NOT NULL,
    original_transaction_id BIGINT NOT NULL REFERENCES pos.transactions(id),
    return_transaction_id   BIGINT REFERENCES pos.transactions(id),
    staff_id                TEXT NOT NULL,
    reason                  TEXT NOT NULL
                            CHECK (reason IN ('defective', 'wrong_drug', 'expired', 'customer_request')),
    refund_amount           NUMERIC(18,4) NOT NULL,
    refund_method           TEXT NOT NULL CHECK (refund_method IN ('cash', 'credit_note')),
    notes                   TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    loaded_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pos_returns_original_txn
    ON pos.returns (original_transaction_id);
CREATE INDEX IF NOT EXISTS idx_pos_returns_tenant_date
    ON pos.returns (tenant_id, created_at DESC);

ALTER TABLE pos.returns ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.returns FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.returns
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.returns
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT ON TABLE pos.returns TO datapulse;
GRANT SELECT ON TABLE pos.returns TO datapulse_reader;

COMMENT ON TABLE pos.returns IS
    'Drug return records linked to original and (optional) return transactions. refund_method: cash or credit_note. RLS-protected.';
