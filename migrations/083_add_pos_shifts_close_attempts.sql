-- Migration: 083 — POS shifts close attempts forensic log
-- Layer: POS operational
-- Idempotent.
--
-- Forensic log of every POST /pos/shifts/{id}/close attempt (accepted or
-- rejected). Used to investigate anomalies and prove that the server-side
-- shift-close guard (§3.6) was correctly enforced. Retained indefinitely.

CREATE TABLE IF NOT EXISTS pos.shifts_close_attempts (
    id                          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    shift_id                    BIGINT NOT NULL REFERENCES pos.shift_records(id),
    tenant_id                   INT NOT NULL,
    terminal_id                 BIGINT NOT NULL REFERENCES pos.terminal_sessions(id),
    attempted_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    outcome                     TEXT NOT NULL
                                CHECK (outcome IN ('accepted','rejected_client','rejected_server')),
    claimed_unresolved_count    INT,
    claimed_unresolved_digest   TEXT,
    server_incomplete_count     INT,
    rejection_reason            TEXT
);

CREATE INDEX IF NOT EXISTS idx_pos_close_attempts_shift
    ON pos.shifts_close_attempts (shift_id, attempted_at DESC);

ALTER TABLE pos.shifts_close_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.shifts_close_attempts FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.shifts_close_attempts
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.shifts_close_attempts
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT ON TABLE pos.shifts_close_attempts TO datapulse;
GRANT SELECT ON TABLE pos.shifts_close_attempts TO datapulse_reader;

COMMENT ON TABLE pos.shifts_close_attempts IS
  'Forensic log of every POST /pos/shifts/{id}/close attempt. Retained indefinitely.';
