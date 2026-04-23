# ADR 007 — Platform Matrix and React App Direction

**Date:** 2026-04-24
**Status:** Accepted
**Deciders:** Platform Engineer, Frontend Engineer
**Closes:** [#659](https://github.com/ahmed-shaaban-94/Data-Pulse/issues/659)

---

## Context

The DataPulse repo now carries four independent client surfaces — a Next.js
web dashboard, an Electron desktop POS, a Kotlin/Compose Android app, and a
Power BI workbook — plus the FastAPI backend they all consume. The repo
layout does not mark which of those surfaces is canonical, which is
accessory, and which is legacy.

The only written statement of the platform direction today lives in a brain
decision note ([2026-04-17 pipeline-health kickoff](../brain/decisions/2026-04-17-pipeline-health-and-phase-2-kickoff.md)):

> Android/Kotlin app — user signaled future pivot to React Native; DTO
> contract fix shipped anyway for continuity.

That one sentence, buried in a historical session log, is not enough to
align roadmap, QA, hiring, or shared-contract work. Issue [#658](https://github.com/ahmed-shaaban-94/Data-Pulse/issues/658)
(shared API contract package) and [#657](https://github.com/ahmed-shaaban-94/Data-Pulse/issues/657)
(mobile responsive regression coverage) both open with *"If the app
direction is React-based, then…"* — they are blocked on this decision
being explicit.

## Decision

We publish a **Platform Matrix** that assigns every shipping surface exactly
one status from a fixed vocabulary:

| Status | Meaning |
|---|---|
| **Canonical** | First-class surface. Shipped in every release. Covered by CI. Bugs here block releases. |
| **Supported** | Shipped as an accessory. Not a primary focus but stays functional. |
| **Incubating** | Declared direction. Not yet built or early-stage. Scoped in roadmap. |
| **Legacy** | Not actively developed. New work routes to the replacement surface. Removal planned. |

### Surface assignments (2026-04-24)

| Surface | Path | Stack | Status |
|---|---|---|---|
| Backend API | `src/datapulse/` | FastAPI + Python 3.12 | **Canonical** |
| Web dashboard | `frontend/` | Next.js 15 + React | **Canonical** |
| Desktop POS | `pos-desktop/` | Electron wrapping `frontend/` | **Canonical** |
| Power BI workbook | `powerbi/` | DAX + PBIT | **Supported** |
| Native mobile app | _(not in repo yet)_ | **React Native** | **Incubating** |
| Android legacy app | `android/` | Kotlin + Jetpack Compose | **Legacy** |

### The React app direction

The next native mobile surface will be **React Native**, not a continuation
of the existing Kotlin/Compose codebase. Rationale:

1. **Shared domain model.** React Native can consume the same generated
   TypeScript contracts that the web surface will use after [#658](https://github.com/ahmed-shaaban-94/Data-Pulse/issues/658)
   lands. Kotlin cannot without a second code-generation pipeline.
2. **One engineering muscle.** The frontend team is already a React team.
   Shipping a second React surface is an extension of that muscle, not a
   second specialization.
3. **Shared responsive foundation.** A stabilized mobile-viewport Playwright
   lane ([#657](https://github.com/ahmed-shaaban-94/Data-Pulse/issues/657))
   pays off twice — once for the web dashboard's phone layout, and again
   as the layout contract a React Native shell inherits.

Consequence: `android/` becomes `Legacy`. No new features ship there. The
directory is kept in the repo for existing users and to preserve domain
knowledge that will inform the React Native build.

## Rules

1. **No new `Incubating`→`Canonical` promotions without an ADR.** Changing a
   surface's status requires amending this document (or superseding it).
2. **`Legacy` surfaces don't get top-of-stack fixes.** Unless a security
   issue forces it, new behaviour lands in the canonical surface and the
   legacy surface is left frozen.
3. **New route, new feature, new dashboard page — always ships on the
   canonical surface first.** POS variants come second, Power BI
   accessories third.
4. **React Native scaffolding lives under `mobile/`** when it lands, to
   avoid the directory-name collision with `android/` and make the
   surface change visible in `git log`.

## Consequences

- **Unblocks [#658](https://github.com/ahmed-shaaban-94/Data-Pulse/issues/658).**
  Shared-contract tooling can target TypeScript confidently because every
  canonical and incubating client consumes TypeScript.
- **Unblocks [#657](https://github.com/ahmed-shaaban-94/Data-Pulse/issues/657).**
  Mobile responsive work is scoped against the Next.js web shell today and
  reused by React Native later.
- **Creates a maintenance debt.** `android/` still compiles and ships as
  Legacy; a follow-up issue should set a sunset date (see "Follow-up").
- **Surfaces the Power BI workbook as non-primary.** Future requests to
  add DAX-heavy features get routed back to the canonical dashboard
  unless the workbook is materially cheaper.

## Follow-up

- Open a tracking issue to sunset `android/` once React Native scaffolding
  lands. Target: first React Native release replaces the Play Store
  listing; Kotlin source is archived to a `legacy-android` branch.
- When the shared-contract package ([#658](https://github.com/ahmed-shaaban-94/Data-Pulse/issues/658))
  ships, add a link to it from this ADR so the contract consumer list is
  discoverable from the platform decision.
