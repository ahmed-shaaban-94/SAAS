# POS Extraction — Phase 3 Observation Log

**Window:** 2026-05-01 → 2026-05-14
**Decision deadline:** 2026-05-14
**Master plan:** `docs/superpowers/plans/2026-05-01-pos-master-plan.md` §Phase 3
**Spec:** `docs/superpowers/specs/2026-04-30-pos-desktop-extraction-design.md` §6

---

## What this tracks

After Phase 1 (POS extraction) lands, we run the new system live for 2
weeks and measure whether the structural pain stopped. The decision at
the end (`docs/brain/decisions/2026-05-14-pos-extraction-outcome.md`)
picks one of three outcomes:

- **Calm** — keep extracted module, close initiative
- **Still noisy in pipeline** — another scoped fix; do NOT fork yet
- **Still noisy in code** — fork to a separate repo, with the recon +
  extraction work as the starting point

---

## Daily metrics

Log one row per day. Empty cells = not measured / no event.

| Date | Pipeline incidents | Time-to-rollout | Cashier tickets | P1 bugs | P2 bugs | Pain notes |
|---|---|---|---|---|---|---|
| 2026-05-01 | | | | | | Phase 1 PRs land today (#809 + #810 + #811). Window starts. |
| 2026-05-02 | | | | | | |
| 2026-05-03 | | | | | | |
| 2026-05-04 | | | | | | |
| 2026-05-05 | | | | | | |
| 2026-05-06 | | | | | | |
| 2026-05-07 | | | | | | |
| 2026-05-08 | | | | | | |
| 2026-05-09 | | | | | | |
| 2026-05-10 | | | | | | |
| 2026-05-11 | | | | | | |
| 2026-05-12 | | | | | | |
| 2026-05-13 | | | | | | |
| 2026-05-14 | | | | | | Decision deadline — write `docs/brain/decisions/2026-05-14-pos-extraction-outcome.md`. |

### Column definitions

- **Pipeline incidents** — silent fails / manual hotfixes during a
  release. Count distinct incidents (not commits).
- **Time-to-rollout** — minutes from `git push <tag>` to first cashier
  seeing the update on their installed app. Measured from release
  workflow timestamps + `pos.desktop_update_releases.created_at`.
- **Cashier tickets** — support inbox tickets specific to install /
  update / desktop crash. Count tickets, not messages.
- **P1 bugs** — production-blocker bugs surfaced in the day. P1 = a
  cashier cannot complete a transaction.
- **P2 bugs** — P2 = degraded UX but workflow completes. Receipt prints
  wrong, chip glitches, etc.
- **Pain notes** — qualitative. Anything that felt slow, broken, weird.
  These are signal even when the numbers are zero.

---

## Targets (per spec §6.1)

| Metric | Target |
|---|---|
| Pipeline incidents | 0 |
| Time-to-rollout | <60 min |
| Cashier tickets | <2 / week |
| P1 bugs | 0 |
| P2 bugs | ≤1 / week |
| Pain notes | qualitative — explicit ask at week 2 |

---

## How to fill this in

- Once a day. End of day or first thing next morning. Don't
  retroactively reconstruct — better to leave a cell blank than to
  guess.
- Pain notes are the most valuable field. If something felt off, write
  it down even if you don't know the cause.
- Skip a day if you genuinely didn't ship anything or hear from
  cashiers. Mark the row "skipped — no signal" rather than blanking
  it.

---

## Rollback signal

If by **2026-05-07** (mid-window) any of the targets is exceeded by 3×
or more, write a mid-window note and propose either:

- A targeted fix (if the cause is identifiable and small), or
- An early decision to fork (if the structural pain is back).

Don't wait for 2026-05-14 if the data is decisive earlier.
