# ADR 006 — Onboarding Step Taxonomy

**Date:** 2026-04-18  
**Status:** Accepted  
**Deciders:** Platform Engineer, Frontend Engineer  
**Parent follow-up:** [Phase 2 Follow-up #7](../../superpowers/plans/2026-04-17-phase2-followups.md#follow-up-7--reconcile-onboarding-step-taxonomies)

---

## Context

Two parallel "onboarding" systems exist in the codebase after Phase 2 shipped:

### System 1 — OnboardingWizard (setup, backend-persisted)

| | Value |
|---|---|
| Backend model | `datapulse.onboarding.models.ONBOARDING_STEPS` |
| Step list | `["connect_data", "first_report", "first_goal", "configure_first_profile"]` |
| Persistence | PostgreSQL (`public.onboarding` table) via `/api/v1/onboarding/*` |
| UI | `frontend/src/components/onboarding/onboarding-wizard.tsx` |
| Hook | `frontend/src/hooks/use-onboarding.ts` |
| Purpose | Guide new tenants through the one-time **account setup** flow |

### System 2 — OnboardingStrip (activation, localStorage-only)

| | Value |
|---|---|
| Step IDs | `["connect_data", "validate", "first_insight", "share"]` |
| Persistence | `localStorage["ttfi_onboarding_strip_v1"]` (frontend-only; Follow-up 6 will add backend sync) |
| UI | `frontend/src/components/dashboard/onboarding-strip.tsx` |
| Purpose | Show **TTFI milestones** on the dashboard; auto-advances via `ttfi:event` CustomEvents |

The two systems share the step name `"connect_data"` but mean different things:
- **Wizard** `connect_data` = "tenant has connected a data source (Excel import, connector, etc.)"  
- **Strip** `connect_data` = "user has hit the `/upload` page" (fires on `upload_started` event)

This ambiguity matters when:
1. Reading code — `ONBOARDING_STEPS.includes("connect_data")` could refer to either system.
2. Following Follow-up 6 (backend sync for the strip) — if the strip writes `connect_data` to the backend, it will shadow or conflict with the wizard's `connect_data` completion record.

---

## Decision

**Keep the two systems parallel and rename the strip step to remove the ambiguity.**

### Rationale

#### Merging is the wrong abstraction

The two systems are conceptually distinct:

| Dimension | Wizard | Strip |
|---|---|---|
| What it tracks | User **configuration** | User **activation** (TTFI milestones) |
| Step semantics | Setup actions (do X to configure the account) | Observation events (Y happened to you) |
| Triggering | Manual user interaction | Automatic via `ttfi:event` CustomEvents |
| Lifecycle | One-time, skippable | 14-day TTL, self-hides |
| Backend state | PostgreSQL, always synced | localStorage; backend sync in Follow-up 6 |

Merging would force an incompatible step taxonomy. The wizard's steps are imperative (`first_report`, `configure_first_profile`); the strip's are observational (`validate`, `first_insight`). There is no meaningful unified list.

#### Parallel is correct, disambiguation is cheap

Keeping them parallel preserves their individual semantics. The only action required is renaming the strip's ambiguous step ID to prevent future readers from conflating it with the wizard.

---

## Chosen rename

**Strip's `connect_data` step → `upload_data`**

Rationale: "upload" is more accurate than "connect" for what the step measures (the user has started a file upload, as evidenced by `upload_started` firing). The wizard's `connect_data` continues to mean "connected a data source" in the broader sense (file upload, connector, API, etc.).

### Migration note

Existing `localStorage["ttfi_onboarding_strip_v1"]` data may have `completed.connect_data` set. After this rename, the strip will look for `completed.upload_data` instead. Existing users will see the first step reset to pending — acceptable because:
1. The strip auto-hides after 14 days, so most active users will have it hidden already.
2. The `upload_started` event re-fires on next `/upload` visit, auto-completing the step again.
3. No backend data is affected.

---

## Consequences

### Positive

- Readers no longer need to check which system uses `"connect_data"` — the strip uses `"upload_data"`.
- Follow-up 6 (backend sync) can write `upload_data`, `validate`, `first_insight`, `share` without any collision risk with the wizard's `connect_data`, `first_report`, `first_goal`, `configure_first_profile`.
- The two systems remain independently evolvable.

### Negative

- Existing users who had step 1 auto-completed will see it reset until `upload_started` fires again (acceptable — see migration note above).
- Two parallel systems add cognitive load. Mitigated by clear naming and this ADR.

---

## Files changed

- `frontend/src/components/dashboard/onboarding-strip.tsx` — rename `StepId.connect_data` → `upload_data`; update `STEPS` array
- `frontend/src/__tests__/components/dashboard/onboarding-strip.test.tsx` — update `data-step="connect_data"` assertion → `data-step="upload_data"`

## Files unchanged

- `src/datapulse/onboarding/models.py` — `ONBOARDING_STEPS` stays as-is
- `frontend/src/hooks/use-onboarding.ts` — references wizard only; unchanged
- `localStorage["ttfi_onboarding_strip_v1"]` key — stays; only the field name inside the `completed` object changes
