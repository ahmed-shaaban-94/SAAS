# Using the DataPulse Second Brain

> Project session memory lives in `docs/brain/`. Read at session start, write after non-trivial fixes or decisions.

## When to use (MANDATORY)

### 1. Session start — always
Read `docs/brain/_INDEX.md` to see the last 5 sessions across the whole team:
- What layers were touched recently
- Which modules are in active change
- Who was working on what branch

Before any exploration or code change. The index is regenerated locally from `session-log.csv` (shared, in git).

### 2. Before touching a module that appears in recent sessions
Read `docs/brain/sessions/<latest>.md` to see exactly what changed. Takes 5 seconds, avoids duplicating work or conflicting with someone's in-flight changes.

### 3. After solving a non-trivial bug or incident
Write `docs/brain/incidents/YYYY-MM-DD-<slug>.md`:
- Root cause + fix + which layer/module
- Link to `global-lessons.md` if cross-project applicable
- Use format: `[[layer]]` + `[[module]]` wikilinks for Obsidian graph

### 4. After a session-level architecture decision
Write `docs/brain/decisions/YYYY-MM-DD-<slug>.md`:
- Why this approach over the alternatives
- Link to the layer: `[[api]]`, `[[gold]]`, etc.
- Full ADRs go in `docs/adr/` — this is for smaller session-level decisions.

## Brain vs Graph MCP — when to use which

| Need | Tool |
|------|------|
| What happened in recent sessions | Brain `_INDEX.md` |
| Who calls this function right now | Graph MCP `dp_context` |
| What breaks if I change X | Graph MCP `dp_impact` |
| Why was this decision made | Brain `decisions/` |
| What layer does this file belong to | Graph MCP `dp_query` |
| What did we fix last session | Brain `sessions/` |

**Graph MCP = WHAT the code is. Brain = WHY decisions were made.**

## Session end — automatic

The Stop hook `.claude/hooks/brain-session-end.sh` fires automatically:
- Appends a row to `docs/brain/session-log.csv` (shared, git-tracked, auto-staged)
- Writes `docs/brain/sessions/YYYY-MM-DD-HH-MM.md` (local detail, gitignored)
- Regenerates `docs/brain/_INDEX.md` (local, gitignored)

**Why CSV for the shared log**: append-only → no git conflicts on merge. Every teammate's sessions appear in every other teammate's `_INDEX.md`. Full session detail stays local (no noise in git, no token bloat).

Only `session-log.csv`, `decisions/`, and `incidents/` are committed. You do NOT need to manually write session notes — the hook handles it.

## Vault structure

```
docs/brain/
├── _INDEX.md          <- READ THIS at session start (gitignored, auto-generated)
├── session-log.csv    <- shared row-per-session log (git-tracked)
├── sessions/          <- auto-generated (hook writes, do not edit manually)
├── layers/            <- Phase 2: bronze.md, silver.md, gold.md, api.md, frontend.md
├── modules/           <- Phase 2: analytics.md, pipeline.md, rbac.md, etc.
├── decisions/         <- write here for session-level decisions (git-tracked)
├── roles/             <- Phase 2: gm.md, pipeline-engineer.md, etc.
└── incidents/         <- write here after fixing non-trivial bugs (git-tracked)
```

## Do NOT skip brain reads when

- Starting any session (`_INDEX.md` always)
- A module in recent sessions overlaps with your current task
- About to fix a bug that feels like you've seen it before
- Making a decision that future-you or teammates will need to understand
