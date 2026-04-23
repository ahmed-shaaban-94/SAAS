# DataPulse Platform Matrix

> **Single source of truth for which surfaces ship, which are experimental,
> and which are being retired.** Authoritative over anything README or
> brain notes say. Updated via [ADR 007](adr/007-platform-matrix.md).

## Surfaces

| Surface | Path | Stack | Status | Notes |
|---|---|---|---|---|
| Backend API | [`src/datapulse/`](../src/datapulse/) | FastAPI + Python 3.12 | **Canonical** | Single runtime contract; every client consumes it |
| Web dashboard | [`frontend/`](../frontend/) | Next.js 15 + React 18 + TypeScript | **Canonical** | Primary product surface |
| Desktop POS | [`pos-desktop/`](../pos-desktop/) | Electron wrapping `frontend/` | **Canonical** | Partner-owned lane; wraps the web dashboard for pharmacy counters |
| Power BI workbook | [`powerbi/`](../powerbi/) | DAX + PBIT | **Supported** | Ships alongside the platform as an accessory; not a primary surface |
| Native mobile app | _`mobile/` (planned)_ | **React Native** | **Incubating** | Declared direction. Reuses the web dashboard's TS contracts and responsive layout. Not yet scaffolded. |
| Android legacy app | [`android/`](../android/) | Kotlin + Jetpack Compose | **Legacy** | Frozen; new work routes to React Native. Sunset tracked separately once RN scaffolding lands. |

## Status vocabulary

| Status | What it means for roadmap / QA / bugs |
|---|---|
| **Canonical** | Every feature lands here first. CI gates protect it. Release-blocking. Sized against the majority of engineering capacity. |
| **Supported** | Accessory surface. Bug fixes, but not the primary target for new features. Quarterly health-check at minimum. |
| **Incubating** | Declared but not built, or early-stage. Scoped on the roadmap with explicit owner and exit criteria for promotion to Canonical. |
| **Legacy** | Not actively developed. New feature requests are rejected and routed to the replacement surface. Only security patches. A sunset plan exists. |

## The React direction (short version)

Future mobile work ships as **React Native** under `mobile/`. It will
consume the same generated TypeScript contracts that the web dashboard
moves to in [#658](https://github.com/ahmed-shaaban-94/Data-Pulse/issues/658),
and inherits the responsive layout work from [#657](https://github.com/ahmed-shaaban-94/Data-Pulse/issues/657).
The existing Kotlin/Compose app (`android/`) is Legacy — it continues
to build but receives no new features. See
[ADR 007](adr/007-platform-matrix.md) for the full rationale.

## When to update this document

- A surface changes status (Incubating → Canonical, Canonical → Legacy, …).
- A new surface is added or an existing one is removed.
- The React app direction changes.

Any of those triggers an ADR (supersede ADR 007, don't edit this doc in
isolation) **and** a corresponding update here.

## Cross-refs

- [ADR 007 — Platform Matrix and React App Direction](adr/007-platform-matrix.md) — the decision record.
- [ARCHITECTURE.md](ARCHITECTURE.md) — system architecture; depends on this doc for surface assignments.
- [`docs/brain/decisions/2026-04-17-pipeline-health-and-phase-2-kickoff.md`](brain/decisions/2026-04-17-pipeline-health-and-phase-2-kickoff.md) — earlier informal mention of the React pivot; superseded by ADR 007.
