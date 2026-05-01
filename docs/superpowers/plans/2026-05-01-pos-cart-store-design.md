# POS Cart Store — Sub-PR 3 Design

**Date:** 2026-05-01
**Phase:** 1 / Task 4.1
**Author:** Architect (Opus)
**Status:** READY — implementer can begin
**Estimated effort:** 1 day (single executor, TDD)
**Risk class:** LOW (re-scoped — see §0)

> Read first: `docs/superpowers/plans/2026-05-01-pos-master-plan.md` §Task 4
> and `docs/superpowers/recon/2026-04-30-pos-extraction-recon.md` §1.1, §2.

---

## §0. State of play (read this before §1)

The recon and master plan describe Sub-PR 3 as a **unification of two cart
stores**. That premise is no longer accurate. A prior PR already collapsed
the React Context into a stateless passthrough Provider:

- `pos-desktop/src/contexts/pos-cart-context.tsx` is **15 lines of live code**:
  - `PosCartProvider` (renders `<>{children}</>`)
  - `AppliedCartDiscount` (interface, used by the Zustand store)
  - `CartVoucher` (interface, used by `VoucherCodeModal`)
  - `computeVoucherDiscount` (pure function, used by `VoucherCodeModal` and `terminal.tsx`)
- `pos-desktop/src/hooks/use-pos-cart.ts` is **already** a thin selector
  wrapper over `usePosCartStore` — every field and action it returns
  pulls directly from the Zustand store.
- `pos-desktop/src/store/cart-store.ts` is the single source of truth for
  cart state. There is no second store. There is no behavior diff to
  preserve.

**Implication for Sub-PR 3 scope.** This is a **dead-code removal +
type-relocation pass**, not a unification. Calling it "unification" risks
manufacturing migration tests for migrations that don't exist. The real
work is:

1. Move `AppliedCartDiscount` from the context file → `cart-store.ts`
   (eliminates the awkward import where the store imports its own
   discount type from a context file: `cart-store.ts:3`).
2. Move `CartVoucher` and `computeVoucherDiscount` from the context file
   → a new `pos-desktop/src/lib/voucher.ts` (a voucher is a discount
   *source*, not part of the cart shape).
3. Remove `<PosCartProvider>` from `pos-desktop/src/pages/layout.tsx`
   (the wrapper does nothing).
4. Remove the same provider wrapper from two test files.
5. Delete `pos-desktop/src/contexts/pos-cart-context.tsx`.
6. Extend `scripts/pos-import-codemod.py` to redirect old import paths
   to the new homes.

The Zustand store contract (§1) does not change — the existing 14
selectors and 6 actions are already correct and already tested
(`frontend/src/__tests__/store/pos-cart-store.test.ts`, 18 tests).

---

## §1. Unified TypeScript interface

The single, canonical store contract. **Zero changes** vs the existing
`pos-desktop/src/store/cart-store.ts` — only the import of
`AppliedCartDiscount` is internalized.

```ts
// pos-desktop/src/store/cart-store.ts (post-Sub-PR 3)

import { create } from "zustand";
import type { PosCartItem } from "@pos/types/pos";
import type { AppliedDiscount } from "@/types/promotions";

// Moved here from contexts/pos-cart-context.tsx (was always co-owned by the cart).
export interface AppliedCartDiscount {
  source: AppliedDiscount["source"]; // "voucher" | "promotion"
  ref: string;
  label: string;
  discountAmount: number;
}

interface PosCartState {
  items: PosCartItem[];
  appliedDiscount: AppliedCartDiscount | null;

  addItem: (item: PosCartItem) => void;
  removeItem: (drugCode: string) => void;
  updateQuantity: (drugCode: string, quantity: number) => void;
  applyDiscount: (discount: AppliedCartDiscount) => void;
  clearDiscount: () => void;
  clear: () => void;

  subtotal: () => number;
  itemDiscountTotal: () => number;
  cartDiscountTotal: () => number;
  voucherDiscount: () => number;
  discountTotal: () => number;
  itemCount: () => number;
  hasControlledSubstance: () => boolean;
  grandTotal: () => number;
}
```

Side-effect contracts (preserved as-is): `removeItem` clears `appliedDiscount` when items goes empty; `updateQuantity(code, ≤0)` removes line + clears discount on empty; `addItem` stacks quantity for existing drug_code; `applyDiscount` replaces (not merges); `clear` resets both fields.

---

## §2. Migration mapping per call site

Because `usePosCart()` already routes through `usePosCartStore`, the
**runtime behavior** at every call site is unchanged. The only edits are
**type-import redirects** for sites that import `AppliedCartDiscount`,
`CartVoucher`, or `computeVoucherDiscount` from the now-deleted context
file, plus removing `PosCartProvider` JSX wrappers.

