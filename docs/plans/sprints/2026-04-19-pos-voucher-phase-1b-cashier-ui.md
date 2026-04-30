# POS Voucher — Phase 1b: Cashier UI Implementation Plan

> **For agentic workers:** Use `superpowers:subagent-driven-development` to execute.
> Depends on: Phase 1a engine PR (voucher backend + admin UI) being merged.

**Goal:** Let a cashier enter a voucher code at checkout, see the discount apply
to the cart, and print it as a line on the receipt. Completes the voucher loop
started in Phase 1a (backend engine + admin UI).

**Strategic Lever:** Activation — turns a half-finished feature into a
demonstrable one.

**Scope boundary:** manual code entry only. Phase 2 (promotions) handles
automatic rules-based discounts and does not share this code path except for
the cart-discount-line rendering primitive this plan introduces.

---

## Architecture

The voucher code travels from the `PaymentPanel` → through a new
`VoucherCodeModal` → into state held by the checkout flow → attached to the
`CommitRequest.voucher_code` / `CheckoutRequest.voucher_code` field. The
server does the actual discount application and redemption (already shipped
in Phase 1a). The cashier UI shows the discount line optimistically once the
server returns 200 with the new `CommitResponse.voucher_discount` field.

### Data flow

```
cashier clicks VOUCHER
       ↓
<VoucherCodeModal> opens — input + Validate button
       ↓
POST /api/v1/pos/vouchers/validate { code, cart_subtotal }
       ↓
200 → modal shows "EGP X discount will apply" + Confirm button
400/404 → modal shows inline error (no code match / expired / etc.)
       ↓
Confirm → modal stores code in parent state + closes
       ↓
Cart renders "Voucher EGP X off" as a discount line
       ↓
User proceeds to Finalize — POST /api/v1/pos/transactions/commit
                              { ..., voucher_code: "ABC123" }
       ↓
Server validates + redeems atomically inside commit transaction
       ↓
Receipt prints the discount line + updated grand total
```

Server-side redemption stays authoritative. The `/validate` call is a UX
courtesy — it gives the cashier fast feedback without committing. If the
network is down between validate and commit, commit will still validate
fresh so nothing stale sneaks through.

---

## File Map

| Action | File |
|--------|------|
| **Create** | `frontend/src/components/pos/VoucherCodeModal.tsx` |
| **Create** | `frontend/src/hooks/use-voucher-validate.ts` |
| **Create** | `frontend/src/__tests__/components/pos/VoucherCodeModal.test.tsx` |
| **Create** | `frontend/src/__tests__/hooks/use-voucher-validate.test.ts` |
| **Modify** | `frontend/src/app/(pos)/terminal/page.tsx` — intercept VOUCHER click to open modal before navigating to checkout |
| **Modify** | `frontend/src/app/(pos)/checkout/page.tsx` — render discount line when voucher attached; thread voucher_code into CheckoutRequest |
| **Modify** | `frontend/src/components/pos/CartPanel.tsx` — render discount line under subtotal when `cart.voucher` is set |
| **Modify** | `frontend/src/components/pos/ReceiptPreview.tsx` — include voucher discount line when present |
| **Modify** | `frontend/src/types/pos.ts` — extend `CheckoutRequest` + `CommitResponse` with `voucher_code` / `voucher_discount` (already present in Phase 1a types; just re-export for consumers) |
| **Modify** | `frontend/src/contexts/pos-cart-context.tsx` — add `voucher` slice + `applyVoucher` / `clearVoucher` actions |

---

## Task 1: Voucher validate hook

**File:** `frontend/src/hooks/use-voucher-validate.ts` (+ test)

### Contract

```ts
export interface VoucherValidateResult {
  code: string;
  discount_type: "amount" | "percent";
  value: string;            // Decimal as string
  remaining_uses: number;
  expires_at: string | null;
  min_purchase: string | null;
}

export function useVoucherValidate(): {
  validate: (code: string, cartSubtotal: number) => Promise<VoucherValidateResult>;
  isLoading: boolean;
  error: string | null;
};
```

### Behavior

- Uses `postAPI` from `@/lib/api-client` to POST
  `/api/v1/pos/vouchers/validate { code, cart_subtotal }`.
- On 200 → returns the result, clears any prior error.
- On 400/404 → throws an `Error` with the server's `detail` as the message
  (typed: `"voucher_not_found"`, `"voucher_expired"`, etc.).
- Not SWR — this is a one-shot mutation, not a polled read. Use `useState`
  for `isLoading` + `error`, `useCallback` for stable `validate`.

### Tests (Vitest + MSW)

- success path → returns the payload
- 404 path → throws with `voucher_not_found`
- 400 min_purchase_unmet → error message includes `voucher_min_purchase_unmet`
- network error → throws with generic message

