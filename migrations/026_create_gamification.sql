-- Migration: Gamification System — badges, streaks, competitions, XP, levels
-- Phase: 6.1 (Sales Gamification)
-- Run order: after 025_create_report_schedules.sql
-- Idempotent: safe to run multiple times (IF NOT EXISTS / DO $$ guards)

-- ============================================================
-- 1. Badges — definitions of earnable achievements
-- ============================================================
CREATE TABLE IF NOT EXISTS public.badges (
    badge_id        SERIAL PRIMARY KEY,
    tenant_id       INT NOT NULL DEFAULT 1,
    badge_key       TEXT NOT NULL,
    title_en        TEXT NOT NULL,
    title_ar        TEXT,
    description_en  TEXT NOT NULL DEFAULT '',
    description_ar  TEXT,
    icon            TEXT NOT NULL DEFAULT 'trophy',
    tier            TEXT NOT NULL DEFAULT 'bronze'
                    CHECK (tier IN ('bronze', 'silver', 'gold', 'platinum')),
    category        TEXT NOT NULL DEFAULT 'sales'
                    CHECK (category IN ('sales', 'streak', 'milestone', 'competition', 'special')),
    condition_type  TEXT NOT NULL DEFAULT 'manual',
    condition_value NUMERIC(18, 4) DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, badge_key)
);

-- ============================================================
-- 2. Staff Badges — earned badges per staff member
-- ============================================================
CREATE TABLE IF NOT EXISTS public.staff_badges (
    id              SERIAL PRIMARY KEY,
    tenant_id       INT NOT NULL DEFAULT 1,
    staff_key       INT NOT NULL,
    badge_id        INT NOT NULL REFERENCES public.badges(badge_id) ON DELETE CASCADE,
    earned_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    context         JSONB DEFAULT '{}',
    UNIQUE (tenant_id, staff_key, badge_id)
);

-- ============================================================
-- 3. Streaks — consecutive achievement tracking
-- ============================================================
CREATE TABLE IF NOT EXISTS public.streaks (
    id              SERIAL PRIMARY KEY,
    tenant_id       INT NOT NULL DEFAULT 1,
    staff_key       INT NOT NULL,
    streak_type     TEXT NOT NULL DEFAULT 'daily_target'
                    CHECK (streak_type IN ('daily_target', 'weekly_target', 'monthly_target',
                                           'daily_sales', 'customer_growth')),
    current_count   INT NOT NULL DEFAULT 0,
    best_count      INT NOT NULL DEFAULT 0,
    last_date       DATE,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, staff_key, streak_type)
);

-- ============================================================
-- 4. Competitions — team/individual sales competitions
-- ============================================================
CREATE TABLE IF NOT EXISTS public.competitions (
    competition_id  SERIAL PRIMARY KEY,
    tenant_id       INT NOT NULL DEFAULT 1,
    title           TEXT NOT NULL,
    description     TEXT DEFAULT '',
    competition_type TEXT NOT NULL DEFAULT 'individual'
                    CHECK (competition_type IN ('individual', 'team')),
    metric          TEXT NOT NULL DEFAULT 'revenue'
                    CHECK (metric IN ('revenue', 'transactions', 'customers', 'returns_reduction')),
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    status          TEXT NOT NULL DEFAULT 'upcoming'
                    CHECK (status IN ('upcoming', 'active', 'completed', 'cancelled')),
    prize_description TEXT,
    created_by      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (end_date > start_date)
);

-- ============================================================
-- 5. Competition Entries — participants & scores
-- ============================================================
CREATE TABLE IF NOT EXISTS public.competition_entries (
    id              SERIAL PRIMARY KEY,
    tenant_id       INT NOT NULL DEFAULT 1,
    competition_id  INT NOT NULL REFERENCES public.competitions(competition_id) ON DELETE CASCADE,
    staff_key       INT NOT NULL,
    score           NUMERIC(18, 4) NOT NULL DEFAULT 0,
    rank            INT,
    joined_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, competition_id, staff_key)
);

-- ============================================================
-- 6. XP Ledger — experience points history
-- ============================================================
CREATE TABLE IF NOT EXISTS public.xp_ledger (
    id              SERIAL PRIMARY KEY,
    tenant_id       INT NOT NULL DEFAULT 1,
    staff_key       INT NOT NULL,
    xp_amount       INT NOT NULL,
    source          TEXT NOT NULL DEFAULT 'sale',
    source_ref      TEXT,
    earned_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_xp_ledger_staff
    ON public.xp_ledger (tenant_id, staff_key);

CREATE INDEX IF NOT EXISTS idx_xp_ledger_earned
    ON public.xp_ledger (tenant_id, earned_at);

-- ============================================================
-- 7. Staff Levels — current level derived from total XP
-- ============================================================
CREATE TABLE IF NOT EXISTS public.staff_levels (
    id              SERIAL PRIMARY KEY,
    tenant_id       INT NOT NULL DEFAULT 1,
    staff_key       INT NOT NULL,
    level           INT NOT NULL DEFAULT 1,
    total_xp        INT NOT NULL DEFAULT 0,
    current_tier    TEXT NOT NULL DEFAULT 'bronze'
                    CHECK (current_tier IN ('bronze', 'silver', 'gold', 'platinum', 'diamond')),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, staff_key)
);

