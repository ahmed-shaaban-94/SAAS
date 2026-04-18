# 2026-04-17 — Pipeline Health reframe + Phase 2 Golden Path kickoff

**Tags:** [[strategy]] [[api]] [[frontend]] [[ci]] [[phase-2]]
**PRs:** [#394](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/394) · [#395](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/395) · [#396](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/396) · [#397](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/397)
**Issues queued:** #398 (epic) · #399–#405 (tasks)

## The turn

DataPulse pivoted today from "broad catalog of capabilities" posture toward a **narrower, sharper pharma operating product**. The `MASTER_CONVERSATION_REPORT.md` (a CEO + designer + manager joint diagnosis) landed and was translated into concrete shippable work:

1. A **Strategic Lever filter** — every future PR must declare which of four levers it moves: **clarity / trust / activation / monetization**. Enforced via PR template. Labels created. `docs/ROADMAP_FILTER.md` codifies it.
2. The top-nav was **narrowed**: "Data Quality" → "Pipeline Health" (reframed around freshness, completeness, trust), and "Data Lineage" was **demoted** out of primary nav into an admin/debug surface at `/lineage`.
3. An **API contract bug** that had been silently breaking the Pipeline Health run-detail panel was fixed. The backend returned `{items, total}` while the web hook expected `{run_id, checks, total_checks, passed, failed, warned}`. Flagged in the master report; now resolved with a new `QualityRunDetail` Pydantic model.
4. A **Phase 2 Golden Path sprint** was planned (`docs/superpowers/plans/2026-04-17-phase2-golden-path.md`) with success metric **TTFI < 5 minutes** and a 7-task backlog (#399–#405) tracked under epic #398.

## Why

- The CEO view (from the master report) flagged positioning as the primary weakness, not engineering. Narrowing Data Ops nav is the cheapest visible signal of that narrowing.
- The designer view wanted an emotional/operational framing over technical framing. "Pipeline Health" speaks to operators ("is my data safe to trust?"); "Data Quality" speaks to engineers ("did the check pass?"). Same backend, sharper framing.
- The manager view wanted "not now" discipline. The lever filter is a cheap, weekly-reviewable gate that forces sprawl to declare itself before it ships.
- The broken run-detail panel was a **Trust tax** — the very page we were elevating into primary nav was rendering `undefined` counters. Fix had to land atomically with the rename.

## How to apply going forward

- **Every PR body** must check a lever box. "None of the above" exists but demands justification in the review.
- **Weekly 30-min review:** what shipped → which lever? what's in-flight moving no lever → cut or park.
- **Data Lineage** stays as a capability but never again gets top-nav real estate unless it becomes *impact lineage* (which business KPI breaks if source X fails), not *model lineage* (which ref() depends on which ref()).
- **Pipeline Health** is now the canonical name. Internal `/quality` route preserved; URL migration deferred until someone has a reason.

## The engineering detour (lesson)

Shipping these 3 PRs revealed a **CI/npm lockfile trap** that nearly derailed the afternoon:

- `main` had a latent npm critical vulnerability (`protobufjs` RCE — GHSA-xq3m-2v4x-88gg) that started tripping the `Dependency Audit` gate on every PR after #393 merged. All 3 of our PRs inherited this red CI.
- First attempt: `npm audit fix` locally. Generated a lockfile my machine liked but CI rejected (`Missing: @swc/helpers@0.5.21 from lock file`). Root cause: my Node 24 / npm 11 resolved the tree differently from CI's Node 20 / npm 10.8.2.
- Second attempt: regenerated the lockfile with `npx npm@10.8.2 install --package-lock-only` on top of main's original lockfile, using **`package.json` overrides** (surgical) instead of `npm audit fix` (blunt, prunes transitives CI still needs).
- This worked: audit clean at `--audit-level=critical`, `npm ci` green.

**Rules learned:**
1. **Use the same npm major that CI uses** when regenerating lockfiles. `npx npm@X.Y.Z` is the cheapest way without nvm.
2. **Prefer `overrides` over `npm audit fix`** for vulnerable transitives. Overrides are a declarative contract in `package.json`; audit fix silently mutates the tree.
3. **Direct deps can't use `overrides`** — npm rejects with EOVERRIDE. For direct deps, bump `package.json` directly.
4. **Pre-existing main-branch red** masquerades as PR failure. Check main's latest Security run before assuming the PR broke CI.

Captured in: [[docs/brain/incidents]] (follow-up). Also worth a `global-lessons.md` entry since it applies to any npm project on Windows.

## What's parked

- Rollup + @sentry/nextjs high-sev advisories (need Sentry major upgrade — breaking change; Platform Engineer decision).
- LLM-backed first-insight card (Phase 8, not Phase 2).
- Android/Kotlin app — user signaled future pivot to React Native; DTO contract fix shipped anyway for continuity.
- Multi-dataset onboarding, connector marketplace, self-serve dashboard builder — all Phase 6+.

## Next session entry point

Start with `docs/superpowers/plans/2026-04-17-phase2-golden-path.md` and [[issue #399]]. The self-contained kickoff prompt lives in this decision note's sibling conversation — if lost, regenerate from the plan doc. Task 0 (baseline TTFI) has zero dependencies and is the cleanest first move.

## Linked work

- [[layers/api]] — contract fix in `src/datapulse/pipeline/quality.py`
- [[layers/frontend]] — nav narrowing in `frontend/src/lib/constants.ts`, `/quality` + `/lineage` page reframes
- [[modules/quality]] — new `QualityRunDetail` model, `get_run_detail` service method
- [[modules/brain]] — this note
- [[phase-2-golden-path]] — backlog epic
