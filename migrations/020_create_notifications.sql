-- Migration: 020 – In-app notification center
-- Layer: application

CREATE TABLE IF NOT EXISTS public.notifications (
    id BIGSERIAL PRIMARY KEY,
    tenant_id INT NOT NULL,
    user_id TEXT,
    type TEXT NOT NULL CHECK (type IN ('urgent', 'info', 'success')),
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    link TEXT,
    read BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_notifications ON public.notifications;
CREATE POLICY tenant_isolation_notifications ON public.notifications
    FOR ALL
    USING (tenant_id::text = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));

CREATE INDEX IF NOT EXISTS idx_notifications_tenant_unread
    ON public.notifications(tenant_id, read, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_user
    ON public.notifications(tenant_id, user_id, created_at DESC);
