-- Migration: 082 — POS override code consumption ledger
-- Layer: POS operational
-- Idempotent.
--
-- One-time-use ledger for supervisor override codes (§8.8.6). The PK
-- (grant_id, code_id) atomically enforces one-time use via primary-key
-- conflict — a second attempt to consume the same code returns 409.

CREATE TABLE IF NOT EXISTS pos.override_consumptions (
    grant_id                TEXT NOT NULL REFERENCES pos.grants_issued(grant_id),
    code_id                 TEXT NOT NULL,
    tenant_id               INT NOT NULL,
    terminal_id             BIGINT NOT NULL REFERENCES pos.terminal_sessions(id),
    shift_id                BIGINT NOT NULL REFERENCES pos.shift_records(id),
    action                  TEXT NOT NULL
                            CHECK (action IN ('retry_override','void','no_sale','price_override','discount_above_limit')),
    action_subject_id       TEXT,
    consumed_at             TIMESTAMPTZ NOT NULL,
    recorded_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    request_idempotency_key TEXT,
    PRIMARY KEY (grant_id, code_id)
);

CREATE INDEX IF NOT EXISTS idx_pos_overrides_terminal
    ON pos.override_consumptions (terminal_id, consumed_at);

ALTER TABLE pos.override_consumptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.override_consumptions FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.override_consumptions
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.override_consumptions
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT ON TABLE pos.override_consumptions TO datapulse;
GRANT SELECT ON TABLE pos.override_consumptions TO datapulse_reader;

COMMENT ON TABLE pos.override_consumptions IS
  'One-time-use ledger for supervisor override codes. PK (grant_id, code_id) enforces via PK conflict.';