| # | File:line | What it touches | Old | New | Manual? |
|---|---|---|---|---|---|
| 1 | `pos-desktop/src/store/cart-store.ts:3` | `AppliedCartDiscount` type | import from `@pos/contexts/pos-cart-context` | define+export inline | manual (one-line) |
| 2 | `pos-desktop/src/hooks/use-pos-cart.ts:4,8` | `AppliedCartDiscount` re-export | from `@pos/contexts/pos-cart-context` | from `@pos/store/cart-store` | codemod |
| 3 | `pos-desktop/src/components/VoucherCodeModal.tsx:5–8` | `computeVoucherDiscount`, `CartVoucher` | from `@pos/contexts/pos-cart-context` | from `@pos/lib/voucher` | codemod |
| 4 | `pos-desktop/src/pages/terminal.tsx:41` | same | same | same | codemod |
| 5–12 | `pos-desktop/src/pages/{terminal,checkout,drugs}.tsx` | `usePosCart()` consumers | unchanged | unchanged | none |
| 13 | `pos-desktop/src/pages/layout.tsx:17` | `import { PosCartProvider }` | line removed | (deleted) | manual |
| 14 | `pos-desktop/src/pages/layout.tsx:224,234` | `<PosCartProvider>` JSX wrapper | removed | (children render directly) | manual JSX |
| 15 | `frontend/src/__tests__/app/(pos)/terminal.test.tsx:6,104,106` | Provider import + JSX | removed | (children render directly) | manual |
| 16 | `frontend/src/__tests__/app/(pos)/drugs.test.tsx:6,94,97` | same | removed | (children render directly) | manual |
| 17 | `frontend/src/__tests__/app/(pos)/layout.test.tsx:57–59` | `vi.mock("@pos/contexts/pos-cart-context", …)` | block removed | (deleted) | manual |
| 18 | `frontend/src/__tests__/store/pos-cart-store.test.ts` | direct setState/getState | unchanged | unchanged | none |

Sites 1–4 + 13–17 are the actual edit surface (8 files). Sites 5–12 + 18 are listed for completeness.

---

## §3. Behavior diffs preserved or waived

| Diff | Status | Note |
|---|---|---|
| Debounced setters (Context vs Zustand) | **N/A** | Context has no setters — passthrough Provider only. |
| Mount-time hydration / unmount-time persistence | **N/A** | Context has no `useEffect`, no state, no lifecycle. |
| Optimistic vs strict updates | **N/A** | All updates flow through Zustand's synchronous `set`. |
| `addItem` clearing voucher (or not) | **PRESERVED** | Existing: `addItem` does not clear `appliedDiscount`; `removeItem` and `updateQuantity(0)` do clear when cart becomes empty. Asymmetry is intentional. Already tested. |
| `line_total` recomputation on `updateQuantity` | **PRESERVED** | `recalcLine` formula `newQty × unit_price − discount` survives stacking. Already tested. |
| Voucher discount recomputation on `subtotal` change | **PRESERVED — call-site responsibility** | Store keeps `discountAmount` snapshot; `terminal.tsx:298–311` recomputes against current `subtotal` before `applyDiscount`. Backend re-validates canonically at commit. |
| `taxTotal` always 0 | **PRESERVED** | Pharmacy items zero-rated. `use-pos-cart.ts:42` hard-codes 0. |

**Net.** Zero behavior diffs to resolve.

---

## §4. Test plan

### §4.1 Existing tests that must stay green (no edits)

`frontend/src/__tests__/store/pos-cart-store.test.ts` — **18 tests**
covering every action, every derived selector, every side-effect.

### §4.2 New parity / migration tests (RED-first)

| # | Test | Where | What it asserts |
|---|---|---|---|
| T1 | `AppliedCartDiscount` exported from `cart-store.ts` | extend existing test | Type import resolves and shape matches. |
| T2 | `CartVoucher` exported from `lib/voucher.ts` | new `frontend/src/__tests__/lib/pos/voucher.test.ts` | Type import resolves; `computeVoucherDiscount` returns 0 for `subtotal <= 0`. |
| T3 | `computeVoucherDiscount` parity | same file as T2 | All four legacy cases: `amount` ≤ subtotal returns value; `amount` > subtotal capped; `percent` rounds 2dp; `subtotal=0` returns 0. (Lifted verbatim from current `pos-cart-context.tsx:40–49`.) |
| T4 | `PosCartProvider` no longer exported | extend layout test | Layout renders without the wrapper, auth/guard tree intact. |
| T5 | No source file imports `@pos/contexts/pos-cart-context` | grep CI check | Codemod converged. |

