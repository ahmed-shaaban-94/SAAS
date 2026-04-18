-- Migration: 080 — POS tenant Ed25519 signing keypairs
-- Layer: POS operational
-- Idempotent.
--
-- Ed25519 signing keypairs per tenant for offline grants (§8.8). The server
-- holds the only signing (private) key; clients verify with the matching
-- public key fetched from GET /pos/tenant-key. Rotated daily with a 7-day
-- overlap window for grant verification.
--
-- Private keys MUST be encrypted at rest via the server's KMS in production.
-- Dev environments may store raw bytes.

CREATE TABLE IF NOT EXISTS pos.tenant_keys (
    key_id        TEXT PRIMARY KEY,
    tenant_id     INT NOT NULL,
    private_key   BYTEA NOT NULL,
    public_key    BYTEA NOT NULL,
    valid_from    TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_until   TIMESTAMPTZ NOT NULL,
    revoked_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_pos_tkeys_tenant_active
    ON pos.tenant_keys (tenant_id, valid_until)
    WHERE revoked_at IS NULL;

ALTER TABLE pos.tenant_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.tenant_keys FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.tenant_keys
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.tenant_keys
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT, UPDATE ON TABLE pos.tenant_keys TO datapulse;
GRANT SELECT ON TABLE pos.tenant_keys TO datapulse_reader;

COMMENT ON TABLE pos.tenant_keys IS
  'Ed25519 signing keypairs per tenant. Rotated daily with 7-day overlap window. Private keys must be encrypted at rest via server KMS in production.';
