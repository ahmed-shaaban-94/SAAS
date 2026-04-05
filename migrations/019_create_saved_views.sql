-- Migration: 019 – Saved views / bookmarks
-- Layer: application

CREATE TABLE IF NOT EXISTS public.saved_views (
    id SERIAL PRIMARY KEY,
    tenant_id INT NOT NULL,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    page_path TEXT NOT NULL DEFAULT '/dashboard',
    filters JSONB NOT NULL DEFAULT '{}',
    is_default BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id, user_id, name)
);

ALTER TABLE public.saved_views ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saved_views FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_saved_views ON public.saved_views;
CREATE POLICY tenant_isolation_saved_views ON public.saved_views
    FOR ALL
    USING (tenant_id::text = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));

CREATE INDEX IF NOT EXISTS idx_saved_views_tenant_user ON public.saved_views(tenant_id, user_id);
