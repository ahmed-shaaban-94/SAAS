---
name: zambahola
description: Cross-model review gate — sends current work to OpenAI Codex for independent code review and adversarial challenge. Activates ONLY when explicitly called.
user-invocable: true
---

# Zambahola — Cross-Model Review Gate

You are the orchestrator for a **dual-model quality gate**. The user has decided to send their current work to OpenAI Codex for an independent review before proceeding.

## Pre-Flight Check

Before running ANY Codex command, verify:
1. Codex plugin is installed: check if `/codex:setup` is available
2. If NOT installed, tell the user:
   ```
   Codex plugin not detected. To install:
   /plugin marketplace add openai/codex-plugin-cc
   /plugin install codex@openai-codex
   /reload-plugins
   /codex:setup
   ```
   Then STOP — do not proceed until the user confirms setup.

## Execution Flow

### Step 1: Assess What to Review

Check the current state:
- Run `git status` and `git diff --stat` to see what changed
- If there's a branch vs main difference, use `--base main`
- If only uncommitted changes, review those

Tell the user what will be reviewed (file count, lines changed).

### Step 2: Standard Codex Review

Run:
```
/codex:review --base main --background
```

Wait for completion:
```
/codex:status
```

Read results:
```
/codex:result
```

Present the findings to the user in a structured format:
- CRITICAL issues (must fix)
- HIGH issues (should fix)
- MEDIUM issues (consider fixing)
- LOW issues (optional)

### Step 3: Adversarial Review (if warranted)

Ask the user if they want an adversarial review. If yes, or if the changes touch any of these:
- Authentication / authorization / JWT / API keys
- Database queries / SQL / filters
- RLS / tenant isolation
- Financial calculations
- Cache logic
- Data pipeline / ETL

Then run:
```
/codex:adversarial-review --base main [focus area based on what changed]
```

Present adversarial findings separately.

### Step 4: Accreditation Decision

Based on Codex findings, present the verdict:

| Level | Meaning | Action |
|-------|---------|--------|
| **ACCREDITED** | 0 critical/high issues | Safe to push/merge |
| **CONDITIONAL** | Medium issues only, fixable quickly | Fix then re-review or accept |
| **BLOCKED** | Critical issues found | Must fix before proceeding |
| **ESCALATED** | Disagreement between models | Human decides |

### Step 5: Summary

Output a review summary block:
```
Zambahola Review Summary
════════════════════════
Reviewed: [X files, Y lines changed]
Standard Review: [PASS/FAIL] — [N findings]
Adversarial Review: [PASS/FAIL/SKIPPED] — [N findings]
Verdict: [ACCREDITED / CONDITIONAL / BLOCKED / ESCALATED]
Action: [what to do next]
```

## Important Rules

- This skill is **read-only** — Codex reviews only, never writes code
- Claude handles ALL fixes if issues are found
- Do NOT enable the auto review gate (`--enable-review-gate`) — manual only
- If Codex is unavailable or quota exceeded, inform the user and STOP
- This works for ANY project, ANY branch, ANY changes — not tied to specific phases

## Optional Arguments

The user can pass focus areas after zambahola:
- `/zambahola` — full review of current changes
- `/zambahola security` — adversarial review focused on security
- `/zambahola performance` — adversarial review focused on performance
- `/zambahola data-integrity` — adversarial review focused on data correctness
- `/zambahola quick` — standard review only, skip adversarial
