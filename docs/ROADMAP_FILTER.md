# Roadmap Filter — Four Strategic Levers

> Every proposed ticket, PR, or sprint item must move at least one of these four levers.
> If it doesn't, it is "not now." This filter is the recurring planning gate.

Source: [MASTER_CONVERSATION_REPORT.md](./superpowers/specs/MASTER_CONVERSATION_REPORT.md)

## The Four Levers

### 1. Clarity
Narrows the product story, sharpens positioning, reduces user-visible surface area.

Examples that qualify:
- Renaming a feature to match the pharma wedge
- Removing a top-nav item that dilutes focus
- Consolidating duplicate pages
- Rewriting landing copy to be outcome-first

Examples that do **not** qualify:
- Adding a new module "because we can"
- Generic cross-industry messaging
- Feature polish on low-priority pages

### 2. Trust
Real proof, reliability, data confidence, buyer-readable signals.

Examples that qualify:
- Fixing a broken detail page (even if "cosmetic")
- Source freshness / last-refreshed badges on dashboards
- Replacing placeholder logos with real pilot references
- Degraded-state UX (visible retry, honest error states)

Examples that do **not** qualify:
- Implied proof ("trusted by thousands")
- Hidden reliability work with no user-visible surface

### 3. Activation
The upload-to-insight path. First-value moments. Golden path.

Examples that qualify:
- Import wizard improvements
- Empty-state coaching on first load
- "Here's one thing to act on today" insight card
- Reducing clicks from login to executive dashboard

Examples that do **not** qualify:
- Secondary features that assume the user is already activated
- Admin tooling

### 4. Monetization
Pilot/demo flow, billing readiness, conversion machinery.

Examples that qualify:
- Productionized lead capture
- Reusable demo tenant (seed data + reset)
- Pilot package definition with acceptance criteria
- Aligning CTAs with real commercial state

Examples that do **not** qualify:
- Free-trial flows before the product demos well
- Fake pricing pages that over-promise

---

## How to Apply

### On every ticket
Tag with one of: `lever:clarity`, `lever:trust`, `lever:activation`, `lever:monetization`.

### On every PR
The PR template's "Strategic Lever" section must be filled in.

### Weekly review (30 min)
- What shipped this week? Which lever?
- What's proposed next week? Which lever?
- What's in-flight but moves no lever? Cut or park.

### When in doubt
If a proposed item doesn't cleanly fit a lever, it is probably "not now." Park it in a "later" lane and revisit in 4 weeks.

## Current Priority Order (2026-04-17)

Per [MASTER_CONVERSATION_REPORT.md](./superpowers/specs/MASTER_CONVERSATION_REPORT.md) and the follow-up brainstorm:

1. **Trust** — Pipeline Health reframe + Data Lineage demote (active sprint)
2. **Activation** — Golden Path sprint (next 3 weeks)
3. **Monetization** — Commercial readiness kit (parallel)
4. **Clarity** — Operations Suite cohesion (after Golden Path)

External-surface expansion (mobile, Power BI, reseller) is **parked** until pilot traction is real.
