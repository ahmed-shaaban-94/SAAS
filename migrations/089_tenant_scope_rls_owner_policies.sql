-- Migration 089 — Tenant-scope every permissive owner_all RLS policy
--
-- Background
-- ==========
-- Migration 037 fixed the P0 RLS hole for the 14 tables that existed at
-- that time. Every table created after 037 (control-center, inventory,
-- suppliers/POs, gamification, branding, ALL of POS) copied the old
-- ``USING (true) WITH CHECK (true)`` pattern and so the ``datapulse`` app
-- role has no DB-level tenant isolation on those tables. This migration
-- brings every such policy into line with the 037-era contract:
--
--   - When ``app.tenant_id`` is SET (API sessions): only matching tenant rows.
--   - When ``app.tenant_id`` is NULL/empty (pipeline / admin / test runners):
--     all rows still visible, preserving backward compatibility for
--     offline pipeline scripts.
--
-- Scope
-- =====
-- 40 policies across 29 tables in ``public``, ``bronze`` and ``pos`` schemas.
-- Tables without a ``tenant_id`` column are intentionally excluded.
--
-- Idempotent: DROP POLICY IF EXISTS + CREATE POLICY.
-- Rollback: re-create each policy with ``USING (true) WITH CHECK (true)``.

-- ---------------------------------------------------------------------------
-- Shared helper — all tenant-scoped policies use this exact expression pair.
-- Kept inline (not as a SQL function) so the migration is readable top-to-bottom.
-- ---------------------------------------------------------------------------
--  USING  (NULLIF(current_setting('app.tenant_id', true), '') IS NULL
--          OR tenant_id = current_setting('app.tenant_id', true)::INT)
--  WITH CHECK (same)

-- ============================================================
-- Gamification (migration 026)
-- ============================================================

DROP POLICY IF EXISTS badges_owner ON public.badges;
CREATE POLICY badges_owner ON public.badges
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS staff_badges_owner ON public.staff_badges;
CREATE POLICY staff_badges_owner ON public.staff_badges
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS streaks_owner ON public.streaks;
CREATE POLICY streaks_owner ON public.streaks
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS competitions_owner ON public.competitions;
CREATE POLICY competitions_owner ON public.competitions
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS competition_entries_owner ON public.competition_entries;
CREATE POLICY competition_entries_owner ON public.competition_entries
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS xp_ledger_owner ON public.xp_ledger;
CREATE POLICY xp_ledger_owner ON public.xp_ledger
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS staff_levels_owner ON public.staff_levels;
CREATE POLICY staff_levels_owner ON public.staff_levels
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS gamification_feed_owner ON public.gamification_feed;
CREATE POLICY gamification_feed_owner ON public.gamification_feed
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

-- ============================================================
-- Branding (migration 027)
-- ============================================================

DROP POLICY IF EXISTS branding_owner ON public.tenant_branding;
CREATE POLICY branding_owner ON public.tenant_branding
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

-- ============================================================
-- Control Center (migrations 041-048)
-- ============================================================

DROP POLICY IF EXISTS owner_all ON public.source_connections;
CREATE POLICY owner_all ON public.source_connections
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON public.pipeline_profiles;
CREATE POLICY owner_all ON public.pipeline_profiles
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON public.mapping_templates;
CREATE POLICY owner_all ON public.mapping_templates
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON public.pipeline_drafts;
CREATE POLICY owner_all ON public.pipeline_drafts
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON public.sync_jobs;
CREATE POLICY owner_all ON public.sync_jobs
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON public.sync_schedules;
CREATE POLICY owner_all ON public.sync_schedules
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON public.source_credentials;
CREATE POLICY owner_all ON public.source_credentials
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

-- ============================================================
-- Inventory (migrations 050-052)
-- ============================================================

DROP POLICY IF EXISTS owner_all ON bronze.stock_receipts;
CREATE POLICY owner_all ON bronze.stock_receipts
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON bronze.stock_adjustments;
CREATE POLICY owner_all ON bronze.stock_adjustments
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON bronze.inventory_counts;
CREATE POLICY owner_all ON bronze.inventory_counts
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON public.reorder_config;
CREATE POLICY owner_all ON public.reorder_config
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON bronze.batches;
CREATE POLICY owner_all ON bronze.batches
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

-- ============================================================
-- Suppliers + Purchase Orders (migrations 053-055)
-- ============================================================

DROP POLICY IF EXISTS owner_all ON bronze.suppliers;
CREATE POLICY owner_all ON bronze.suppliers
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON bronze.purchase_orders;
CREATE POLICY owner_all ON bronze.purchase_orders
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON bronze.po_lines;
CREATE POLICY owner_all ON bronze.po_lines
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

-- ============================================================
-- Bronze POS (migration 056 — feeds the medallion pipeline)
-- ============================================================

DROP POLICY IF EXISTS owner_all ON bronze.pos_transactions;
CREATE POLICY owner_all ON bronze.pos_transactions
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

-- ============================================================
-- Operational POS (migrations 065-083)
-- ============================================================

DROP POLICY IF EXISTS owner_all ON pos.terminal_sessions;
CREATE POLICY owner_all ON pos.terminal_sessions
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON pos.transactions;
CREATE POLICY owner_all ON pos.transactions
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON pos.transaction_items;
CREATE POLICY owner_all ON pos.transaction_items
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON pos.receipts;
CREATE POLICY owner_all ON pos.receipts
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON pos.shift_records;
CREATE POLICY owner_all ON pos.shift_records
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON pos.cash_drawer_events;
CREATE POLICY owner_all ON pos.cash_drawer_events
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON pos.void_log;
CREATE POLICY owner_all ON pos.void_log
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON pos.returns;
CREATE POLICY owner_all ON pos.returns
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON pos.idempotency_keys;
CREATE POLICY owner_all ON pos.idempotency_keys
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON pos.terminal_devices;
CREATE POLICY owner_all ON pos.terminal_devices
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON pos.tenant_keys;
CREATE POLICY owner_all ON pos.tenant_keys
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON pos.grants_issued;
CREATE POLICY owner_all ON pos.grants_issued
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON pos.override_consumptions;
CREATE POLICY owner_all ON pos.override_consumptions
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all ON pos.shifts_close_attempts;
CREATE POLICY owner_all ON pos.shifts_close_attempts
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );
