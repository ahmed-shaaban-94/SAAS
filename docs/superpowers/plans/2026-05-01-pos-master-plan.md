# POS Clean Extraction — Master Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Pre-existing per-Phase plans (`2026-04-30-pos-pipeline-phase-2.md`, `2026-04-30-pos-extraction-phase-1.md`) are absorbed/superseded by this master document; the recon report at `docs/superpowers/recon/2026-04-30-pos-extraction-recon.md` is the ground-truth input.

**Goal:** Extract POS into a focused, lint-clean, dead-code-free `pos-desktop/src/` module with a single Zustand cart store, a Vite-built static React renderer (no embedded Next.js), and a typed OpenAPI client — without breaking any of the 160 existing tests or any user-facing flow.

**Architecture:** Four sequential sub-PRs, each independently mergeable, each with TDD gates. Phase 2-B catches up the still-pending pipeline-standardization commits to main. Phase 1's recon (Task 1) is already done — this plan picks up at Task 2 with concrete per-step task lists derived from the recon. Phase 3 is observation-only with a hard 2026-05-14 decision deadline.

> **REVISION 2026-05-01 (post-execution learning):** The original plan split Sub-PR 1 (move) and Sub-PR 2 (Vite) — but moving POS sources OUT of `frontend/src/` while Next.js still serves them creates cross-package npm resolution headaches (React, Zustand, lucide-react have no node_modules path from `pos-desktop/src/`). Spec §5 says Sub-PR 1 must "still produce a runnable Electron app". Folding the move into Sub-PR 2 (where pos-desktop gets its own `package.json` with renderer deps for Vite anyway) keeps Sub-PR 1 small, atomic, and zero-risk. **Sub-PR 1 (Task 2)** is now scoped to: dead-code drop (DONE) + POS-only CSS extract + line-level dead-export cleanup. **Sub-PR 2 (Task 3)** expands to: Vite migration + add renderer deps to pos-desktop + git-mv POS code + codemod imports + drop POS from frontend/ + Electron `loadFile` switch.