-- ============================================================
-- 8. Activity Feed — recent gamification events
-- ============================================================
CREATE TABLE IF NOT EXISTS public.gamification_feed (
    id              SERIAL PRIMARY KEY,
    tenant_id       INT NOT NULL DEFAULT 1,
    staff_key       INT NOT NULL,
    event_type      TEXT NOT NULL
                    CHECK (event_type IN ('badge_earned', 'level_up', 'streak_milestone',
                                          'competition_win', 'xp_bonus')),
    title           TEXT NOT NULL,
    description     TEXT DEFAULT '',
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_gamification_feed_tenant
    ON public.gamification_feed (tenant_id, created_at DESC);

-- ============================================================
-- 9. Row-Level Security
-- ============================================================
DO $$ BEGIN
    ALTER TABLE public.badges ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.badges FORCE ROW LEVEL SECURITY;
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE public.staff_badges ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.staff_badges FORCE ROW LEVEL SECURITY;
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE public.streaks ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.streaks FORCE ROW LEVEL SECURITY;
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE public.competitions ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.competitions FORCE ROW LEVEL SECURITY;
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE public.competition_entries ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.competition_entries FORCE ROW LEVEL SECURITY;
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE public.xp_ledger ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.xp_ledger FORCE ROW LEVEL SECURITY;
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE public.staff_levels ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.staff_levels FORCE ROW LEVEL SECURITY;
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE public.gamification_feed ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.gamification_feed FORCE ROW LEVEL SECURITY;
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

-- Owner (datapulse) — full access
DO $$ BEGIN
    CREATE POLICY badges_owner ON public.badges FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY staff_badges_owner ON public.staff_badges FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY streaks_owner ON public.streaks FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY competitions_owner ON public.competitions FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY competition_entries_owner ON public.competition_entries FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY xp_ledger_owner ON public.xp_ledger FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY staff_levels_owner ON public.staff_levels FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY gamification_feed_owner ON public.gamification_feed FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Reader (datapulse_reader) — tenant-scoped read-only
DO $$ BEGIN
    CREATE POLICY badges_reader ON public.badges FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY staff_badges_reader ON public.staff_badges FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY streaks_reader ON public.streaks FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY competitions_reader ON public.competitions FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY competition_entries_reader ON public.competition_entries FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY xp_ledger_reader ON public.xp_ledger FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY staff_levels_reader ON public.staff_levels FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY gamification_feed_reader ON public.gamification_feed FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================
-- 10. Grants
-- ============================================================
GRANT SELECT ON TABLE public.badges TO datapulse_reader;
GRANT SELECT ON TABLE public.staff_badges TO datapulse_reader;
GRANT SELECT ON TABLE public.streaks TO datapulse_reader;
GRANT SELECT ON TABLE public.competitions TO datapulse_reader;
GRANT SELECT ON TABLE public.competition_entries TO datapulse_reader;
GRANT SELECT ON TABLE public.xp_ledger TO datapulse_reader;
GRANT SELECT ON TABLE public.staff_levels TO datapulse_reader;
GRANT SELECT ON TABLE public.gamification_feed TO datapulse_reader;

-- ============================================================
-- 11. Seed default badges
-- ============================================================
INSERT INTO public.badges (tenant_id, badge_key, title_en, title_ar, icon, tier, category, condition_type, condition_value)
VALUES
    (1, 'first_sale',       'First Sale',        'أول بيعة',           'sparkles',    'bronze',   'milestone',    'total_sales',      1),
    (1, 'century_club',     'Century Club',      'نادي المئة',         'target',      'silver',   'sales',        'monthly_txn',      100),
    (1, 'quarter_million',  'Quarter Million',   'ربع مليون',          'banknote',    'silver',   'milestone',    'monthly_revenue',  250000),
    (1, 'million_maker',    'Million Maker',     'صانع المليون',       'gem',         'gold',     'milestone',    'monthly_revenue',  1000000),
    (1, 'streak_7',         '7-Day Streak',      'سلسلة 7 أيام',      'flame',       'bronze',   'streak',       'streak_days',      7),
    (1, 'streak_30',        '30-Day Streak',     'سلسلة 30 يوم',      'fire',        'silver',   'streak',       'streak_days',      30),
    (1, 'streak_90',        '90-Day Streak',     'سلسلة 90 يوم',      'zap',         'gold',     'streak',       'streak_days',      90),
    (1, 'customer_magnet',  'Customer Magnet',   'مغناطيس العملاء',    'users',       'silver',   'sales',        'monthly_customers', 50),
    (1, 'comeback_king',    'Comeback King',     'ملك العودة',         'trending-up', 'silver',   'special',      'mom_growth_pct',   50),
    (1, 'perfect_quarter',  'Perfect Quarter',   'ربع مثالي',          'crown',       'platinum', 'milestone',    'quarter_100pct',   3),
    (1, 'top_performer',    'Top Performer',     'الأفضل أداءً',       'award',       'gold',     'competition',  'rank_first',       1),
    (1, 'zero_returns',     'Zero Returns',      'صفر مرتجعات',        'shield',      'gold',     'special',      'monthly_returns',  0)
ON CONFLICT (tenant_id, badge_key) DO NOTHING;