### §4.3 Cross-tier boundary parity (recon §2)

| Boundary | Touches cart? | Parity test? |
|---|---|---|
| Idempotency-key handling | YES — `terminal.tsx:341` reads `items`, POSTs each via idempotency key | T6 (covered by existing terminal.test.tsx) |
| Offline sync bridge | NO — sync queue is independent | No |
| Receipt rendering | NO — receipts read from API not cart | No |
| Device grants | NO — orthogonal | No |
| Terminal session | YES — `terminal.test.tsx:113` calls `usePosCartStore.setState` | T7 (verify reset shape stable) |

Boundaries 2/3/4 deliberately skipped — manufacturing parity tests for orthogonal subsystems is busywork.

---

## §5. Implementation order (TDD)

1. **RED** — extend tests (T1, T2, T3) — fail to compile.
2. **GREEN** — relocate types + helpers:
   - Inline `AppliedCartDiscount` in `cart-store.ts`; export it.
   - Create `pos-desktop/src/lib/voucher.ts` with `CartVoucher` + `computeVoucherDiscount`.
3. **GREEN** — point consumers at new homes (manual edits to 3 files for type imports).
4. **GREEN** — extend `scripts/pos-import-codemod.py` with two redirect rules; run dry-run; run for real.
5. **GREEN** — remove dead Provider:
   - `pages/layout.tsx`: delete import + open/close JSX tags.
   - 2 test files: same.
   - `layout.test.tsx`: delete `vi.mock` block.
6. **GREEN** — `git rm pos-desktop/src/contexts/pos-cart-context.tsx`; `rmdir` if empty.
7. **VERIFY** — vitest run; lint; `grep -rn "pos-cart-context"` empty.

Each step keeps the tree compiling. Step 5 must precede Step 6 — codemod redirects callers *before* file deletion.

---

## §6. Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Codemod regex misses an import variant. | medium | Build break. | After codemod, `grep -rn "pos-cart-context"` to find leftovers; manual edit. List of consumers is small (4 files). |
| R2 | `cart-store.ts:3` imports `AppliedCartDiscount` from context — sequencing matters. | medium | TS error during transition. | Step 2 *replaces* the import with inline definition AND adds `export`. Step 3 redirects consumers. Atomic per step. |
| R3 | JSX `<PosCartProvider>` removal across 3 files — multi-line edit. | medium | Stale wrapper survives. | Don't codemod JSX. Edit manually. |
| R4 | `layout.test.tsx` mocks `@pos/contexts/pos-cart-context` — module no longer exists. | low | Test warning. | Delete the entire `vi.mock(...)` block. |
| R5 | `terminal.tsx` voucher recompute moves to `lib/voucher.ts` — runtime sequence is the most-tested customer path. | low | Voucher button no-ops. | T6 covers the apply path. Run before merge. |
| R6 | This PR rebases on top of Sub-PR 2 (PR #809) which is itself in flight. | low | Merge conflict on `cart-store.ts`. | Rebase locally; surface for conflicts is small. |
| R7 | Master plan says "Zustand has richer state shape per audit notes" — reader may try to merge nonexistent state. | low | Wasted exploration. | §0 disclaims the unification framing. |

**Risks deliberately *not* listed.** Performance regression (impossible — same store), hydration mismatch (no SSR for POS desktop), tenant-id leakage (cart is RAM-only, scoped via API headers).

---

## Appendix A — Files touched (final manifest)

**Created:**
- `pos-desktop/src/lib/voucher.ts` (~50 lines)
- `frontend/src/__tests__/lib/pos/voucher.test.ts` (~40 lines)

**Modified:**
- `pos-desktop/src/store/cart-store.ts` (+10 lines)
- `pos-desktop/src/hooks/use-pos-cart.ts` (0 net)
- `pos-desktop/src/components/VoucherCodeModal.tsx` (0 net)
- `pos-desktop/src/pages/terminal.tsx` (0 net)
- `pos-desktop/src/pages/layout.tsx` (−5 lines)
- 3 test files (−9 lines combined)
- `frontend/src/__tests__/store/pos-cart-store.test.ts` (+5 lines)
- `scripts/pos-import-codemod.py` (+5 lines)

**Deleted:**
- `pos-desktop/src/contexts/pos-cart-context.tsx` (58 lines)

**Net diff:** ~−40 lines, 1 file deleted, 2 files created, 9 modified.

---

## Appendix B — Why this is decisively a single Zustand store

Per master plan §Task 4 the survivor must be Zustand. The decision is
already crystallized in code: the Context is a passthrough; the Zustand
store owns all state. This design ratifies the existing reality and
removes the dead Provider.