**Tech Stack:** Vite (replaces Next.js for renderer), React Router (`createHashRouter` for Electron `loadFile`), Zustand (single cart store), `openapi-typescript` (typed API), TypeScript 5, Electron, electron-builder, FastAPI (existing backend, untouched), pytest, Vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-04-30-pos-desktop-extraction-design.md`
**Recon:** `docs/superpowers/recon/2026-04-30-pos-extraction-recon.md`

---

## File Structure (target after all phases)

```
Data-Pulse/
├── frontend/                           ← dashboard only; POS gone
│   └── src/
│       ├── app/(dashboard)/
│       └── app/globals.css             ← --pos-* tokens removed
├── pos-desktop/                        ← focused, owns its build
│   ├── src/
│   │   ├── pages/                      ← was frontend/src/app/(pos)/  (8 routes)
│   │   ├── components/                 ← was frontend/src/components/pos/  (~25 files)
│   │   ├── hooks/                      ← was frontend/src/hooks/use-pos-*  (12 files)
│   │   ├── store/cart-store.ts         ← THE one Zustand cart store
│   │   ├── contexts/                   ← (deleted after Task 4)
│   │   ├── lib/                        ← was frontend/src/lib/pos/*  (5 files)
│   │   ├── types/pos.ts
│   │   ├── api/
│   │   │   ├── client.ts               ← auth + Idempotency-Key + retry
│   │   │   ├── types.ts                ← generated from contracts/openapi.json
│   │   │   └── endpoints/              ← typed wrappers per resource
│   │   ├── styles/globals.css          ← --pos-* tokens + 40 rule blocks (extracted)
│   │   └── electron/                   ← unchanged: main, preload, IPC, updater, sync
│   ├── vite.config.ts                  ← NEW
│   ├── index.html                      ← NEW
│   ├── electron-builder.yml            ← extraResources/nextjs block deleted
│   ├── package.json                    ← bumped to 3.0.0 (clean-break signal)
│   └── tsconfig.json
├── contracts/openapi.json              ← shared, unchanged
└── docs/superpowers/
    ├── plans/2026-05-01-pos-master-plan.md   ← THIS FILE
    └── recon/2026-04-30-pos-extraction-recon.md
```

---

## Execution model

| Phase / Task | Agent dispatch | Model | Parallel? |
|---|---|---|---|
| Phase 0 cleanup | inline (this session) | Opus 4.7 | n/a |
| Phase 2-B Sub-task A (open PR) | inline | Opus 4.7 | n/a |
| Phase 1 Task 1 (recon) | DONE | — | — |
| Phase 1 Task 1.5 (dead-code scan) | 3× `Explore` agents | Sonnet 4.6 | YES |
| Phase 1 Task 2 (mechanical move) | single executor | Sonnet 4.6 | no |
| Phase 1 Task 2 review | `code-reviewer` | Sonnet 4.6 | n/a |
| Phase 1 Task 3 (Vite migration) | single executor | Sonnet 4.6 | no |
| Phase 1 Task 3 review | `code-reviewer` | Sonnet 4.6 | n/a |
| Phase 1 Task 4 (cart store design) | `feature-dev:code-architect` | **Opus 4.7** | n/a |
| Phase 1 Task 4 (cart store impl) | single executor + `tdd-guide` | Sonnet 4.6 | no |
| Phase 1 Task 4 review | `code-reviewer` | Sonnet 4.6 | n/a |
| Phase 1 Task 5 (typed API client) | single executor | Sonnet 4.6 | no |
| Phase 3 (observation) | inline metrics, no agents | — | n/a |

This master plan stays pinned in the executor's context across tasks. Each task ends with a commit and a stop-point for review.

---

## Phase 0: Cleanup — DONE

- [x] Aborted in-progress merge on `feat/pos-738-paymob-gateway-v2` (branch dead per 2026-04-26 audit)
- [x] Fast-forwarded `main` to latest (`937dbbfa`)
- [x] Created branch `feat/pos-extraction-phase-1` off main
- [x] Cherry-picked `70bcfb3a` (recon doc) onto branch
- [x] This master plan committed

PR #738 (`feat/pos-738-paymob-gateway-v2`) will be closed without merging — separate operator step.

---

## Phase 2-B: Pipeline standardization completion (~30 min)

The branch `feat/pos-pipeline-phase-2` has 6 commits ahead of main (8 files, +634 LOC) that are ready to PR — endpoint route, workflow auto-register step, tag/version assert, code-signing rotation docs, rate-limit. The plan at `docs/superpowers/plans/2026-04-30-pos-pipeline-phase-2.md` already specifies these tasks. Phase 2-B here is the **delivery** wrapper: open the PR, get CI green, merge.

### Task 2-B.1: Open PR for `feat/pos-pipeline-phase-2`

**Files:** none modified — git/CI work only.

- [ ] **Step 1: Verify branch is up to date with main**

```bash
git fetch origin
git rev-list --count origin/main..origin/feat/pos-pipeline-phase-2
```
Expected: `6` (or higher; should not be `0`).

- [ ] **Step 2: Open PR**

```bash
gh pr create \
  --base main \
  --head feat/pos-pipeline-phase-2 \
  --title "feat(pos): Phase 2-B — pipeline standardization completion" \
  --body "$(cat <<'EOF'
## Summary
Delivers the remaining Phase 2 work from `docs/superpowers/specs/2026-04-30-pos-desktop-extraction-design.md` §4:

- POST /api/v1/pos/admin/desktop-releases endpoint (RBAC-gated, idempotent)
- Workflow `auto-register` step calling the endpoint after publish
- Tag/version assertion (kills tonight's silent-fail mode permanently)
- Rate-limit /admin/desktop-releases at 10/min
- Code-signing cert + POS_ADMIN_TOKEN rotation cadence docs

Phase 2-A (models + service) was merged via #803/#804/#805. This is the routing/workflow/docs layer.

## Test plan
- [ ] CI green
- [ ] Deliberate-mismatch test: push tag pos-desktop-v0.0.0-test against package.json `2.0.0` — assert workflow fails fast with recovery message
- [ ] Idempotent re-call: hit the new endpoint twice with same version — assert single row in pos.desktop_update_releases
- [ ] Rate-limit verified: 11th request inside 60s gets HTTP 429
EOF
)"
```
Expected: PR URL printed.

- [ ] **Step 3: Wait for CI green, request review, merge**

This step is operator-driven (you handle the merge button). Once merged, Phase 2-B is complete.

- [ ] **Step 4: Verify Phase 2 acceptance criteria from spec §10**

Per spec §10 Phase 2:
- [ ] Workflow fails loudly if tag ≠ package.json version (covered by step 3 test plan)
- [ ] Endpoint registers a rollout row, idempotent
- [ ] Workflow calls the endpoint after publish; release auto-registers
- [ ] Code-signing produces Valid signature on next release (separate operator step — set `CSC_LINK` + `CSC_KEY_PASSWORD` GitHub secrets)
- [ ] Tag-push end-to-end: published release + DB row + signed installer

If all check, Phase 2-B is **DONE** and Phase 1 Task 1.5 begins.

---

## Phase 1: Extraction (the main event)

### Task 1: Recon — DONE

Recon report at `docs/superpowers/recon/2026-04-30-pos-extraction-recon.md`. Key findings (verbatim from report):

- **0 inbound imports** non-POS → POS — extraction is mechanically safe.
- **67 POS files** import from 22 non-POS modules. Cross-cuts:
  - `@/lib/utils` (43×) — **keep external** (dashboard-wide).
  - `@/types/pos` (13×), `@/lib/api-client` (11×), `@/lib/auth-bridge` (5×), `@/lib/pos/*` (10×) — **move with POS**.
  - `@/components/{empty-state, auth-provider, branding, error-boundary, ui/toast}`, generic `@/hooks/*` — **keep external**.
  - `@/hooks/use-pos-terminal` — **move with POS** (POS-named hook outside the `use-pos-*` glob).
- **160 tests** (71 frontend + 23 Electron + 66 backend) must stay green.
- **No POS-only public assets** — only Next.js-specific pattern is `next/font/google` (single migration point).
- **55 POS-only CSS tokens** + **40 rule blocks** in `frontend/src/app/globals.css` (lines 1086–1124, 1129–1264, 1295–1517) to extract.
- **2 cart stores** (`pos-cart-store.ts` Zustand + `pos-cart-context.tsx` Context) → unify into one Zustand store.

### Task 1.5: Dead-code scan (NEW — supplements recon)

The recon mapped what to keep & move; it did NOT enumerate dead code within POS itself. The user's "without many bugs and noise" intent demands an explicit drop list. Three parallel `Explore` agents produce it.

**Files this task PRODUCES:**
- Create: `docs/superpowers/recon/2026-05-01-pos-deadcode-scan.md`

**Files this task TOUCHES:** none in source code (read-only).

- [ ] **Step 1: Dispatch three parallel `Explore` subagents (Sonnet 4.6)**

Send a single message containing three `Agent` calls (subagent_type=Explore, model=sonnet) so they run concurrently:

**Subagent A — unused-exports:**

> Read-only analysis. In `Data-Pulse/`, find every export from these directories that has zero importers anywhere in the repo: `frontend/src/components/pos/**`, `frontend/src/hooks/use-pos-*.ts`, `frontend/src/lib/pos/**`, `frontend/src/store/pos-cart-store.ts`, `frontend/src/contexts/pos-cart-context.tsx`, `frontend/src/types/pos.ts`. For each unused export, report `<file>:<line> :: <export-name>`. Skip exports re-exported via barrel files unless the barrel itself has zero importers. Output under 600 words.

**Subagent B — fix-on-fix bug-trail:**

> Read-only git-history analysis on `Data-Pulse/`. For files matching `frontend/src/{components,hooks,lib,store,contexts}/pos*` and `frontend/src/app/(pos)/**`, find files with ≥3 commits in the last 14 days. For each, list the commit subjects (one line each, oldest first). Pay special attention to commit subjects matching `fix:`, `hotfix:`, `revert:`, or "fix [previous fix]". This identifies hot-spot files where bug-on-bug accumulation suggests refactor-or-rewrite. Output under 500 words.

**Subagent C — orphan-tests:**

> Read-only analysis on `Data-Pulse/`. Find every test file under `frontend/src/__tests__/**` and `frontend/e2e/**` that imports from POS code (`@/components/pos/**`, `@/hooks/use-pos-*`, `@/store/pos-cart-store`, `@/contexts/pos-cart-context`, `@/lib/pos/**`, `@/types/pos`). For each, list (a) which POS source files it covers, (b) when it was last modified (`git log -1 --format=%ai`), (c) whether the source files still exist. Flag any test whose covered source no longer exists — those are orphans to delete. Output under 600 words.

- [ ] **Step 2: Collate the three reports into the dead-code scan file**

Save as `docs/superpowers/recon/2026-05-01-pos-deadcode-scan.md`. Sections: §A unused-exports, §B fix-on-fix hot-spots, §C orphan-tests, §D consolidated drop list (Claude's synthesis: file-paths to delete in Task 2).

- [ ] **Step 3: User review gate**

Show the consolidated drop list (§D) before deleting anything. If user flags an item as "false positive", remove it from the drop list and continue.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/recon/2026-05-01-pos-deadcode-scan.md
git commit -m "docs(recon): POS dead-code scan — exports, fix-on-fix, orphan tests"
```

---

### Task 2: Cleanup — Sub-PR 1 (revised scope, 0.5 day)

> **REVISED 2026-05-01:** Sub-PR 1 no longer includes the file move. The move (Tasks 2.2, 2.4, 2.5) is folded into Sub-PR 2 (Task 3) where pos-desktop gets its own renderer deps for Vite. Sub-PR 1 now ships: dead-code drop (Task 2.3 — DONE) + POS-only CSS extract (Task 2.6) + line-level dead-export cleanup via `ts-prune` + smoke + PR. Tasks 2.2/2.4/2.5 below are kept for reference but **execute under Task 3 instead**.

**Goal:** Drop dead code, extract POS-only CSS to a future-ready location (still under `frontend/src/styles/pos-globals.css` for now — moves to `pos-desktop/src/styles/` in Sub-PR 2), clean up unused exports flagged by recon. Existing tests pass unchanged. POS code stays in `frontend/src/` until Sub-PR 2 atomically moves + Vite-migrates it.

**Files this task PRODUCES:**
- Create: `pos-desktop/src/pages/{terminal,checkout,shift,drugs,history,pos-returns,sync-issues}/page.tsx` (moved)
- Create: `pos-desktop/src/components/**` (moved)
- Create: `pos-desktop/src/hooks/use-pos-*.ts` (moved)
- Create: `pos-desktop/src/store/cart-store.ts` (moved from `pos-cart-store.ts`)
- Create: `pos-desktop/src/contexts/pos-cart-context.tsx` (moved — deleted in Task 4)
- Create: `pos-desktop/src/lib/{format-drug-name,ipc,offline-db,print-bridge,scanner-keymap}.ts` (moved)
- Create: `pos-desktop/src/types/pos.ts` (moved)
- Create: `pos-desktop/src/styles/globals.css` (extracted POS-only tokens + rule blocks)
- Create: `pos-desktop/tsconfig.json` (paths alias `@pos/*` → `./src/*`)

**Files this task MODIFIES:**
- `frontend/src/app/globals.css` — drop lines 1086–1124, 1129–1264, 1295–1517
- `frontend/tsconfig.json` — drop `@/components/pos/*`, `@/hooks/use-pos-*` if explicitly aliased; add `@pos/*` external alias if codemod uses cross-package imports (decided in step 3)
- All 67 POS files — codemod-rewritten imports

**Files this task DELETES:**
- Files on Task 1.5 §D drop list

#### Task 2.1: Pre-flight — verify clean baseline

- [ ] **Step 1: Confirm full test suite green on current branch**

```bash
cd frontend && npm run test -- --run 2>&1 | tail -5
cd ../pos-desktop && npm run test 2>&1 | tail -5
cd .. && pytest -m unit -x -q 2>&1 | tail -5
```
Expected: 0 failures across all three suites. If any failures, FIX THEM FIRST — do not start a move on a red baseline.

- [ ] **Step 2: Snapshot the test count for parity check at end of task**

```bash
cd frontend && npm run test -- --run --reporter=verbose 2>&1 | grep -cE "✓|PASS"
```
Record the number. The same command at end of Task 2 must produce ≥ this number.

#### Task 2.2: Set up `pos-desktop/src/` skeleton + path alias

- [ ] **Step 1: Create the target directory tree**

```bash
mkdir -p pos-desktop/src/{pages,components,hooks,store,contexts,lib,types,styles,api}
mkdir -p pos-desktop/src/components/{terminal,receipts,shift,sync,drugs}
```

- [ ] **Step 2: Create `pos-desktop/tsconfig.json`**

```json
{
  "extends": "../frontend/tsconfig.json",
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@pos/*": ["./src/*"],
      "@shared/utils": ["../frontend/src/lib/utils.ts"],
      "@shared/components/*": ["../frontend/src/components/*"],
      "@shared/hooks/*": ["../frontend/src/hooks/*"]
    },
    "rootDirs": ["./src", "./electron"],
    "jsx": "preserve"
  },
  "include": ["src/**/*", "electron/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

