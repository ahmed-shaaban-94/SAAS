-- Migration: 114 - Harden POS idempotency scope and shift-open RBAC
-- Layer: POS operational / RBAC
-- Idempotent.

-- Idempotency keys are scoped by tenant in application code. The original
-- table made key globally unique, so two tenants using the same UUID-style
-- key could collide. Replace that with a tenant/key primary key.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
          FROM information_schema.table_constraints
         WHERE table_schema = 'pos'
           AND table_name = 'idempotency_keys'
           AND constraint_name = 'idempotency_keys_pkey'
    ) THEN
        ALTER TABLE pos.idempotency_keys DROP CONSTRAINT idempotency_keys_pkey;
    END IF;
END $$;

DO $$
BEGIN
    ALTER TABLE pos.idempotency_keys
        ADD CONSTRAINT idempotency_keys_pkey PRIMARY KEY (tenant_id, key);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_pos_idemp_key
    ON pos.idempotency_keys (key);

-- start_shift and cash drawer events are mutating POS operations and now have
-- explicit route-level permission checks. Seed the permissions and grant them
-- to POS roles that can already operate terminals.
INSERT INTO public.permissions (permission_key, category, description)
VALUES
    ('pos:shift:open', 'pos', 'Open a POS cashier shift'),
    ('pos:cash:event:create', 'pos', 'Record a POS cash drawer event')
ON CONFLICT (permission_key) DO NOTHING;

INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key IN ('pos_cashier', 'pos_pharmacist', 'pos_supervisor')
  AND p.permission_key IN ('pos:shift:open', 'pos:cash:event:create')
ON CONFLICT DO NOTHING;
