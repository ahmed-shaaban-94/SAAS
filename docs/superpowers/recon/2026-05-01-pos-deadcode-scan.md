# POS Dead-Code Scan — Phase 1 Task 1.5 Output

**Date:** 2026-05-01
**For:** `docs/superpowers/plans/2026-05-01-pos-master-plan.md` Task 2.3 (drop list)
**Status:** Read-only inventory. Drop list awaits user approval (Task 1.5 step 3 gate).

Three parallel `Explore` (Sonnet 4.6) agents scanned for: (A) unused exports, (B) fix-on-fix bug-trail hot-spots, (C) orphan tests. Findings consolidated below.

---

## §A — Unused exports (cross-verified)

### Whole-file drops (high confidence)

These 6 files have **zero non-test importers** anywhere in the repo. Cross-verified via direct grep (false-positive rate: 0). One co-test deletion attached.

| Path | Export | Co-tests to drop | Verification |
|---|---|---|---|
| `frontend/src/components/pos/CartPanel.tsx` | `CartPanel` (function) | none | Only references in `terminal/page.tsx:88–89` are comments, not imports |
| `frontend/src/components/pos/CartItem.tsx` | `CartItem` (function) | none | Cascade — only importer was `CartPanel.tsx` (now dead) |
| `frontend/src/components/pos/NumPad.tsx` | `NumPad` (function) | none | Zero non-self occurrences |
| `frontend/src/components/pos/ProductSearch.tsx` | `ProductSearch` (function) | none | Zero non-self occurrences |
| `frontend/src/components/pos/PromotionsModal.tsx` | `PromotionsModal`, `PromotionsModalProps` | `__tests__/components/pos/PromotionsModal.test.tsx` | Source has zero importers; test exists but has no live consumer to validate |
| `frontend/src/hooks/use-pos-scanner.ts` | `usePosScanner` (hook) | none | Hook is defined, never called |

**Total: 6 source files + 1 test file = 7 git-rm targets in Task 2.3**

### Line-level dead exports (clean up DURING Task 2 codemod, not Task 2.3)

These exports are dead but live in files that have other live exports. They get cleaned up incidentally as part of the Task 2.5 codemod, not as a separate `git rm` step.

- `frontend/src/hooks/use-pos-terminal.ts:10` `usePosTerminal` (function) — never called
- `frontend/src/hooks/use-pos-terminal.ts:29` `pauseTerminal` (function)
- `frontend/src/hooks/use-pos-terminal.ts:33` `resumeTerminal` (function)
- `frontend/src/hooks/use-pos-products.ts:39` `usePosStockInfo` (function)
- `frontend/src/hooks/use-pos-customer-lookup.ts:47` `normalizeEgyptianPhone` (function)
- `frontend/src/lib/pos/offline-db.ts:39` `searchProducts`
- `frontend/src/lib/pos/offline-db.ts:58` `getProductByCode`
- `frontend/src/lib/pos/offline-db.ts:97` `getQueueStats`
- `frontend/src/lib/pos/offline-db.ts:30` `PosProductResult` (type) — duplicate of `types/pos.ts#PosProductResult`
- `frontend/src/lib/pos/ipc.ts:233` `drawer` (const)
- `frontend/src/lib/pos/ipc.ts:237` `sync` (const)
- `frontend/src/lib/pos/ipc.ts:243` `authz` (const)
- `frontend/src/components/pos/sync/reason-tags.ts:15` `ReasonTone` (type)
- `frontend/src/components/pos/sync/reason-tags.ts:17` `ReasonMeta` (interface)
- `frontend/src/components/pos/sync/reason-tags.ts:23` `REASON_META` (const)
- `frontend/src/components/pos/drugs/types.ts:24` `classifyStock` (function)
- ~12 unused interface props on individual modal components (`InsuranceModal`, `InvoiceModal`, `ModalShell`, `VoucherCodeModal`, `StocktakingModal`)
- ~9 unused types in `frontend/src/types/pos.ts`: `TerminalStatus`, `ReceiptFormat`, `RefundMethod`, `PosStockBatch`, `EmailReceiptRequest`, `CashCountRequest`, `CashDrawerEventResponse`, `PharmacistVerifyRequest`, `PaginatedResponse`

**Action:** during Task 2.5 codemod, run `npx ts-prune` again post-move and remove these inline.

---

## §B — Fix-on-fix bug-trail hot-spots

Window: 2026-04-17 → 2026-04-30 (14 days).

### Top hot-spots by commit count

