-- Migration: 039 – Brain schema for session tracking and knowledge base
-- Layer: infrastructure
-- Replaces: markdown/CSV brain (docs/brain/) with PostgreSQL-backed FTS + pgvector
--
-- Requires: pgvector extension (image: pgvector/pgvector:pg16)
-- Idempotent: safe to run multiple times

-- ============================================================
-- 1. Enable pgvector extension
-- ============================================================
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- 2. Create brain schema
-- ============================================================
CREATE SCHEMA IF NOT EXISTS brain;

DO $$ BEGIN
    GRANT USAGE ON SCHEMA brain TO datapulse_reader;
EXCEPTION WHEN undefined_object THEN
    RAISE NOTICE 'Role datapulse_reader does not exist yet — skipping GRANT';
END $$;

DO $$ BEGIN
    ALTER DEFAULT PRIVILEGES IN SCHEMA brain
        GRANT SELECT ON TABLES TO datapulse_reader;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

-- ============================================================
-- 3. Helper functions for tsvector generation
-- ============================================================
CREATE OR REPLACE FUNCTION brain.make_session_tsvector(
    p_branch TEXT,
    p_layers TEXT[],
    p_modules TEXT[],
    p_files TEXT[],
    p_body TEXT
) RETURNS tsvector
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT
        setweight(to_tsvector('english', COALESCE(p_branch, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(array_to_string(p_layers, ' '), '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(array_to_string(p_modules, ' '), '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(array_to_string(p_files, ' '), '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(p_body, '')), 'C')
$$;

CREATE OR REPLACE FUNCTION brain.make_note_tsvector(
    p_title TEXT,
    p_body TEXT,
    p_tags TEXT[]
) RETURNS tsvector
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT
        setweight(to_tsvector('english', COALESCE(p_title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(array_to_string(p_tags, ' '), '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(p_body, '')), 'B')
$$;

-- ============================================================
-- 4. brain.sessions
-- ============================================================
CREATE TABLE IF NOT EXISTS brain.sessions (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id   INT NOT NULL DEFAULT 1,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT now(),
    branch      TEXT NOT NULL DEFAULT '',
    user_name   TEXT NOT NULL DEFAULT '',
    layers      TEXT[] NOT NULL DEFAULT '{}',
    modules     TEXT[] NOT NULL DEFAULT '{}',
    files_changed TEXT[] NOT NULL DEFAULT '{}',
    commits     JSONB NOT NULL DEFAULT '[]',
    body_md     TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- tsvector (generated stored) — added via ALTER to stay idempotent
DO $$ BEGIN
    ALTER TABLE brain.sessions ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            brain.make_session_tsvector(branch, layers, modules, files_changed, body_md)
        ) STORED;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- pgvector embedding column — nullable until embeddings are generated
DO $$ BEGIN
    ALTER TABLE brain.sessions ADD COLUMN embedding vector(1536);
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- ============================================================
-- 5. brain.decisions
-- ============================================================
CREATE TABLE IF NOT EXISTS brain.decisions (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id   INT NOT NULL DEFAULT 1,
    session_id  BIGINT REFERENCES brain.sessions(id) ON DELETE SET NULL,
    title       TEXT NOT NULL,
    body_md     TEXT NOT NULL DEFAULT '',
    tags        TEXT[] NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$ BEGIN
    ALTER TABLE brain.decisions ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            brain.make_note_tsvector(title, body_md, tags)
        ) STORED;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE brain.decisions ADD COLUMN embedding vector(1536);
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- ============================================================
-- 6. brain.incidents
-- ============================================================
CREATE TABLE IF NOT EXISTS brain.incidents (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id   INT NOT NULL DEFAULT 1,
    session_id  BIGINT REFERENCES brain.sessions(id) ON DELETE SET NULL,
    title       TEXT NOT NULL,
    severity    TEXT NOT NULL DEFAULT 'low'
                CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    body_md     TEXT NOT NULL DEFAULT '',
    tags        TEXT[] NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$ BEGIN
    ALTER TABLE brain.incidents ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            brain.make_note_tsvector(title, body_md, tags)
        ) STORED;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE brain.incidents ADD COLUMN embedding vector(1536);
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- ============================================================
-- 7. Indexes
-- ============================================================
-- Full-text search (GIN)
CREATE INDEX IF NOT EXISTS idx_brain_sessions_search
    ON brain.sessions USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_brain_decisions_search
    ON brain.decisions USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_brain_incidents_search
    ON brain.incidents USING GIN(search_vector);

-- Semantic search (HNSW for cosine similarity)
CREATE INDEX IF NOT EXISTS idx_brain_sessions_embedding
    ON brain.sessions USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_brain_decisions_embedding
    ON brain.decisions USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_brain_incidents_embedding
    ON brain.incidents USING hnsw (embedding vector_cosine_ops);

-- Tenant isolation (B-tree)
CREATE INDEX IF NOT EXISTS idx_brain_sessions_tenant
    ON brain.sessions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_brain_decisions_tenant
    ON brain.decisions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_brain_incidents_tenant
    ON brain.incidents(tenant_id);

-- Temporal + branch
CREATE INDEX IF NOT EXISTS idx_brain_sessions_timestamp
    ON brain.sessions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_brain_sessions_branch
    ON brain.sessions(branch);

-- Array containment (GIN)
CREATE INDEX IF NOT EXISTS idx_brain_sessions_layers
    ON brain.sessions USING GIN(layers);
CREATE INDEX IF NOT EXISTS idx_brain_sessions_modules
    ON brain.sessions USING GIN(modules);

-- Foreign key lookups
CREATE INDEX IF NOT EXISTS idx_brain_decisions_session
    ON brain.decisions(session_id);
CREATE INDEX IF NOT EXISTS idx_brain_incidents_session
    ON brain.incidents(session_id);

-- ============================================================
-- 8. Access control
-- ============================================================
-- Brain stores per-developer session memory (git diff, decisions, incidents)
-- captured by the local Stop hook — not multi-tenant business data. RLS is
-- deliberately NOT enabled here because the hook connects via raw psycopg2
-- from outside the API container and has no JWT → app.tenant_id context.
-- The tenant_id column is retained for future use.

-- Drop any previously-applied RLS state so re-running this migration is idempotent.
DROP POLICY IF EXISTS tenant_isolation_brain_sessions  ON brain.sessions;
DROP POLICY IF EXISTS tenant_isolation_brain_decisions ON brain.decisions;
DROP POLICY IF EXISTS tenant_isolation_brain_incidents ON brain.incidents;
ALTER TABLE brain.sessions  NO FORCE ROW LEVEL SECURITY;
ALTER TABLE brain.sessions  DISABLE ROW LEVEL SECURITY;
ALTER TABLE brain.decisions NO FORCE ROW LEVEL SECURITY;
ALTER TABLE brain.decisions DISABLE ROW LEVEL SECURITY;
ALTER TABLE brain.incidents NO FORCE ROW LEVEL SECURITY;
ALTER TABLE brain.incidents DISABLE ROW LEVEL SECURITY;

-- ============================================================
-- 9. Comments
-- ============================================================
COMMENT ON SCHEMA brain IS
    'Second Brain — session tracking, decisions, and incident notes for Claude Code.';
COMMENT ON TABLE brain.sessions IS
    'Auto-captured session data from Claude Code Stop hook. '
    'FTS via search_vector (GIN), semantic via embedding (HNSW cosine).';
COMMENT ON TABLE brain.decisions IS
    'Lightweight decision records captured during sessions.';
COMMENT ON TABLE brain.incidents IS
    'Post-incident notes with severity levels.';