- [ ] **Step 3: Verify the alias resolves in a smoke file**

Create `pos-desktop/src/index.ts` containing `export const VERSION = "phase-1-skeleton";`. Run:
```bash
cd pos-desktop && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Commit the skeleton**

```bash
git add pos-desktop/tsconfig.json pos-desktop/src/index.ts
git rm pos-desktop/src/index.ts  # remove smoke file before commit body
git add -u
git commit -m "feat(pos-desktop): scaffold src/ tree + tsconfig path aliases (Phase 1 Task 2.2)"
```

#### Task 2.3: Apply the dead-code drop list

- [ ] **Step 1: For each file on Task 1.5 §D drop list, `git rm`**

```bash
# Example — actual list comes from Task 1.5 §D output
git rm frontend/src/components/pos/<orphan>.tsx
git rm frontend/src/__tests__/components/pos/<orphan>.test.tsx
# ... repeat per drop-list entry
```

- [ ] **Step 2: Run the test suite to confirm no regression**

```bash
cd frontend && npm run test -- --run 2>&1 | tail -5
```
Expected: 0 failures. The dead code shouldn't have been imported by anything.

- [ ] **Step 3: Commit**

```bash
git commit -m "chore(pos): drop dead code per Task 1.5 §D drop list (Phase 1 Task 2.3)"
```

#### Task 2.4: `git mv` the keep list

- [ ] **Step 1: Move pages**

```bash
git mv frontend/src/app/\(pos\)/terminal/page.tsx pos-desktop/src/pages/terminal.tsx
git mv frontend/src/app/\(pos\)/checkout/page.tsx pos-desktop/src/pages/checkout.tsx
git mv frontend/src/app/\(pos\)/shift/page.tsx pos-desktop/src/pages/shift.tsx
git mv frontend/src/app/\(pos\)/drugs/page.tsx pos-desktop/src/pages/drugs.tsx
git mv frontend/src/app/\(pos\)/history/page.tsx pos-desktop/src/pages/history.tsx
git mv frontend/src/app/\(pos\)/pos-returns/page.tsx pos-desktop/src/pages/pos-returns.tsx
git mv frontend/src/app/\(pos\)/sync-issues/page.tsx pos-desktop/src/pages/sync-issues.tsx
git mv frontend/src/app/\(pos\)/layout.tsx pos-desktop/src/pages/layout.tsx
```

- [ ] **Step 2: Move components**

```bash
git mv frontend/src/components/pos/* pos-desktop/src/components/
```

- [ ] **Step 3: Move hooks**

```bash
git mv frontend/src/hooks/use-pos-branding.ts pos-desktop/src/hooks/
git mv frontend/src/hooks/use-pos-cart.ts pos-desktop/src/hooks/
git mv frontend/src/hooks/use-pos-checkout.ts pos-desktop/src/hooks/
git mv frontend/src/hooks/use-pos-customer-lookup.ts pos-desktop/src/hooks/
git mv frontend/src/hooks/use-pos-drug-clinical.ts pos-desktop/src/hooks/
git mv frontend/src/hooks/use-pos-history.ts pos-desktop/src/hooks/
git mv frontend/src/hooks/use-pos-products.ts pos-desktop/src/hooks/
git mv frontend/src/hooks/use-pos-returns.ts pos-desktop/src/hooks/
git mv frontend/src/hooks/use-pos-scanner.ts pos-desktop/src/hooks/
git mv frontend/src/hooks/use-pos-sync-issues.ts pos-desktop/src/hooks/
git mv frontend/src/hooks/use-pos-terminal.ts pos-desktop/src/hooks/
```

Note: `use-expiry-exposure.ts` is non-POS-named but recon may flag it. Check Task 1.5 §A — if it's POS-only, include it; otherwise leave it.

- [ ] **Step 4: Move store, context, lib, types**

```bash
git mv frontend/src/store/pos-cart-store.ts pos-desktop/src/store/cart-store.ts
git mv frontend/src/contexts/pos-cart-context.tsx pos-desktop/src/contexts/
git mv frontend/src/lib/pos/format-drug-name.ts pos-desktop/src/lib/
git mv frontend/src/lib/pos/ipc.ts pos-desktop/src/lib/
git mv frontend/src/lib/pos/offline-db.ts pos-desktop/src/lib/
git mv frontend/src/lib/pos/print-bridge.ts pos-desktop/src/lib/
git mv frontend/src/lib/pos/scanner-keymap.ts pos-desktop/src/lib/
git mv frontend/src/types/pos.ts pos-desktop/src/types/
```

- [ ] **Step 5: Move POS tests**

For each test in `frontend/src/__tests__/` matching POS code per recon §2:

```bash
# Pattern: tests/__tests__/components/pos/<X>.test.tsx → pos-desktop/__tests__/components/<X>.test.tsx
git mv frontend/src/__tests__/components/pos/<X>.test.tsx pos-desktop/__tests__/components/<X>.test.tsx
git mv frontend/src/__tests__/hooks/use-pos-<X>.test.ts pos-desktop/__tests__/hooks/use-pos-<X>.test.ts
git mv frontend/src/__tests__/lib/pos/<X>.test.ts pos-desktop/__tests__/lib/<X>.test.ts
git mv frontend/src/__tests__/store/pos-cart-store.test.ts pos-desktop/__tests__/store/cart-store.test.ts
# etc — recon §2 has the full list
```

- [ ] **Step 6: Commit the move (no import fixes yet — those are next)**

```bash
git commit -m "refactor(pos): mv POS code → pos-desktop/src/ (Phase 1 Task 2.4 — paths only, imports broken)"
```
Tests will be RED at this point — that's expected. Step 2.5 fixes the imports.

#### Task 2.5: Codemod to fix imports

- [ ] **Step 1: Write the codemod script**

Create `scripts/pos-import-codemod.mjs`:

```javascript
#!/usr/bin/env node
// Rewrite POS imports after Task 2.4 mechanical move.
// Run: node scripts/pos-import-codemod.mjs <root>
import { readFileSync, writeFileSync } from "node:fs";
import { globSync } from "glob";

const root = process.argv[2] ?? ".";
const files = globSync(`${root}/{frontend,pos-desktop}/**/*.{ts,tsx}`, {
  ignore: ["**/node_modules/**", "**/dist/**", "**/.next/**"],
});

const REWRITES = [
  // Direction: callers of POS code now import from @pos/*
  [/from\s+["']@\/components\/pos\/([^"']+)["']/g, 'from "@pos/components/$1"'],
  [/from\s+["']@\/hooks\/use-pos-([^"']+)["']/g, 'from "@pos/hooks/use-pos-$1"'],
  [/from\s+["']@\/contexts\/pos-cart-context["']/g, 'from "@pos/contexts/pos-cart-context"'],
  [/from\s+["']@\/store\/pos-cart-store["']/g, 'from "@pos/store/cart-store"'],
  [/from\s+["']@\/lib\/pos\/([^"']+)["']/g, 'from "@pos/lib/$1"'],
  [/from\s+["']@\/types\/pos["']/g, 'from "@pos/types/pos"'],
  // POS files now reach shared utilities via @shared/* alias
  // (NB: only inside pos-desktop/ — frontend/ keeps @/lib/utils as-is)
];

let changed = 0;
for (const file of files) {
  const before = readFileSync(file, "utf8");
  let after = before;
  for (const [from, to] of REWRITES) after = after.replace(from, to);
  if (file.startsWith(`${root}/pos-desktop/`)) {
    after = after.replace(/from\s+["']@\/lib\/utils["']/g, 'from "@shared/utils"');
    after = after.replace(/from\s+["']@\/components\/empty-state["']/g, 'from "@shared/components/empty-state"');
    after = after.replace(/from\s+["']@\/components\/auth-provider["']/g, 'from "@shared/components/auth-provider"');
    // Generic shared imports — extend per recon §1.1 cross-cut summary
  }
  if (after !== before) {
    writeFileSync(file, after);
    changed++;
  }
}
console.log(`${changed} file(s) rewritten`);
```