| Rank | File | Commits | Verdict |
|---|---|---|---|
| 1 | `frontend/src/app/(pos)/terminal/page.tsx` | 15 | **Salvage** — feature-driven; scan-bar fix-pair only blemish |
| 2 | `frontend/src/app/(pos)/layout.tsx` | 13 | **Rewrite candidate** — 5 consecutive fixes including security "v3" re-fix |
| 3 | `frontend/src/app/(pos)/checkout/page.tsx` | 11 | **Rewrite candidate** — 5 fixes spanning unrelated concerns (auth, receipts, VAT, branding, bulk-sync) |
| 4 | `frontend/src/components/pos/terminal/ClinicalPanel.tsx` | 5 | **Salvage** — 1 fix, rest feat |
| 5 | `frontend/src/components/pos/terminal/QuickPickGrid.tsx` | 5 | **Salvage** — all feat/perf |
| 5 | `frontend/src/components/pos/terminal/CartRow.tsx` | 5 | **Salvage** — feature-driven |
| 5 | `frontend/src/app/(pos)/drugs/page.tsx` | 5 | **Salvage** — fixes address different concerns |
| 5 | `frontend/src/app/(pos)/shift/page.tsx` | 5 | **Salvage** — stable trajectory |
| 9 | `frontend/src/lib/pos/ipc.ts` | 4 | **Untouched** — healthy, no fix commits |
| 9 | `frontend/src/components/pos/terminal/ShortcutLegend.tsx` | 4 | **Untouched** — minimal churn |

### Rewrite candidates (3 files — DEFER to per-file review during Task 2)

**`frontend/src/app/(pos)/layout.tsx`** — 5 consecutive fix commits in 4 days, including the "v3" security re-fix (`f84c5245 fix(pos/security): explicit tenant_id predicates in POS repo layer (#675) v3`). Mixes auth, Clerk bootstrap, offline bridge, tenant branding in one root component. **Recommend domain split** before further work.

**`frontend/src/app/(pos)/checkout/page.tsx`** — 5 fixes out of 11 commits, spanning unrelated domains:
- `36586818` close C4/C5/C6
- `f6ad58be` route receipts to native ESC/POS
- `ea36ee69` dynamic tenant_branding
- `d5ebb629` memo + VAT consistency
- `cb4410d8` bulk-sync cart items at Charge time

**Recommend domain split** (totals/payment/receipt/sync into separate hooks) before the Vite migration.

**`frontend/src/lib/pos/print-bridge.ts`** — 2 back-to-back fixes 25 minutes apart (sales path then shift-close path). Small file; classic incomplete-coverage pattern. **Recommend clean rewrite** with full path coverage.

### Action for Phase 1

These three files are NOT auto-dropped. They're flagged for per-file review during Task 2 (mechanical move). Two paths:
- **Option α (default):** `git mv` as-is (preserves git blame), open follow-up cleanup PRs after extraction
- **Option β:** rewrite-during-move — riskier (loses blame + bigger PR) but kills the bug churn permanently

Master plan defaults to **α**. User can elevate to β at the start of Task 2 for any flagged file.

---

## §C — Orphan tests

**None.** Every POS source file imported by every test file currently exists on disk. After Task 2.3 drops, the test in §A's table (`__tests__/components/pos/PromotionsModal.test.tsx`) will be dropped together with its source — that's a same-step deletion, not a delayed orphan.

### Stale-ish tests (review candidates, not auto-drops)

These tests have a 13-day lag between test last-modified (2026-04-17) and source last-modified (2026-04-30). Source has been touched, test hasn't been updated:

- `frontend/src/__tests__/lib/pos/offline-db.test.ts`
- `frontend/src/__tests__/lib/pos/scanner-keymap.test.ts`

**Action:** Task 2 acceptance gate (Task 2.7) runs all 160 tests — if either of these still passes against the latest source, leave them; if they break, update them as part of Task 2.

### POS test inventory (informational)

- 30 frontend POS unit tests (Vitest)
- 7 e2e POS specs (Playwright — `pos-cart`, `pos-controlled`, `pos-keyboard-modals`, `pos-returns`, `pos-shift`, `pos-terminal`, `pos-void`)
- 23 Electron unit tests (`pos-desktop/electron/__tests__/`) — all healthy, no orphans

---

## §D — Consolidated drop list (auto-execute in Task 2.3)

7 files. All low-risk.

```bash
git rm frontend/src/components/pos/CartPanel.tsx
git rm frontend/src/components/pos/CartItem.tsx
git rm frontend/src/components/pos/NumPad.tsx
git rm frontend/src/components/pos/ProductSearch.tsx
git rm frontend/src/components/pos/PromotionsModal.tsx
git rm frontend/src/hooks/use-pos-scanner.ts
git rm frontend/src/__tests__/components/pos/PromotionsModal.test.tsx
```

After deletion, run:
```bash
cd frontend && npm run test -- --run
```
Expected: 0 regressions (count drops by exactly the 8 cases in `PromotionsModal.test.tsx`).

---

## Outputs for the master plan

- **Task 2.3 drop list:** §D (7 files) — execute as-is.
- **Task 2 rewrite-vs-salvage decisions:** §B — defer to per-file review at start of Task 2 (default = α: mv as-is).
- **Task 2 line-level dead-export cleanup:** §A second table — fold into Task 2.5 codemod via `ts-prune`.
- **Phase 1 acceptance gate:** §C stale-ish tests are watched, not pre-fixed.

This scan does NOT authorize any deletion. User review (Task 1.5 step 3) gates the actual `git rm`.
