-- Migration: 081 — POS grants issued registry
-- Layer: POS operational
-- Idempotent.
--
-- Authoritative server-side record of every offline grant issued. The
-- override_token_verifier uses this table to validate that a claimed
-- code_id was legitimately minted in a particular grant (§8.8.6).

CREATE TABLE IF NOT EXISTS pos.grants_issued (
    grant_id            TEXT PRIMARY KEY,
    tenant_id           INT NOT NULL,
    terminal_id         BIGINT NOT NULL REFERENCES pos.terminal_sessions(id),
    shift_id            BIGINT NOT NULL REFERENCES pos.shift_records(id),
    staff_id            TEXT NOT NULL,
    key_id              TEXT NOT NULL REFERENCES pos.tenant_keys(key_id),
    code_ids            JSONB NOT NULL,
    issued_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    offline_expires_at  TIMESTAMPTZ NOT NULL,
    revoked_at          TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_pos_grants_terminal
    ON pos.grants_issued (terminal_id, issued_at DESC);

ALTER TABLE pos.grants_issued ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.grants_issued FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.grants_issued
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.grants_issued
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT, UPDATE ON TABLE pos.grants_issued TO datapulse;
GRANT SELECT ON TABLE pos.grants_issued TO datapulse_reader;

COMMENT ON TABLE pos.grants_issued IS
  'Authoritative registry of issued offline grants + their code_id sets. Consumed by override_token_verifier.';