- [ ] **Step 2: Run the codemod**

```bash
node scripts/pos-import-codemod.mjs .
```
Expected: ~67 files rewritten (per recon §1.1).

- [ ] **Step 3: Type-check both packages**

```bash
cd frontend && npx tsc --noEmit 2>&1 | tail -20
cd ../pos-desktop && npx tsc --noEmit 2>&1 | tail -20
```
Expected: 0 errors. If any TS7006 (implicit-any) appear in newly-touched files that weren't pre-existing, FIX THEM (don't sweep — user wants clean code).

- [ ] **Step 4: Run tests**

```bash
cd frontend && npm run test -- --run 2>&1 | tail -10
cd ../pos-desktop && npm run test 2>&1 | tail -10
```
Expected: same green count as Task 2.1 step 2 (parity gate).

- [ ] **Step 5: Commit**

```bash
git add scripts/pos-import-codemod.mjs
git add -u
git commit -m "refactor(pos): codemod imports → @pos/* aliases (Phase 1 Task 2.5)"
```

#### Task 2.6: Extract POS-only CSS

- [ ] **Step 1: Read recon §4 for exact line ranges**

Lines to extract from `frontend/src/app/globals.css`:
- 1086–1124 (`.pos-root` block, 15 base tokens)
- 1129–1264 (animations: `pos-glow-halo`, `pos-display`, `dpScan*`, `pos-scan-flash*`, `pos-provisional-rail`, `dpRowEnter`, `dpSlideUp`, `dpKeyFade`)
- 1295–1361 (`.pos-omni` block, 40 expanded tokens)
- 1364–1517 (receipt surface: `.pos-omni .pos-grand-total`, `.pos-omni .pos-eyebrow`, `.pos-omni .pos-receipt`, etc., plus print variants and `@page`)
- 573–608 (print pipeline: `.pos-print-root`, `.pos-print-paper`, etc.)

- [ ] **Step 2: Create `pos-desktop/src/styles/globals.css`**

Use `Read` to slice each range from `frontend/src/app/globals.css`, then `Write` them concatenated (in order: tokens first, then geometry/typography, then animations, then receipt surface, then print pipeline) into the new file. Preserve the original cascade order.

- [ ] **Step 3: Delete those exact ranges from `frontend/src/app/globals.css`**

