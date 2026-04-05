-- Migration: 022 – Chart annotations / notes
-- Layer: application

CREATE TABLE IF NOT EXISTS public.annotations (
    id SERIAL PRIMARY KEY,
    tenant_id INT NOT NULL,
    user_id TEXT NOT NULL,
    chart_id TEXT NOT NULL,
    data_point TEXT NOT NULL,
    note TEXT NOT NULL,
    color TEXT NOT NULL DEFAULT '#D97706',
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.annotations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.annotations FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_annotations ON public.annotations;
CREATE POLICY tenant_isolation_annotations ON public.annotations
    FOR ALL
    USING (tenant_id::text = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));

CREATE INDEX IF NOT EXISTS idx_annotations_chart ON public.annotations(tenant_id, chart_id);