---

## Task 2: VoucherCodeModal component

**File:** `frontend/src/components/pos/VoucherCodeModal.tsx` (+ test)

### Contract

```tsx
interface Props {
  cartSubtotal: number;
  onApply: (code: string, discountPreview: number) => void;
  onCancel: () => void;
}
```

### UI states

1. **Enter code** — text input (auto-uppercase, max 64 chars, pattern
   `[A-Z0-9_-]+`), Validate button disabled until >=3 chars
2. **Validating** — spinner, button disabled
3. **Valid** — shows `"EGP X off"` or `"Y% off (up to EGP Z)"` + Confirm /
   Change code buttons. Confirm calls `onApply(code, computedDiscount)`.
4. **Error** — red inline message, input re-enabled for another attempt

### Discount preview computation (client-side)

Mirrors `VoucherService.compute_discount` from the backend exactly:

```ts
function preview(type: "amount"|"percent", value: number, subtotal: number) {
  if (type === "amount") return Math.min(value, subtotal);
  return Math.round((subtotal * value / 100) * 100) / 100;  // 2dp
}
```

### Accessibility

- `role="dialog"`, `aria-labelledby`, `aria-describedby`
- Escape closes (via `onCancel`)
- Focus on input on open (`useRef` + `useEffect`)
- Match the `ReconcileModal` / `VoidModal` styling conventions

### Tests

- renders input + Validate button disabled when code <3 chars
- Validate triggers useVoucherValidate
- success shows preview + Confirm
- Confirm invokes `onApply` with `(code, computedDiscount)`
- Cancel invokes `onCancel`
- 404 shows "Voucher not found"
- 400 min-purchase shows "Cart total too low for this voucher"

---

## Task 3: Cart context extension

**File:** `frontend/src/contexts/pos-cart-context.tsx`

Add a `voucher` slice to the existing cart state:

```ts
interface VoucherState {
  code: string;
  discount_type: "amount" | "percent";
  value: string;
  computed_discount: number;  // client-side preview, server replaces at commit
}

// Actions
applyVoucher(v: VoucherState): void;
clearVoucher(): void;

// Derived state
discountTotal: number;   // sum of item discounts + voucher computed_discount
grandTotal: number;      // subtotal - discountTotal + taxTotal
```

The voucher must be cleared automatically if the cart becomes empty.

---

## Task 4: Terminal page wiring

**File:** `frontend/src/app/(pos)/terminal/page.tsx`

Change `handleCheckout(method)`:

- If `method === "voucher"` and no voucher attached → open VoucherCodeModal
  first. On `onApply` → attach voucher to cart, navigate to `/checkout` with
  `method="voucher"`.
- If `method === "voucher"` and voucher already attached → navigate
  directly (the applied voucher is still valid in the modal preview; server
  will re-validate at commit).
- Other methods → unchanged.

---

## Task 5: Checkout page + cart line

**Files:**
- `frontend/src/app/(pos)/checkout/page.tsx` — pass `voucher_code` from cart
  context to `processCheckout`, which adds it to the `CheckoutRequest` body.
- `frontend/src/components/pos/CartPanel.tsx` — render the voucher line
  under subtotal, showing `"-EGP {computed_discount} ({code})"` in green
  with a small X button to clear the voucher (calls `clearVoucher`).

---

## Task 6: Receipt rendering

**File:** `frontend/src/components/pos/ReceiptPreview.tsx`

Add a "Discounts" section showing each applied discount. For vouchers:
```
Voucher (ABC123)           -EGP 50.00
```
Follow the receipt's existing line/column layout. If no discount, hide
the section entirely (don't render an empty heading).

---

## Task 7: Verification gate

Before committing the final PR:

- [ ] `npx tsc --noEmit` clean
- [ ] `npx vitest run` green — all new tests pass, no existing test regressions
- [ ] `ruff check` clean (no Python changes in Phase 1b, but smoke-test)
- [ ] Manual smoke (dev mode): add item → click VOUCHER → enter a test
  code → see discount preview → Confirm → cart shows discount line → Finalize
  → receipt shows discount line
- [ ] Server rejection path — if the voucher is consumed between validate and
  commit, commit returns 400 and the UI surfaces the error without losing
  the cart

---

## Out of scope (parked)

- Multiple vouchers per transaction (stacking) — defer until we see demand
- Voucher bulk-generation admin tool — single voucher create form is enough
  for MVP; bulk CSV import can ship later
- Offline voucher use — client refuses voucher entry when offline with a
  clear message. Phase 3 can add client-side cache + optimistic apply
- Customer-facing voucher lookup ("do I have any active vouchers?") — this
  is a customer-app feature, not POS