Use `Edit` with the precise old/new strings — never sed/awk on this file (it's 1500+ lines and easy to corrupt).

- [ ] **Step 4: Wire `pos-desktop/src/styles/globals.css` into the POS pages layout**

In `pos-desktop/src/pages/layout.tsx`, ensure the import points to the new path:
```tsx
import "@pos/styles/globals.css";
```
Remove any old `import "@/app/globals.css"` from POS files.

- [ ] **Step 5: Smoke-test the visual port**

Run dev:
```bash
cd pos-desktop && npm run dev
```
Manually open the terminal page and confirm: gold accents, glow halo, receipt surface render correctly. Record a Playwright screenshot to `docs/brain/incidents/screenshots/2026-05-01-css-extract.png` for diff against the pre-task baseline.

- [ ] **Step 6: Run dashboard regression check**

```bash
cd frontend && npm run dev &
# wait for ready, screenshot a non-POS page (e.g. /dashboard) and diff vs baseline
```
Expected: no visual regression. The extracted tokens were POS-only per recon §4.

- [ ] **Step 7: Commit**

```bash
git add -u pos-desktop/src/styles/globals.css frontend/src/app/globals.css pos-desktop/src/pages/layout.tsx
git commit -m "refactor(pos): extract POS-only CSS → pos-desktop/src/styles/globals.css (Phase 1 Task 2.6)"
```

#### Task 2.7: Smoke test — Electron app launches

- [ ] **Step 1: Build Electron in dev mode**

```bash
cd pos-desktop && npm run dev
```
Expected: Electron window opens, terminal page loads, IPC works (test by running a `getConfig` IPC call from the renderer console).

- [ ] **Step 2: Open all 8 POS routes**

Manually click through: terminal → checkout → shift → drugs → history → pos-returns → sync-issues → and back to terminal. Each must load without console errors.

- [ ] **Step 3: Run the cashier walkthrough on staging**

Open shift → scan one drug → quick-pick another → apply a voucher → checkout cash → shift close → receipt prints. If any step fails, ROOT-CAUSE before continuing — do not paper over with a sub-PR-level workaround.

#### Task 2.8: Open Sub-PR 1

- [ ] **Step 1: Push branch + open PR**

```bash
git push -u origin feat/pos-extraction-phase-1
gh pr create \
  --base main \
  --title "feat(pos): Phase 1 Sub-PR 1 — mechanical move + dead-code drop + CSS extract" \
  --body "$(cat <<'EOF'
## Summary
Phase 1 Task 2 — moves POS code to `pos-desktop/src/`, drops dead code (Task 1.5 §D), extracts POS-only CSS. **No behavior change** — Electron app still uses embedded Next.js standalone; only paths changed.

- 67 files moved per recon §5
- Dead code dropped per Task 1.5 §D drop list
- 55 POS-only CSS tokens + 40 rule blocks extracted
- All 160 existing tests stay green (parity gate verified at Task 2.5 step 4)

## Test plan
- [ ] CI green
- [ ] Manual cashier walkthrough on staging passes (Task 2.7 step 3)
- [ ] Dashboard visual regression: no diff vs baseline (Task 2.6 step 6)
EOF
)"
```

- [ ] **Step 2: Dispatch `code-reviewer` agent (Sonnet 4.6)**

```
Agent({
  subagent_type: "code-reviewer",
  description: "Review Phase 1 Sub-PR 1",
  prompt: "Review PR <URL>. Focus on: (a) any cross-cut import that the codemod missed → would surface as TS7006 in CI, (b) any CSS rule whose selectors leaked from .pos-omni / .pos-root scope, (c) any test that's still red because it imports a moved file, (d) any frontend/src/components/pos/ residue. Report blocking issues vs nice-to-haves separately."
})
```

- [ ] **Step 3: Address reviewer feedback, get CI green, request human review, merge**

Operator step. Once merged, Task 2 is **DONE**. Task 3 begins.

---

### Task 3: Vite migration — Sub-PR 2 (2–3 days)

**Goal:** Replace embedded Next.js standalone with a Vite-built static React renderer loaded via `BrowserWindow.loadFile()`. Bundled installer ≥20 MB smaller. Zero behavior change.

**Files this task PRODUCES:**
- Create: `pos-desktop/vite.config.ts`
- Create: `pos-desktop/index.html`
- Create: `pos-desktop/src/main.tsx` (Vite entry — replaces Next.js auto-bootstrap)
- Create: `pos-desktop/src/router.tsx` (`createHashRouter` setup)
- Create: `pos-desktop/public/fonts/{Fraunces,JetBrainsMono,Cairo}.woff2` (self-hosted)
- Create: `pos-desktop/src/styles/fonts.css` (manual `--font-*` CSS variables replacing `next/font/google`)

**Files this task MODIFIES:**
- `pos-desktop/electron/main.ts` — `BrowserWindow.loadFile('dist/renderer/index.html')` replaces the `spawn(node, ['server.js'])` block
- `pos-desktop/electron-builder.yml` — drop `extraResources` block referencing `resources/nextjs`
- `pos-desktop/scripts/build.sh` — drop the standalone-copy block
- `pos-desktop/package.json` — add Vite + react-router-dom deps; bump version to 3.0.0
- All `pos-desktop/src/pages/*.tsx` — strip Next.js page conventions (`export default function Page`, no metadata/layout primitives)
- `pos-desktop/src/pages/layout.tsx` — replace `next/font/google` with `import "@pos/styles/fonts.css"`

**Files this task DELETES:**
- `pos-desktop/resources/nextjs/` (entire directory)

#### Task 3.1: Add Vite + dependencies

- [ ] **Step 1: Install Vite + React Router**

```bash
cd pos-desktop
npm install --save-dev vite @vitejs/plugin-react vite-plugin-electron
npm install --save react-router-dom
```

- [ ] **Step 2: Create `pos-desktop/vite.config.ts`**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@pos": path.resolve(__dirname, "src"),
      "@shared": path.resolve(__dirname, "../frontend/src"),
    },
  },
  base: "./",
  build: {
    outDir: "dist/renderer",
    rollupOptions: {
      input: path.resolve(__dirname, "index.html"),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
  },
});
```

- [ ] **Step 3: Create `pos-desktop/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>DataPulse POS</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 4: Smoke test Vite dev server**

