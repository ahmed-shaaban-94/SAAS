# `datapulse.brain` — Second Brain

PostgreSQL-backed session memory for Claude Code. Captures what each session
touched (files, commits, layers, modules) and lets future sessions search
across them.

## Storage model

Three tables in the `brain` schema:

| Table | Purpose |
|-------|---------|
| `brain.sessions`  | Auto-captured by the Stop hook — branch, layers, modules, files_changed, commits |
| `brain.decisions` | Lightweight decision records — logged explicitly via the MCP tool |
| `brain.incidents` | Post-incident notes with severity (low/medium/high/critical) |

Each table has:
- `search_vector` (GIN-indexed `tsvector`) for full-text search
- `embedding`     (HNSW-indexed `vector(1536)`) for semantic search
- `tenant_id`     retained for future scoping (see "Access control" below)

## Access control

Brain stores per-developer session memory captured by the local Stop hook —
not multi-tenant business data. RLS is **not** enabled on `brain.*`: the hook
runs outside the API container and has no JWT → `app.tenant_id` context, so
`FORCE ROW LEVEL SECURITY` would silently block every insert. The `tenant_id`
column is kept for future multi-tenant hosting but is not enforced today.

## How it runs

- The `Stop` hook fires `.claude/hooks/brain-session-end.sh`, which delegates
  to `python -m datapulse.brain.session_end`.
- If the DB is reachable, the session is inserted into `brain.sessions` and
  `docs/brain/_INDEX.md` is regenerated from the DB.
- If the DB is not reachable (no `DATABASE_URL`, container down, etc.) the
  hook falls back to writing a markdown session note under
  `docs/brain/sessions/YYYY-MM-DD-HH-MM.md` and regenerating `_INDEX.md` from
  those files. The CSV log is only appended on fallback.

## Semantic search — current status

`embeddings.py` calls `https://openrouter.ai/api/v1/embeddings` with the model
configured in `BRAIN_EMBED_MODEL` (default `openai/text-embedding-3-small`).
**This endpoint was not validated in the initial rollout.** OpenRouter's
embeddings coverage is provider-dependent and may differ from the well-tested
chat/completions endpoint used by `datapulse.ai_light`.

If `get_embedding()` returns `None`, the brain falls back to FTS-only — the
`brain_search` MCP tool and all hook inserts remain fully functional. The
`embedding` column is simply left `NULL` on those rows.

To enable semantic search with confidence, choose one:

1. **Verify OpenRouter** — manually test the endpoint with your key:

   ```bash
   curl https://openrouter.ai/api/v1/embeddings \
     -H "Authorization: Bearer $OPENROUTER_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model": "openai/text-embedding-3-small", "input": "hello"}'
   ```

   If this returns a `data[0].embedding` array, the default path works.

2. **Swap to OpenAI direct** — add `OPENAI_API_KEY` to `.env` and point
   `embeddings.py` at `https://api.openai.com/v1/embeddings` (drop the
   OpenRouter referrer headers). Costs ~$0.02 per 1M tokens.

Existing rows with `NULL` embeddings can be back-filled later by looping over
`brain.sessions WHERE embedding IS NULL` and calling
`update_embedding('sessions', id, vec)`.

## MCP tools

The graph MCP server (`python -m datapulse.graph.mcp_server`) also exposes
five brain tools:

| Tool                | Purpose |
|---------------------|---------|
| `brain_search`      | Hybrid FTS + semantic search (falls back to FTS-only) |
| `brain_recent`      | Last N sessions (default 5, max 20) |
| `brain_session`     | Full detail of one session, with linked decisions/incidents |
| `brain_log_decision`| Record a decision record (generates embedding if available) |
| `brain_log_incident`| Record an incident note with severity |

## Migration

`migrations/039_create_brain_schema.sql` is idempotent — re-runs are safe.
Requires the `pgvector` extension (image `pgvector/pgvector:pg16`).

To back-fill from the pre-existing markdown vault:

```bash
PYTHONPATH=src python -m datapulse.brain.migrate_csv --project-dir /path/to/repo
```
