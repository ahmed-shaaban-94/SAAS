# POS Terminal Design Handoff — Repo Reference

This folder contains the **authoritative high-fidelity design handoff** for the
DataPulse Pharmacy POS terminal. It was produced outside this repo and imported
here on 2026-04-19 for reference during implementation.

## Status

**Design reference, not production code.** The JSX files in `frames/pos/` are
React prototypes demonstrating the intended look, behavior, keyboard model, and
copy. The implementation task is to **recreate these designs in the Next.js
frontend** using existing patterns (Tailwind, next-intl, SWR, NextAuth), NOT
to copy-paste the JSX.

## What lives here

| File | Purpose |
|------|---------|
| `README.md` | Authoritative design spec — tokens, typography, keyboard model, screen behaviors, copy |
| `POS Terminal v2.html` | Runnable HTML entry point that renders the React prototypes — open in a browser to see the live design |
| `frames/pos/*.jsx` | React component prototypes for each screen (terminal, drugs, sync, shift, modals, shell, etc.) |
| `_NOTE.md` | This file |

## When to read this

- **Before starting any new POS frontend work.** Read `README.md` §Screens / Views
  and §Design Tokens at minimum to match colors, typography, spacing, shadows.
- **When picking a keyboard shortcut.** The handoff has a full F-key map
  (F1–F12) — don't invent new ones.
- **When naming CSS classes or variables.** The handoff uses CSS custom
  properties like `--accent`, `--ink-3`, `--line-strong`. Match them when we
  land the design token system (planned PR 1 of the design recreation epic).

## Planned recreation PRs

The implementation plan lives at `docs/plans/sprints/2026-04-19-pos-design-recreation.md`
(to be written). Short version:

1. Design tokens + Google Fonts + TopBar shell
2. Terminal v2 (scan bar + Quick Pick + keypad + payment tiles + cash denominations strip)
3. Drugs tab (new screen — searchable inventory with add-to-cart)
4. Invoice modal + Stocktaking modal (both printable A4)
5. Sync Issues + Shift Close redesign
6. Voucher/Promo/Insurance modals (supersede current Phase 1b voucher modal)

## Known divergences to resolve during recreation

- **Accent color:** handoff uses `#00c7f2` (bright cyan). Current project uses
  `#00C8B4` (teal). They are close; PR 1 picks one and commits repo-wide.
- **Fonts:** handoff mandates Fraunces italic (display), JetBrains Mono
  (numbers), IBM Plex Sans Arabic (Arabic), Inter (UI). Project already has
  `next/font` infrastructure; PR 1 adds the three missing families.
- **Inline styles vs Tailwind:** the JSX prototype uses inline `style={{}}`
  objects heavily. Production code should translate these to Tailwind utility
  classes or CSS modules, referencing the tokens from PR 1.

## Authorship & license

Authored externally. License terms pending confirmation from the author before
any portion of the prototype code is shipped verbatim. The **specifications**
(tokens, keyboard model, copy) are reference material and safe to implement
from.