```bash
cd pos-desktop && npx vite
```
Expected: dev server boots at `http://localhost:5173`, serves a blank page (we haven't created `main.tsx` yet).

- [ ] **Step 5: Commit**

```bash
git add pos-desktop/vite.config.ts pos-desktop/index.html pos-desktop/package.json pos-desktop/package-lock.json
git commit -m "feat(pos-desktop): add Vite + React Router deps + config (Phase 1 Task 3.1)"
```

#### Task 3.2: Self-host fonts (replaces `next/font/google`)

- [ ] **Step 1: Download Fraunces, JetBrains Mono, Cairo as .woff2**

```bash
mkdir -p pos-desktop/public/fonts
# Download from Google Fonts API (or vendor them in a vendor/ if offline)
curl -L -o pos-desktop/public/fonts/Fraunces.woff2 "https://fonts.gstatic.com/s/fraunces/v34/<id>.woff2"
curl -L -o pos-desktop/public/fonts/JetBrainsMono.woff2 "https://fonts.gstatic.com/s/jetbrainsmono/v20/<id>.woff2"
curl -L -o pos-desktop/public/fonts/Cairo.woff2 "https://fonts.gstatic.com/s/cairo/v30/<id>.woff2"
```

NB: replace `<id>` with the actual Google Fonts URL. Use `npx google-fonts-helper` or the bundled fonts already in the existing build.

- [ ] **Step 2: Create `pos-desktop/src/styles/fonts.css`**

```css
@font-face {
  font-family: "Fraunces";
  src: url("/fonts/Fraunces.woff2") format("woff2");
  font-weight: 100 900;
  font-display: swap;
}
@font-face {
  font-family: "JetBrains Mono";
  src: url("/fonts/JetBrainsMono.woff2") format("woff2");
  font-weight: 100 900;
  font-display: swap;
}
@font-face {
  font-family: "Cairo";
  src: url("/fonts/Cairo.woff2") format("woff2");
  font-weight: 200 1000;
  font-display: swap;
}

:root {
  --font-fraunces: "Fraunces", serif;
  --font-jetbrains-mono: "JetBrains Mono", monospace;
  --font-cairo: "Cairo", "Segoe UI", system-ui, sans-serif;
}
```

- [ ] **Step 3: Replace `next/font/google` import in layout**

In `pos-desktop/src/pages/layout.tsx`:

```diff
- import { Fraunces, JetBrains_Mono, Cairo } from "next/font/google";
- const fraunces = Fraunces({ subsets: ["latin"], display: "swap" });
- const jetbrainsMono = JetBrains_Mono({ subsets: ["latin"], display: "swap" });
- const cairo = Cairo({ subsets: ["arabic"], display: "swap" });
+ import "@pos/styles/fonts.css";
```

Adjust any `<html className={`${fraunces.variable} …`}>` to use `<html style={{ fontFamily: "var(--font-cairo)" }}>` or class-based references.

- [ ] **Step 4: Type-check**

```bash
cd pos-desktop && npx tsc --noEmit
```
Expected: 0 errors. If `next/font/google` is the only Next.js-specific import (per recon §3), this completes the de-Next.js dependency.

- [ ] **Step 5: Commit**

```bash
git add pos-desktop/public/fonts/ pos-desktop/src/styles/fonts.css pos-desktop/src/pages/layout.tsx
git commit -m "feat(pos-desktop): self-host fonts → drop next/font/google (Phase 1 Task 3.2)"
```

#### Task 3.3: Build the Vite entry + router

- [ ] **Step 1: Write a failing test for the router setup**

Create `pos-desktop/__tests__/router.test.tsx`:

```typescript
import { describe, it, expect } from "vitest";
import { router } from "@pos/router";

describe("POS router", () => {
  it("registers all 8 routes", () => {
    const paths = router.routes.flatMap((r) => r.children?.map((c) => c.path) ?? []);
    expect(paths).toEqual(
      expect.arrayContaining([
        "/terminal",
        "/checkout",
        "/shift",
        "/drugs",
        "/history",
        "/pos-returns",
        "/sync-issues",
      ])
    );
  });
});
```

Run:
```bash
cd pos-desktop && npx vitest run __tests__/router.test.tsx
```
Expected: FAIL with `Cannot find module '@pos/router'`.

- [ ] **Step 2: Create `pos-desktop/src/router.tsx`**

```typescript
import { createHashRouter, Outlet, Navigate } from "react-router-dom";
import Layout from "@pos/pages/layout";
import Terminal from "@pos/pages/terminal";
import Checkout from "@pos/pages/checkout";
import Shift from "@pos/pages/shift";
import Drugs from "@pos/pages/drugs";
import History from "@pos/pages/history";
import PosReturns from "@pos/pages/pos-returns";
import SyncIssues from "@pos/pages/sync-issues";

export const router = createHashRouter([
  {
    element: (
      <Layout>
        <Outlet />
      </Layout>
    ),
    children: [
      { index: true, element: <Navigate to="/terminal" replace /> },
      { path: "/terminal", element: <Terminal /> },
      { path: "/checkout", element: <Checkout /> },
      { path: "/shift", element: <Shift /> },
      { path: "/drugs", element: <Drugs /> },
      { path: "/history", element: <History /> },
      { path: "/pos-returns", element: <PosReturns /> },
      { path: "/sync-issues", element: <SyncIssues /> },
    ],
  },
]);
```

- [ ] **Step 3: Re-run the test**

```bash
cd pos-desktop && npx vitest run __tests__/router.test.tsx
```
Expected: PASS.

- [ ] **Step 4: Create `pos-desktop/src/main.tsx` (Vite entry)**

```typescript
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { router } from "@pos/router";
import "@pos/styles/globals.css";

const root = document.getElementById("root");
if (!root) throw new Error("#root element not found in index.html");

createRoot(root).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>
);
```

- [ ] **Step 5: Strip Next.js conventions from each page**

For each `pos-desktop/src/pages/<page>.tsx`:
- Replace `export default function Page()` with named export matching the import in `router.tsx`
- Remove any `metadata` exports, `generateMetadata`, `layout` co-location magic
- Replace `next/navigation`'s `useRouter`, `usePathname` with `react-router-dom` equivalents (`useNavigate`, `useLocation`)

This is mechanical — same handful of patterns repeated 8 times. After every page, run `npx tsc --noEmit` to catch missed conversions.

- [ ] **Step 6: Smoke test the Vite build**

```bash
cd pos-desktop && npx vite build
ls dist/renderer/
```
Expected: `index.html`, `assets/index-<hash>.js`, `assets/index-<hash>.css`. Open `dist/renderer/index.html` directly in a browser — terminal page should render (no IPC, but visual is correct).

- [ ] **Step 7: Commit**

```bash
git add pos-desktop/src/router.tsx pos-desktop/src/main.tsx pos-desktop/src/pages/ pos-desktop/__tests__/router.test.tsx
git commit -m "feat(pos-desktop): Vite entry + React Router for 8 POS routes (Phase 1 Task 3.3)"
```

#### Task 3.4: Switch Electron to `loadFile`

- [ ] **Step 1: Edit `pos-desktop/electron/main.ts`**

Find the block that spawns the Next.js standalone server:

```typescript
// BEFORE (existing — find and delete):
const serverPath = path.join(process.resourcesPath, "nextjs", "server.js");
const serverProcess = spawn(process.execPath, [serverPath], { stdio: "pipe" });
// ... wait for "ready" log line
mainWindow.loadURL("http://localhost:3000");
```

Replace with:

```typescript
// AFTER:
mainWindow.loadFile(path.join(__dirname, "..", "dist", "renderer", "index.html"));
```

In dev mode, point at the Vite dev server:

```typescript
if (process.env.NODE_ENV === "development") {
  mainWindow.loadURL("http://localhost:5173");
} else {
  mainWindow.loadFile(path.join(__dirname, "..", "dist", "renderer", "index.html"));
}
```

- [ ] **Step 2: Update `pos-desktop/electron-builder.yml`**

Find:
```yaml
extraResources:
  - from: resources/nextjs
    to: nextjs
```

Delete it. Add:
```yaml
extraResources:
  - from: dist/renderer
    to: renderer
```

- [ ] **Step 3: Update `pos-desktop/scripts/build.sh`**

Drop the block that copies `frontend/.next/standalone` into `pos-desktop/resources/nextjs`. Replace with `vite build`:

```bash
# BEFORE: cp -r ../frontend/.next/standalone resources/nextjs
# AFTER:
npx vite build
```

- [ ] **Step 4: Delete the old embedded standalone**

```bash
rm -rf pos-desktop/resources/nextjs
```

- [ ] **Step 5: Build a development Electron build**

```bash
cd pos-desktop && npm run dev
```
Expected: Electron window opens at the Vite dev URL → terminal page loads → IPC handlers respond.

- [ ] **Step 6: Build a production Electron installer**

```bash
cd pos-desktop && npm run build
ls -lh dist/*-Setup.exe
```
Expected: installer is ≥20 MB smaller than baseline (was ~108 MB; target ≤90 MB per spec §10).

- [ ] **Step 7: Manual cashier walkthrough on the new installer**

Install on a test machine. Open shift → scan → quick-pick → voucher → checkout cash → checkout card (external terminal flow) → shift close → receipt print. Every step must succeed.

- [ ] **Step 8: Commit**

```bash
git rm -r pos-desktop/resources/nextjs
git add -u pos-desktop/electron/main.ts pos-desktop/electron-builder.yml pos-desktop/scripts/build.sh
git commit -m "feat(pos-desktop): switch Electron to loadFile() — drop embedded Next.js standalone (Phase 1 Task 3.4)"
```

#### Task 3.5: Open Sub-PR 2

Same flow as Task 2.8 — `gh pr create` with title `feat(pos): Phase 1 Sub-PR 2 — Vite migration + drop Next.js standalone`, dispatch `code-reviewer` agent (Sonnet 4.6) focused on: Electron load-flow regression, Vite build output completeness, missing IPC handlers, font fallbacks. Address feedback, merge.

After merge, Task 3 is **DONE**. Task 4 begins.

---

### Task 4: Cart-store unification — Sub-PR 3 (1–2 days, **highest risk**)

**Goal:** Collapse `pos-desktop/src/store/cart-store.ts` (Zustand) and `pos-desktop/src/contexts/pos-cart-context.tsx` (React Context) into one Zustand store. Every existing call-site reads from the new store. No behavior change verified by snapshot tests at every recon-mapped call-site.

**Why Opus on this task:** the recon flagged 14 `usePosCart` call-sites whose behavior must be preserved exactly. Subtle differences between the two stores (e.g., one debounces, one doesn't; one has eager `applied_discount` syncing, one doesn't) could regress the Charge flow if missed. Architect-level design call lives in Step 4.1.

#### Task 4.1: Architect design call (Opus 4.7)

- [ ] **Step 1: Dispatch `feature-dev:code-architect` (Opus 4.7)**

```
Agent({
  subagent_type: "feature-dev:code-architect",
  model: "opus",
  description: "Design unified POS cart store",
  prompt: "Design the unified Zustand cart store at pos-desktop/src/store/cart-store.ts. Inputs: (a) the current Zustand store at pos-desktop/src/store/cart-store.ts (54 LOC after merge); (b) the React Context at pos-desktop/src/contexts/pos-cart-context.tsx; (c) the 14 call-sites mapped in docs/superpowers/recon/2026-04-30-pos-extraction-recon.md §5. Identify: every state field, every setter, every selector. Flag any behavior the Context has that the Zustand store doesn't (e.g., debounce, derived state, side effects). Output: a markdown design with (1) the unified TypeScript interface for the store, (2) the migration mapping from each old call-site to the new shape, (3) any test cases that must pass after the migration. Save the design to docs/superpowers/plans/2026-05-01-pos-cart-store-design.md. Do NOT modify source code — design only."
})
```

- [ ] **Step 2: Review the architect's design**

Read `docs/superpowers/plans/2026-05-01-pos-cart-store-design.md`. Confirm: (a) every existing `usePosCart` call-site has a mapping, (b) every behavior the React Context has is preserved or explicitly waived, (c) the test plan covers the 5 cross-tier boundaries from recon §2.

- [ ] **Step 3: Commit the design**

```bash
git add docs/superpowers/plans/2026-05-01-pos-cart-store-design.md
git commit -m "docs(plan): unified POS cart store design (Phase 1 Task 4.1)"
```

#### Task 4.2: Write parity tests (TDD — RED)

For each call-site in the architect's design (§2 migration mapping):

- [ ] **Step 1: Write a snapshot/behavior test**

Example for the `addItem` flow at `pos-desktop/src/components/CartPanel.tsx`:

```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useCartStore } from "@pos/store/cart-store";

describe("CartPanel.addItem parity", () => {
  beforeEach(() => useCartStore.setState({ items: [], totals: null, applied_discount: null }));

  it("adds item, increments quantity on duplicate scan, recomputes totals", () => {
    const { result } = renderHook(() => useCartStore());
    act(() => result.current.addItem({ drug_code: "DR001", quantity: 1, unit_price: 10 }));
    expect(result.current.items).toHaveLength(1);
    expect(result.current.totals?.subtotal).toBe(10);

    act(() => result.current.addItem({ drug_code: "DR001", quantity: 1, unit_price: 10 }));
    expect(result.current.items).toHaveLength(1);
    expect(result.current.items[0].quantity).toBe(2);
    expect(result.current.totals?.subtotal).toBe(20);
  });
});
```

Repeat per call-site (14 tests total per recon).

- [ ] **Step 2: Run tests — they should FAIL**

```bash
cd pos-desktop && npx vitest run __tests__/store/cart-parity.test.ts
```
Expected: FAILs with current store missing methods/state from the design.

#### Task 4.3: Implement the unified store

- [ ] **Step 1: Replace `pos-desktop/src/store/cart-store.ts`**

Implement against the architect's design (`docs/superpowers/plans/2026-05-01-pos-cart-store-design.md` §1). Single Zustand store, all state + setters + derived selectors. Every type is exported.

- [ ] **Step 2: Run parity tests — they should PASS**

```bash
cd pos-desktop && npx vitest run __tests__/store/cart-parity.test.ts
```
Expected: PASS.

- [ ] **Step 3: Run full POS test suite**

```bash
cd pos-desktop && npm run test
cd ../frontend && npm run test -- --run
```
Expected: 0 regressions vs Task 2.1 baseline.

- [ ] **Step 4: Codemod every `useCartContext` call-site to `useCartStore`**

Add a final entry to `scripts/pos-import-codemod.mjs` and re-run:

```javascript
[/from\s+["']@pos\/contexts\/pos-cart-context["']/g, 'from "@pos/store/cart-store"'],
[/useCartContext\(\)/g, 'useCartStore()'],
```

```bash
node scripts/pos-import-codemod.mjs .
```

- [ ] **Step 5: Delete `pos-desktop/src/contexts/pos-cart-context.tsx`**

```bash
git rm pos-desktop/src/contexts/pos-cart-context.tsx
rmdir pos-desktop/src/contexts/  # if empty
```

- [ ] **Step 6: Type-check + test once more**

```bash
cd pos-desktop && npx tsc --noEmit && npm run test
```
Expected: 0 errors, 0 regressions.

- [ ] **Step 7: Commit**

```bash
git add -u
git commit -m "feat(pos-desktop): unify cart store — delete pos-cart-context (Phase 1 Task 4.3)"
```

#### Task 4.4: Manual checkout walkthrough

- [ ] **Step 1: Build dev Electron**

```bash
cd pos-desktop && npm run dev
```

- [ ] **Step 2: Cashier walkthrough**

Open shift → scan drug A (qty 1) → scan drug A again (expect qty 2) → scan drug B → apply 10% voucher → expect totals correct → checkout cash → expect receipt printed → shift close → expect summary correct.

If ANY step diverges from current production behavior, ROOT-CAUSE before proceeding. Diff against `git stash` of the previous store implementation if needed.

#### Task 4.5: Open Sub-PR 3

Same flow as 2.8 / 3.5 — `gh pr create` titled `feat(pos): Phase 1 Sub-PR 3 — cart-store unification`, dispatch `code-reviewer` (Sonnet) focused on: parity test completeness, any missed call-site, any behavior subtly different. Special attention to the 5 cross-tier boundaries from recon §2.

After merge, Task 4 is **DONE**. Task 5 begins.

---

### Task 5: Typed API client — Sub-PR 4 (1 day)

**Goal:** Replace ad-hoc `fetchAPI` / `postAPI` calls in POS code with a typed client generated from `contracts/openapi.json`. Auth + Idempotency-Key + retry happen in one place.

#### Task 5.1: Generate types

- [ ] **Step 1: Add `openapi-typescript` dev dep**

```bash
cd pos-desktop && npm install --save-dev openapi-typescript
```

- [ ] **Step 2: Generate types**

```bash
npx openapi-typescript ../contracts/openapi.json -o src/api/types.ts
```

- [ ] **Step 3: Commit**

```bash
git add pos-desktop/src/api/types.ts pos-desktop/package.json pos-desktop/package-lock.json
git commit -m "feat(pos-desktop): generate typed API types from openapi.json (Phase 1 Task 5.1)"
```

#### Task 5.2: Build the typed client

- [ ] **Step 1: Write failing tests**

Create `pos-desktop/__tests__/api/client.test.ts` with cases for: auth header forwarding, Idempotency-Key minting on POST, retry on 5xx (3 attempts, exponential backoff), no retry on 4xx, JSON body serialisation.

- [ ] **Step 2: Implement `pos-desktop/src/api/client.ts`**

```typescript
import type { paths } from "@pos/api/types";
import { v4 as uuidv4 } from "uuid";

type Method = "GET" | "POST" | "PATCH" | "DELETE";

interface ClientOptions {
  baseUrl: string;
  getToken: () => Promise<string | null>;
  fetch?: typeof fetch;
}

export class ApiClient {
  constructor(private readonly opts: ClientOptions) {}

  async request<T>(method: Method, path: string, body?: unknown): Promise<T> {
    const token = await this.opts.getToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (method === "POST") headers["Idempotency-Key"] = uuidv4();

    const fetchFn = this.opts.fetch ?? fetch;
    const url = `${this.opts.baseUrl}${path}`;
    const init: RequestInit = {
      method,
      headers,
      body: body != null ? JSON.stringify(body) : undefined,
    };

    for (let attempt = 0; attempt < 3; attempt++) {
      const res = await fetchFn(url, init);
      if (res.ok) return res.json() as Promise<T>;
      if (res.status >= 400 && res.status < 500) {
        throw new ApiError(res.status, await res.text());
      }
      // 5xx — exponential backoff
      await new Promise((r) => setTimeout(r, 250 * 2 ** attempt));
    }
    throw new ApiError(0, "exhausted retries");
  }
}

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
  }
}
```

- [ ] **Step 3: Tests pass**

```bash
cd pos-desktop && npx vitest run __tests__/api/client.test.ts
```

- [ ] **Step 4: Commit**

```bash
git add pos-desktop/src/api/client.ts pos-desktop/__tests__/api/client.test.ts
git commit -m "feat(pos-desktop): typed API client with auth + Idempotency-Key + retry (Phase 1 Task 5.2)"
```

#### Task 5.3: Replace ad-hoc fetch calls in POS code

- [ ] **Step 1: List every direct fetch in POS**

```bash
cd pos-desktop && grep -rn "fetchAPI\|postAPI\|patchAPI" src/ | head -30
```

- [ ] **Step 2: Replace each with typed endpoint module**

Create per-resource endpoint modules under `pos-desktop/src/api/endpoints/` — e.g., `transactions.ts`:

```typescript
import { ApiClient } from "@pos/api/client";
import type { paths } from "@pos/api/types";

type CommitTransactionRequest = paths["/api/v1/pos/transactions/commit"]["post"]["requestBody"]["content"]["application/json"];
type CommitTransactionResponse = paths["/api/v1/pos/transactions/commit"]["post"]["responses"]["200"]["content"]["application/json"];

export const createTransactionEndpoints = (client: ApiClient) => ({
  commit: (body: CommitTransactionRequest) =>
    client.request<CommitTransactionResponse>("POST", "/api/v1/pos/transactions/commit", body),
});
```

Repeat for: shifts, products, customers, vouchers, promotions, returns, sync.

- [ ] **Step 3: Update call-sites to use the new endpoints**

Per recon — there are ~11 call sites (recon §1.1). Replace each one. Type errors are your guide.

- [ ] **Step 4: Tests pass**

```bash
cd pos-desktop && npm run test
```

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "refactor(pos-desktop): replace ad-hoc fetch with typed endpoint modules (Phase 1 Task 5.3)"
```

#### Task 5.4: Open Sub-PR 4

Same flow — `gh pr create` titled `feat(pos): Phase 1 Sub-PR 4 — typed API client`, dispatch `code-reviewer`, address feedback, merge.

After merge, Phase 1 is **COMPLETE**. Bump `pos-desktop/package.json` to version `3.0.0` (clean-break signal) — this happens in Sub-PR 4's final commit.

---

## Phase 1 Acceptance criteria (per spec §10)

- [ ] All 160 existing POS tests pass (unchanged behavior)
- [ ] Cashier walkthrough succeeds on staging
- [ ] `pos-desktop/dist/*-Setup.exe` is ≥20 MB smaller than baseline
- [ ] Cart store has exactly one source of truth
- [ ] `frontend/src/components/pos/`, `frontend/src/app/(pos)/`, `frontend/src/hooks/use-pos-*` directories no longer exist
- [ ] `frontend/src/app/globals.css` has no `--pos-*` tokens

---

## Phase 3: Observation gate (2 weeks, ends 2026-05-14)

No code work. Operate, measure, decide.

### Task 3-Obs.1: Set up metrics tracking

- [ ] **Step 1: Create `docs/brain/observation/2026-05-01-pos-extraction-metrics.md`**

```markdown
# POS Extraction — Phase 3 Observation Log

**Window:** 2026-05-01 → 2026-05-14
**Decision deadline:** 2026-05-14

## Daily metrics

| Date | Pipeline incidents | Time-to-rollout | Cashier tickets | P1 bugs | P2 bugs | Pain notes |
|---|---|---|---|---|---|---|
| 2026-05-01 | | | | | | |
| ... | | | | | | |
```

Update daily.

### Task 3-Obs.2: Decision gate (2026-05-14)

- [ ] **Step 1: Write `docs/brain/decisions/2026-05-14-pos-extraction-outcome.md`**

Template:
```markdown
# POS Extraction Outcome — 2026-05-14

## Did the structural pain stop?
[answer with metrics]

## What's still messy?
[bulleted]

## Decision
- [ ] Calm — keep extracted module, close initiative
- [ ] Still noisy in pipeline — another scoped fix; do NOT fork yet
- [ ] Still noisy in code — fork to a separate repo, with the recon + extraction work as the starting point
```

---

## Self-Review

**1. Spec coverage**

Spec §4 (Phase 2):
- 4.1 tag/version assertion → Phase 2-B Task 2-B.1
- 4.2 auto-register endpoint → Phase 2-B Task 2-B.1
- 4.3 code-signing → Phase 2-B Task 2-B.1 step 4 (operator)
- 4.4 testing → Phase 2-B Task 2-B.1 PR test plan

Spec §5 (Phase 1):
- 5.1 recon → Task 1 DONE; Task 1.5 (dead-code scan) supplements
- 5.2 module move → Task 2
- 5.3 typed API client → Task 5
- 5.4 testing → Tasks 2.7, 3.7, 4.4 manual walkthroughs + parity tests

Spec §6 (Phase 3):
- Metrics + decision file → Phase 3 Task 3-Obs.1, 3-Obs.2

Spec §10 acceptance criteria → covered above.

**2. Placeholder scan**

Searched for: `TBD`, `TODO`, `implement later`, `appropriate error handling`, `Similar to Task`, `fill in details` — none in this plan. The `<id>` in Task 3.2 step 1 (Google Fonts URL) is a non-deterministic external value, intentionally bracketed for the executor to fill at runtime — this is acceptable.

**3. Type consistency**

- `useCartStore` (not `useCartContext`) referenced consistently in Task 4.
- `ApiClient` (not `Client` or `HttpClient`) consistently in Task 5.
- `@pos/*` alias consistently in all `tsconfig`, codemod, and import examples.
- `pos-desktop/src/store/cart-store.ts` (not `pos-cart-store.ts`) consistently after Task 2.

---

## Execution handoff

This plan ships in two layers:

**Layer 1 (orchestration, this session):** Phase 0 already done. Execute Task 1.5 (dead-code scan) inline since it's read-only and parallel agent dispatch is straightforward. Stop at user gate (Task 1.5 step 3).

**Layer 2 (sub-PRs, subagent-driven):** Each of Tasks 2, 3, 4, 5 is a sub-PR. Use `superpowers:subagent-driven-development` — fresh subagent per task with this plan + recon + dead-code scan in context. Two-stage review per the skill: subagent self-review at the end of each task, then human review of the PR.

Phase 2-B (Task 2-B.1) runs in parallel with Phase 1 — it has no dependency on Phase 1 work.

Phase 3 is observation; no executor needed — calendar deadline.
