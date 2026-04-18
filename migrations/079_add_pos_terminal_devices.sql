-- Migration: 079 — POS terminal device-bound credentials
-- Layer: POS operational
-- Idempotent.
--
-- Binds each POS terminal_id to a specific physical machine via an Ed25519
-- public key + device fingerprint. The server verifies every mutating POS
-- request's X-Terminal-Token against the registered public key. A unique
-- partial index enforces "at most one active (non-revoked) device per
-- terminal." See §8.9.

CREATE TABLE IF NOT EXISTS pos.terminal_devices (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id           INT NOT NULL,
    terminal_id         BIGINT NOT NULL REFERENCES pos.terminal_sessions(id),
    public_key          BYTEA NOT NULL,
    device_fingerprint  TEXT NOT NULL,
    registered_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at          TIMESTAMPTZ,
    last_seen_at        TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_pos_device_terminal_active
    ON pos.terminal_devices (terminal_id)
    WHERE revoked_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_pos_device_tenant
    ON pos.terminal_devices (tenant_id, revoked_at);

ALTER TABLE pos.terminal_devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.terminal_devices FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.terminal_devices
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.terminal_devices
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT, UPDATE ON TABLE pos.terminal_devices TO datapulse;
GRANT SELECT ON TABLE pos.terminal_devices TO datapulse_reader;

COMMENT ON TABLE pos.terminal_devices IS
  'Physical-device binding for POS terminals. Unique partial index enforces one active device per terminal.';
