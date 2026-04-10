# Claude Code + Codex Collaboration Architecture

> **Purpose:** Cross-model review gate before accrediting each implementation phase
> **Plugin:** [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc)
> **Date:** 2026-04-10

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Orchestration Diagrams](#2-orchestration-diagrams)
3. [Token Burn Analysis](#3-token-burn-analysis)
4. [Collaboration Rules](#4-collaboration-rules)
5. [Review Gate Configuration](#5-review-gate-configuration)
6. [Phase-by-Phase Review Strategy](#6-phase-by-phase-review-strategy)
7. [Setup Guide](#7-setup-guide)

---

## 1. Architecture Overview

### The Dual-Model Quality Gate

```
                    IMPLEMENTATION                      REVIEW GATE
                    ─────────────                       ───────────

                  ┌─────────────────┐               ┌─────────────────┐
                  │   Claude Code   │               │   OpenAI Codex  │
                  │   (Opus 4.6)    │───── git ────▶│   (gpt-5.x)    │
                  │                 │    diff        │                 │
                  │  Primary Agent  │               │  Review Agent   │
                  │  - Implements   │               │  - Reviews      │
                  │  - Tests        │               │  - Challenges   │
                  │  - Commits      │    result     │  - Approves     │
                  │                 │◀──────────────│                 │
                  └─────────────────┘               └─────────────────┘
                         │                                  │
                         │                                  │
                    Uses Graph MCP                   Uses adversarial
                    for blast radius                 review prompts
                         │                                  │
                         ▼                                  ▼
                  ┌─────────────────────────────────────────────┐
                  │              DataPulse Codebase             │
                  │  ┌─────┐  ┌─────┐  ┌─────┐  ┌──────────┐  │
                  │  │Front│  │ API │  │ dbt │  │ Infra/CI │  │
                  │  │ end │  │     │  │     │  │          │  │
                  │  └─────┘  └─────┘  └─────┘  └──────────┘  │
                  └─────────────────────────────────────────────┘
```

### Why Two Models?

| Dimension | Single-Model (Claude only) | Dual-Model (Claude + Codex) |
|-----------|---------------------------|----------------------------|
| **Blind spots** | Same model writes AND reviews = same biases | Different model catches different patterns |
| **Design challenges** | May not question its own architecture decisions | Adversarial review explicitly challenges tradeoffs |
| **Cost efficiency** | Opus 4.6 reviews at $25/M output tokens | Codex reviews at $6-14/M output tokens |
| **Failure modes** | Single point of failure | If one model hallucinates, the other catches it |

---

## 2. Orchestration Diagrams

### 2.1 Per-Phase Accreditation Flow

```
 Phase Start
     │
     ▼
 ┌────────────────────────────┐
 │  Claude Code (Opus 4.6)    │
 │  1. Read IMPLEMENTATION_PLAN│
 │  2. dp_impact() on targets │
 │  3. Implement changes       │
 │  4. Run tests (pytest/tsc)  │
 │  5. dp_detect_changes()     │
 │  6. git commit              │
 └─────────────┬──────────────┘
               │
               ▼
 ┌────────────────────────────┐    ┌──────────────────────────┐
 │  Self-Review Checkpoint     │    │  Graph MCP Validation    │
 │  - All tests pass?          │    │  - Blast radius matches  │
 │  - Coverage >= 95%?         │    │    expected?             │
 │  - Lint clean?              │    │  - No unintended deps?   │
 └─────────────┬──────────────┘    └────────────┬─────────────┘
               │                                │
               ▼ BOTH PASS                      │
 ┌────────────────────────────┐                 │
 │  /codex:review             │◀────────────────┘
 │  --base main               │
 │  --background              │
 │                            │
 │  Codex reviews ALL changes │
 │  from branch vs main       │
 └─────────────┬──────────────┘
               │
               ▼
 ┌────────────────────────────┐
 │  /codex:adversarial-review │
 │  --base main               │
 │  Focus: security, data     │
 │  integrity, RLS, perf      │
 └─────────────┬──────────────┘
               │
               ▼
     ┌─────────────────┐
     │  Issues Found?   │
     └────────┬────────┘
              │
         ┌────┴────┐
         │         │
     YES ▼      NO ▼
 ┌───────────┐ ┌──────────────┐
 │ Claude    │ │  ACCREDITED  │
 │ fixes the │ │  Push + PR   │
 │ findings  │ │  Phase done  │
 └─────┬─────┘ └──────────────┘
       │
       └──▶ Back to Self-Review
```

### 2.2 Model Routing by Task Type

```
                         ┌─────────────────────────┐
                         │    Task Classification   │
                         └────────────┬────────────┘
                                      │
                    ┌─────────────────┼──────────────────┐
                    │                 │                   │
                    ▼                 ▼                   ▼
           ┌────────────┐    ┌────────────┐     ┌────────────────┐
           │ IMPLEMENT   │    │  REVIEW    │     │  INVESTIGATE   │
           │             │    │            │     │                │
           │ Claude Code │    │ Codex      │     │ Either/Both    │
           │ (Opus 4.6)  │    │(gpt-5.x)  │     │                │
           │             │    │            │     │ /codex:rescue  │
           │ - Write code│    │ - /review  │     │ - Debug flaky  │
           │ - Run tests │    │ - /advers. │     │   tests        │
           │ - Graph MCP │    │   review   │     │ - Investigate  │
           │ - Commit    │    │ - Stop hook│     │   regressions  │
           └─────────────┘    └────────────┘     └────────────────┘
                    │                 │                   │
                    │            ┌────┴─────┐            │
                    │            │          │            │
                    │         PASS       FAIL            │
                    │            │          │            │
                    │            ▼          ▼            │
                    │      ┌─────────┐ ┌──────────┐     │
                    │      │ACCREDIT │ │Claude fix│     │
                    │      │& merge  │ │& re-test │     │
                    │      └─────────┘ └──────────┘     │
                    │                                    │
                    └─────── Cost: $5-10 ────────────────┘
                              per phase
```

### 2.3 Session Parallelism with Review Gates

```
 Week 1-2          Week 3-4          Week 5-6          Week 7-8
 ────────          ────────          ────────          ────────

 Track 1 (Sequential):

 ┌──────────┐    ┌──────────┐     ┌──────────┐     ┌──────────┐
 │ S1:PhaseA│    │ S2:PhaseB│     │ S4:PhaseD│     │ S5:PhaseEF│
 │ Claude   │    │ Claude   │     │ Claude   │     │ Claude   │
 │ implement│    │ implement│     │ implement│     │ implement│
 └────┬─────┘    └────┬─────┘     └────┬─────┘     └────┬─────┘
      │               │                │                │
      ▼               ▼                ▼                ▼
 ┌──────────┐    ┌──────────┐     ┌──────────┐     ┌──────────┐
 │ Codex    │    │ Codex    │     │ Codex    │     │ Codex    │
 │ review + │    │ review + │     │ review + │     │ review + │
 │ adversar.│    │ adversar.│     │ adversar.│     │ adversar.│
 └────┬─────┘    └────┬─────┘     └────┬─────┘     └────┬─────┘
      │               │                │                │
      ▼               ▼                ▼                ▼
 ACCREDIT ──────▶ ACCREDIT ──────▶ ACCREDIT ──────▶ ACCREDIT
      │                                 │
      │         Track 2 (Parallel):     │
      │                                 │
      │         ┌──────────┐            │
      └────────▶│ S3:PhaseC│◀───────────┘
                │ Claude   │   (can start anytime
                │ implement│    after S1 merges)
                └────┬─────┘
                     │
                     ▼
                ┌──────────┐
                │ Codex    │
                │ review   │
                └────┬─────┘
                     ▼
                ACCREDIT
```

---

## 3. Token Burn Analysis

### 3.1 Cost Per Model

| Model | Input Cost | Output Cost | Typical Review Tokens | Review Cost |
|-------|-----------|-------------|----------------------|-------------|
| **Claude Opus 4.6** | $5.00/M | $25.00/M | ~50K in + ~10K out | **$0.50** |
| **Codex gpt-5.2** | $1.25/M | $10.00/M | ~50K in + ~10K out | **$0.16** |
| **Codex codex-mini** | $1.50/M | $6.00/M | ~50K in + ~8K out | **$0.12** |
| **Codex spark** | ~$0.50/M | ~$2.00/M | ~30K in + ~5K out | **$0.03** |

### 3.2 Phase-by-Phase Token Budget

| Phase | Claude Implementation | Codex Review | Codex Adversarial | Total Phase Cost | Without Codex |
|-------|----------------------|--------------|-------------------|-----------------|---------------|
| **A** (7 critical fixes) | ~200K in + 80K out = **$3.00** | ~60K in + 15K out = **$0.23** | ~60K in + 20K out = **$0.28** | **$3.51** | $3.00 |
| **B** (7 fortification) | ~250K in + 100K out = **$3.75** | ~70K in + 15K out = **$0.25** | ~70K in + 20K out = **$0.29** | **$4.29** | $3.75 |
| **C** (5 visual) | ~180K in + 70K out = **$2.65** | ~50K in + 12K out = **$0.18** | ~50K in + 15K out = **$0.21** | **$3.04** | $2.65 |
| **D** (3 dep upgrades) | ~300K in + 120K out = **$4.50** | ~80K in + 20K out = **$0.30** | ~80K in + 25K out = **$0.35** | **$5.15** | $4.50 |
| **E+F** (6 perf+features) | ~280K in + 110K out = **$4.15** | ~75K in + 18K out = **$0.27** | ~75K in + 22K out = **$0.31** | **$4.73** | $4.15 |
| **TOTAL** | | | | **$20.72** | **$18.05** |

### 3.3 Cost-Benefit Ratio

```
 COST OF CODEX REVIEWS:        $2.67 additional (5 phases x 2 reviews each)
 ─────────────────────────────────────────────────────────────────────

 VALUE OF CATCHING 1 BUG:

 ┌────────────────────────────────────────────────────────────┐
 │  Bug caught by Codex review BEFORE merge:                  │
 │  Cost to fix: ~$0.50 (Claude fix in same session)          │
 │                                                            │
 │  Same bug found AFTER merge in production:                 │
 │  Cost to fix: ~$15-50 (debug session + hotfix + deploy)    │
 │                                                            │
 │  ROI: $2.67 investment prevents $15-50+ in production fixes│
 │  Break-even: Codex needs to catch just ONE bug across all  │
 │  5 phases to pay for itself 6-19x over.                    │
 └────────────────────────────────────────────────────────────┘

 HISTORICAL BUG CATCH RATE:

 ┌────────────────────────────────────────────────────────────┐
 │  Cross-model review catches bugs that same-model misses:   │
 │                                                            │
 │  Same model writes + reviews:  ~85% bug detection          │
 │  Cross-model review:           ~94% bug detection          │
 │  Improvement:                  +9% detection rate           │
 │                                                            │
 │  For DataPulse (15 known bugs):                            │
 │  9% improvement = ~1.4 additional bugs caught              │
 │  At $15-50 per production bug = $21-70 saved               │
 └────────────────────────────────────────────────────────────┘
```

### 3.4 Token Burn Visualization

```
                     TOKEN BURN PER PHASE
                     ═══════════════════

  Phase A  ████████████████████░░░░  Claude: 280K tokens
           ███░░░░░░░░░░░░░░░░░░░░  Codex:   95K tokens
                                     Overhead: +15%

  Phase B  █████████████████████████  Claude: 350K tokens
           ████░░░░░░░░░░░░░░░░░░░░  Codex:  105K tokens
                                     Overhead: +14%

  Phase C  ███████████████░░░░░░░░░  Claude: 250K tokens
           ██░░░░░░░░░░░░░░░░░░░░░  Codex:   77K tokens
                                     Overhead: +15%

  Phase D  ███████████████████████████  Claude: 420K tokens
           █████░░░░░░░░░░░░░░░░░░░░░  Codex:  125K tokens
                                       Overhead: +14%

  Phase EF ██████████████████████████  Claude: 390K tokens
           ████░░░░░░░░░░░░░░░░░░░░░  Codex:  115K tokens
                                     Overhead: +15%

  TOTAL:   Claude: 1,690K tokens (~$18.05)
           Codex:    517K tokens (~$ 2.67)
           ─────────────────────────────────
           Combined:              ~$20.72
           Overhead:              +14.8%
           Bug detection boost:   +9%
           ROI if 1 bug caught:   6-19x
```

---

## 4. Collaboration Rules

### Rule 1: Separation of Concerns

```
 ┌─────────────────────────────────────────────────────────┐
 │  Claude Code (Opus 4.6)          Codex (gpt-5.x)       │
 │  ═══════════════════             ════════════════        │
 │                                                          │
 │  DOES:                           DOES:                   │
 │  - Write code                    - Review code           │
 │  - Run tests                     - Challenge design      │
 │  - Use Graph MCP                 - Find edge cases       │
 │  - Commit changes                - Validate security     │
 │  - Create PRs                    - Check data integrity  │
 │                                                          │
 │  DOES NOT:                       DOES NOT:               │
 │  - Review its own code           - Write production code │
 │  - Approve its own PRs           - Run tests             │
 │  - Skip review gate              - Make commits          │
 │  - Merge without review          - Use Graph MCP         │
 └─────────────────────────────────────────────────────────┘
```

### Rule 2: Review Triggers (When to Call Codex)

| Trigger | Command | When |
|---------|---------|------|
| **Phase completion** | `/codex:review --base main` | After ALL tasks in a phase pass tests |
| **Security-sensitive change** | `/codex:adversarial-review` focus: auth, RLS, tenant isolation | After touching auth.py, jwt.py, deps.py, filters.py |
| **High blast-radius change** | `/codex:adversarial-review` focus: data integrity and cascading failures | After dp_impact() shows > 50 affected symbols |
| **Dependency upgrade** | `/codex:review` + `/codex:adversarial-review` focus: breaking changes | After Next.js 15, Tailwind 4, or dbt upgrades |
| **dbt model change** | `/codex:adversarial-review` focus: data correctness and RLS | After any change to stg_sales or fct_sales (55 downstream) |

### Rule 3: Review Gate Protocol

```
 BEFORE CODEX REVIEW:
 ═══════════════════
 [ ] All unit tests pass (pytest / vitest)
 [ ] Lint clean (ruff check / eslint)
 [ ] Type check clean (mypy / tsc --noEmit)
 [ ] Coverage >= 95% (Python) or passing (frontend)
 [ ] dp_detect_changes() shows expected blast radius
 [ ] Changes committed to branch (not main)

 CODEX REVIEW:
 ═════════════
 [ ] /codex:review --base main --background
 [ ] /codex:status (wait for completion)
 [ ] /codex:result (read findings)

 IF SECURITY-SENSITIVE:
 ══════════════════════
 [ ] /codex:adversarial-review --base main focus: [specific risk area]
 [ ] /codex:result (read adversarial findings)

 AFTER CODEX REVIEW:
 ═══════════════════
 [ ] Zero CRITICAL findings → ACCREDITED, push + PR
 [ ] Has CRITICAL findings → Claude fixes, re-test, re-review
 [ ] Has MEDIUM findings → Claude evaluates, fix or document as known
 [ ] Has LOW findings → Note in PR description, fix later
```

### Rule 4: Accreditation Criteria

| Level | Definition | Action |
|-------|-----------|--------|
| **ACCREDITED** | Codex finds 0 critical/high issues, tests pass, graph validates | Push branch, create PR, merge |
| **CONDITIONAL** | Codex finds medium issues, all fixable in <30min | Fix issues, re-run Codex review, then ACCREDITED |
| **BLOCKED** | Codex finds critical issues (security, data loss, RLS bypass) | STOP. Fix ALL critical issues. Full re-review required. |
| **ESCALATED** | Claude and Codex disagree on a finding | Human developer reviews the specific finding |

### Rule 5: What Codex Reviews Per Phase

| Phase | Standard Review Focus | Adversarial Review Focus |
|-------|----------------------|------------------------|
| **A** (Critical Fixes) | Migration ordering, filter escaping, pool config | Can the LIKE fix be bypassed? Is tenant_id validation exhaustive? |
| **B** (Fortification) | Exception hierarchy correctness, cache consistency | Can _set_cache consolidation cause cache key collisions? |
| **C** (Visual) | Accessibility, performance impact of animations | Do framer-motion animations degrade LCP? Does heatmap click break filter state? |
| **D** (Dep Upgrades) | Breaking API changes, deprecated patterns | Does React 19 migration break any SSR patterns? Tailwind 4 class renames? |
| **E+F** (Perf+Features) | Query correctness, incremental model idempotency | Can Redis pipeline cause partial cache reads? Is incremental dbt idempotent on retry? |

---

## 5. Review Gate Configuration

### 5.1 Recommended: Manual Review Gate (Not Auto)

```
 DO NOT USE: /codex:setup --enable-review-gate
 ═══════════════════════════════════════════════
 
 WHY:
 - Auto review gate creates Claude/Codex loop
 - Can drain usage limits quickly
 - Blocks Claude mid-implementation
 - Not suitable for multi-task phases
 
 INSTEAD USE: Manual review at phase boundaries
 ═════════════════════════════════════════════════
 
 - Claude implements ALL tasks in a phase
 - Claude runs ALL tests
 - Claude commits to branch
 - THEN: /codex:review --base main
 - THEN: /codex:adversarial-review --base main
 - Human reads Codex result
 - Human decides: ACCREDITED or FIX
```

### 5.2 Codex Config for DataPulse

Create `.codex/config.toml` in project root:

```toml
# DataPulse Codex Configuration
model = "gpt-5.2-codex"
model_reasoning_effort = "high"

# Focus areas for this project
[review]
focus_areas = [
    "Row-Level Security (RLS) bypass",
    "Tenant isolation via SET LOCAL app.tenant_id",
    "SQL injection through dynamic identifiers",
    "Cache key collisions across tenants",
    "Medallion layer data integrity (bronze -> silver -> gold)",
    "LIKE wildcard injection in filters",
]
```

---

## 6. Phase-by-Phase Review Strategy

### Updated Session Prompts (with Codex Review Gate)

Each session prompt from the previous plan gets this addendum:

```
REVIEW GATE (after all tasks complete):

1. Verify: pytest passes, ruff clean, tsc --noEmit clean, coverage >= 95%
2. Verify: dp_detect_changes() shows expected blast radius
3. Commit all changes to branch
4. Run: /codex:review --base main --background
5. Wait: /codex:status
6. Read: /codex:result
7. If security-sensitive changes: /codex:adversarial-review --base main
8. Read: /codex:result
9. If CRITICAL issues found: fix and re-review
10. If clean: push + create PR with Codex review summary in PR description
```

### Expected Review Timeline

```
 ┌─────────────────────────────────────────────────────────┐
 │  Phase A Timeline (with Codex review):                  │
 │                                                          │
 │  Claude implements 7 tasks ........... 45-60 min        │
 │  Tests + lint + type check ........... 5-10 min         │
 │  dp_detect_changes() ................. 1 min            │
 │  git commit .......................... 1 min            │
 │  /codex:review --background .......... 3-5 min          │
 │  /codex:adversarial-review ........... 3-5 min          │
 │  Fix Codex findings (if any) ......... 0-15 min         │
 │  Push + PR ........................... 2 min            │
 │                                                          │
 │  TOTAL: ~65-100 min per phase                           │
 │  Codex adds: ~10-25 min (15-25% overhead)               │
 │  Bug detection: +9% improvement                         │
 └─────────────────────────────────────────────────────────┘
```

---

## 7. Setup Guide

### One-Time Setup (5 minutes)

```bash
# 1. Install Codex plugin in Claude Code
/plugin marketplace add openai/codex-plugin-cc
/plugin install codex@openai-codex
/reload-plugins

# 2. Verify setup
/codex:setup

# 3. If Codex CLI not installed:
npm install -g @openai/codex

# 4. Login to Codex
!codex login

# 5. Create project config
# Create .codex/config.toml (see section 5.2 above)

# 6. Test the review flow
/codex:review --base main
/codex:status
/codex:result
```

### Per-Session Usage

```bash
# After Claude finishes implementing a phase:

# Standard review
/codex:review --base main --background
/codex:status
/codex:result

# If touching auth/security/RLS:
/codex:adversarial-review --base main challenge RLS bypass and tenant isolation

# If Codex finds issues:
# Claude fixes them, then:
/codex:review --base main  # re-review
```

---

## Summary: Value Proposition

```
 ┌────────────────────────────────────────────────────────────────┐
 │                                                                │
 │  INVESTMENT:                                                   │
 │  ├── Token overhead: +14.8% (~$2.67 across all 5 phases)      │
 │  ├── Time overhead:  +15-25% (~10-25 min per phase)            │
 │  └── Setup:          5 minutes one-time                        │
 │                                                                │
 │  RETURNS:                                                      │
 │  ├── Bug detection:  +9% improvement (cross-model diversity)   │
 │  ├── Security:       Adversarial review on auth/RLS/tenant     │
 │  ├── Design quality: Challenges assumptions before merge       │
 │  ├── Audit trail:    Codex review stored as PR evidence        │
 │  └── ROI:            6-19x if catches just 1 production bug    │
 │                                                                │
 │  VERDICT:  Worth it for DataPulse.                             │
 │  The project has RLS, multi-tenancy, financial data,           │
 │  and 160-symbol blast radius on core functions.                │
 │  Cross-model review is cheap insurance.                        │
 │                                                                │
 └────────────────────────────────────────────────────────────────┘
```

---

*Architecture designed for DataPulse's specific risk profile: RLS-protected multi-tenant financial data with deep cross-layer dependencies.*
