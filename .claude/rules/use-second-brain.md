# Rule: Use DataPulse Second Brain for Session Context

## When to Use the Brain (MANDATORY)

### 1. Session Start — ALWAYS
```
Read docs/brain/_INDEX.md -> get last 5 sessions context
```
- What layers were touched recently
- What modules are in active change
- What branch/work is in progress
- Do this BEFORE any exploration or code changes

### 2. Before Touching a Module That Appears in Recent Sessions
```
Read docs/brain/sessions/<latest>.md -> see exactly what changed
```
- If `_INDEX.md` shows a module was touched in the last session, read the full note
- Avoids duplicating work or conflicting with recent changes
- Takes 5 seconds, saves hours of confusion

### 3. After Solving a Non-Trivial Bug or Incident
```
Write docs/brain/incidents/YYYY-MM-DD-<slug>.md
```
- Root cause + fix + which layer/module
- Link to global-lessons.md if cross-project applicable
- Use format: `[[layer]]` + `[[module]]` wikilinks for Obsidian graph

### 4. After Making an Architecture Decision (not ADR-worthy but worth keeping)
```
Write docs/brain/decisions/YYYY-MM-DD-<slug>.md
```
- Why this approach was chosen over alternatives
- Link to the layer: `[[api]]`, `[[gold]]`, etc.
- Full ADRs go in `docs/adr/` — this is for smaller session-level decisions

## Brain vs Graph MCP — When to Use Which

| Need | Tool |
|------|------|
| What happened in recent sessions | Brain `_INDEX.md` |
| Who calls this function right now | Graph MCP `dp_context` |
| What will break if I change X | Graph MCP `dp_impact` |
| Why was this decision made | Brain `decisions/` |
| What layer does this file belong to | Graph MCP `dp_query` |
| What did we fix last session | Brain `sessions/` |

They are complementary: **Graph MCP = WHAT the code is. Brain = WHY decisions were made.**

## Session End — Automatic (no action needed)

The Stop hook `.claude/hooks/brain-session-end.sh` fires automatically:
- Writes `docs/brain/sessions/YYYY-MM-DD-HH-MM.md`
- Regenerates `docs/brain/_INDEX.md`

These files are **gitignored** (local-only context, never committed).
This prevents merge conflicts when multiple branches generate session notes.

Only `decisions/` and `incidents/` are tracked in git — commit those manually.

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
