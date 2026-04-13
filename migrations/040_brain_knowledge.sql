-- Migration: 040 – brain.knowledge — Project knowledge base table
-- Layer: infrastructure
-- Adds a dedicated knowledge table to the brain schema for storing
-- static project info: architecture docs, API contracts, dbt model
-- explanations, runbooks, onboarding guides, etc.
--
-- Reuses existing brain.make_note_tsvector() for FTS weight parity
-- with brain.decisions and brain.incidents.
-- Idempotent: safe to run multiple times

-- ============================================================
-- 1. brain.knowledge table
-- ============================================================
CREATE TABLE IF NOT EXISTS brain.knowledge (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id   INT NOT NULL DEFAULT 1,
    category    TEXT NOT NULL DEFAULT 'general',
    title       TEXT NOT NULL,
    body_md     TEXT NOT NULL DEFAULT '',
    tags        TEXT[] NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE brain.knowledge IS
    'Static project knowledge — architecture docs, API contracts, dbt explanations, runbooks. '
    'FTS via search_vector (GIN), semantic via embedding (HNSW cosine).';
COMMENT ON COLUMN brain.knowledge.category IS
    'Logical grouping: architecture, api, dbt, runbook, onboarding, glossary, etc.';

-- ============================================================
-- 2. search_vector generated column (reuses make_note_tsvector)
-- ============================================================
DO $$ BEGIN
    ALTER TABLE brain.knowledge ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            brain.make_note_tsvector(title, body_md, tags)
        ) STORED;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- ============================================================
-- 3. pgvector embedding column — nullable until embeddings are generated
-- ============================================================
DO $$ BEGIN
    ALTER TABLE brain.knowledge ADD COLUMN embedding vector(1536);
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- ============================================================
-- 4. updated_at trigger
-- ============================================================
CREATE OR REPLACE FUNCTION brain.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_knowledge_updated_at ON brain.knowledge;
CREATE TRIGGER trg_knowledge_updated_at
    BEFORE UPDATE ON brain.knowledge
    FOR EACH ROW EXECUTE FUNCTION brain.set_updated_at();

-- ============================================================
-- 5. Indexes
-- ============================================================
-- Full-text search (GIN)
CREATE INDEX IF NOT EXISTS idx_brain_knowledge_search
    ON brain.knowledge USING GIN(search_vector);

-- Tag containment (GIN)
CREATE INDEX IF NOT EXISTS idx_brain_knowledge_tags
    ON brain.knowledge USING GIN(tags);

-- Semantic search (HNSW for cosine similarity)
CREATE INDEX IF NOT EXISTS idx_brain_knowledge_embedding
    ON brain.knowledge USING hnsw (embedding vector_cosine_ops);

-- Category and tenant lookups (B-tree)
CREATE INDEX IF NOT EXISTS idx_brain_knowledge_category
    ON brain.knowledge(category);
CREATE INDEX IF NOT EXISTS idx_brain_knowledge_tenant
    ON brain.knowledge(tenant_id);

-- ============================================================
-- 6. Access control — mirrors brain.decisions (no RLS, same rationale)
-- ============================================================
DROP POLICY IF EXISTS tenant_isolation_brain_knowledge ON brain.knowledge;
ALTER TABLE brain.knowledge NO FORCE ROW LEVEL SECURITY;
ALTER TABLE brain.knowledge DISABLE ROW LEVEL SECURITY;
