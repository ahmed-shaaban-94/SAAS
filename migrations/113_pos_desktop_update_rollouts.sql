-- Migration: 113 - POS desktop staged update rollouts
-- Layer: POS operational / release management
-- Idempotent.

CREATE TABLE IF NOT EXISTS pos.desktop_update_releases (
    release_id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    version            TEXT NOT NULL,
    channel            TEXT NOT NULL DEFAULT 'stable',
    platform           TEXT NOT NULL DEFAULT 'win32',
    rollout_scope      TEXT NOT NULL DEFAULT 'selected'
                       CHECK (rollout_scope IN ('all', 'selected', 'paused')),
    active             BOOLEAN NOT NULL DEFAULT true,
    release_notes      TEXT,
    min_schema_version INT,
    max_schema_version INT,
    min_app_version    TEXT,
    starts_at          TIMESTAMPTZ,
    ends_at            TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (version, channel, platform)
);

CREATE TABLE IF NOT EXISTS pos.desktop_update_release_targets (
    release_id BIGINT NOT NULL REFERENCES pos.desktop_update_releases(release_id)
               ON DELETE CASCADE,
    tenant_id  INT NOT NULL REFERENCES bronze.tenants(tenant_id)
               ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (release_id, tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_pos_desktop_update_releases_lookup
    ON pos.desktop_update_releases (channel, platform, active, rollout_scope);

CREATE INDEX IF NOT EXISTS idx_pos_desktop_update_targets_tenant
    ON pos.desktop_update_release_targets (tenant_id, release_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE pos.desktop_update_releases TO datapulse;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE pos.desktop_update_release_targets TO datapulse;
GRANT USAGE, SELECT ON SEQUENCE pos.desktop_update_releases_release_id_seq TO datapulse;

GRANT SELECT ON TABLE pos.desktop_update_releases TO datapulse_reader;
GRANT SELECT ON TABLE pos.desktop_update_release_targets TO datapulse_reader;

INSERT INTO public.permissions (permission_key, category, description)
VALUES
    ('pos:update:manage', 'pos', 'Manage staged POS desktop update rollouts')
ON CONFLICT (permission_key) DO NOTHING;

INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key IN ('owner', 'admin', 'pos_manager')
  AND p.permission_key = 'pos:update:manage'
ON CONFLICT DO NOTHING;

COMMENT ON TABLE pos.desktop_update_releases IS
    'Operator-managed POS desktop releases. rollout_scope=all updates every eligible tenant; selected updates only tenant targets; paused blocks rollout.';

COMMENT ON TABLE pos.desktop_update_release_targets IS
    'Tenant allow-list for selected POS desktop release rollouts.';
