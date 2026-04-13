# Rule: Use DataPulse Second Brain for Session Context

## When to Use the Brain (MANDATORY)

### 1. Session Start — ALWAYS
```
Read docs/brain/_INDEX.md -> get last 5 sessions context (all team members)
```
- What layers were touched recently across the whole team
- What modules are in active change
- Who was working on what branch
- Do this BEFORE any exploration or code changes

> `_INDEX.md` is regenerated locally from `session-log.csv` — it reflects
> everyone's sessions, not just yours.

### 2. Before Touching a Module That Appears in Recent Sessions
```
Read docs/brain/sessions/<latest>.md -> see exactly what changed
```
- If `_INDEX.md` shows a module was touched in the last session, read the full note
- Avoids duplicating work or conflicting with recent changes
- Takes 5 seconds, saves hours of confusion

### 3. After Solving a Non-Trivial Bug or Incident
```
brain_log_incident(title, body_md, severity)
```
- Root cause + fix + which layer/module in body_md
- Also add to `C:\Users\user\.claude\global-lessons.md` if cross-project applicable
- Severity: `low` | `medium` | `high` | `critical`

### 4. After Making an Architecture Decision (not ADR-worthy but worth keeping)
```
brain_log_decision(title, body_md)
```
- Why this approach was chosen over alternatives
- Link to the layer in body_md: e.g. `api`, `gold`, etc.
- Full ADRs go in `docs/adr/` — this is for smaller session-level decisions

### 5. When You Learn Something Worth Keeping as Project Reference
```
brain_log_knowledge(title, body_md, category, tags)
```
Use for **static project info** that teammates or future sessions should be able to search:
- Architecture overviews, data flow explanations
- API contract summaries (request/response shapes)
- dbt model explanations (what a dimension/fact/agg contains)
- Runbooks (how to re-run the bronze pipeline, apply migrations, etc.)
- Onboarding guides, glossary entries

**Categories to use consistently:**
`architecture`, `api`, `dbt`, `runbook`, `onboarding`, `glossary`, `security`, `testing`

**Search it back with:**
```
brain_knowledge_search(query="bronze loader parquet")
brain_knowledge_search(query="tenant RLS", category="security")
```

> Unlike `decisions` (session-linked, ephemeral context) and `incidents` (bugs/fixes),
> `knowledge` is **evergreen reference material** — write it once, retrieve it forever.

## Brain vs Graph MCP — When to Use Which

| Need | Tool |
|------|------|
| What happened in recent sessions | Brain `_INDEX.md` |
| Who calls this function right now | Graph MCP `dp_context` |
| What will break if I change X | Graph MCP `dp_impact` |
| Why was this decision made | Brain `brain_log_decision` |
| What layer does this file belong to | Graph MCP `dp_query` |
| What did we fix last session | Brain `sessions/` |
| How does this module/API work | Brain `brain_knowledge_search` |
| What's the runbook for X | Brain `brain_knowledge_search(category="runbook")` |

They are complementary: **Graph MCP = WHAT the code is. Brain = WHY decisions were made + HOW things work.**

## Session End — Automatic (no action needed)

The Stop hook `.claude/hooks/brain-session-end.sh` fires automatically:
- Appends one row to `docs/brain/session-log.csv` (shared, tracked in git, auto-staged)
- Writes `docs/brain/sessions/YYYY-MM-DD-HH-MM.md` (local detail, gitignored)
- Regenerates `docs/brain/_INDEX.md` from the CSV (local, gitignored)

**Why CSV for the shared log:**
- Append-only = git never conflicts on merge
- Every team member's sessions appear in every other member's `_INDEX.md`
- Full session detail stays local (no noise in git, no token bloat)

Only `session-log.csv`, `decisions/`, and `incidents/` are committed.
You do NOT need to manually write session notes. The hook handles it.

## Vault Structure Reference

```
docs/brain/
├── _INDEX.md          <- READ THIS at session start
├── sessions/          <- Auto-generated (hook writes, do not edit manually)
├── layers/            <- Phase 2: bronze.md, silver.md, gold.md, api.md, frontend.md
├── modules/           <- Phase 2: analytics.md, pipeline.md, rbac.md, etc.
├── decisions/         <- Write here for session-level decisions
├── roles/             <- Phase 2: gm.md, pipeline-engineer.md, etc.
└── incidents/         <- Write here after fixing non-trivial bugs
```

## Do NOT Skip Brain Read When:
- Starting any session (always read `_INDEX.md` first)
- A module in `_INDEX.md` recent sessions overlaps with your current task
- You are about to fix a bug that feels like it may have been seen before
- You are making a decision that future-you or teammates will need to understand
