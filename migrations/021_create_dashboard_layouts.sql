-- Migration: 021 – Customizable dashboard layouts
-- Layer: application

CREATE TABLE IF NOT EXISTS public.dashboard_layouts (
    id SERIAL PRIMARY KEY,
    tenant_id INT NOT NULL,
    user_id TEXT NOT NULL,
    layout JSONB NOT NULL DEFAULT '[]',
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id, user_id)
);

ALTER TABLE public.dashboard_layouts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dashboard_layouts FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_dashboard_layouts ON public.dashboard_layouts;
CREATE POLICY tenant_isolation_dashboard_layouts ON public.dashboard_layouts
    FOR ALL
    USING (tenant_id::text = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));
