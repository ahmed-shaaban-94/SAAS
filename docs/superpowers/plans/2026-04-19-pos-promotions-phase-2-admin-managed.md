# POS Promotions — Phase 2: Admin-Managed Seasonal Campaigns

> **For agentic workers:** Use `superpowers:subagent-driven-development`.
> Depends on: Phase 1a (voucher engine backend) and Phase 1b (cashier UI) — this
> phase reuses the cart-discount-line primitive and the atomic commit-time
> redemption pattern.

**Goal:** Let the pharmacy owner configure named discount campaigns (e.g.
"Ramadan 15% off antibiotics, 2026-04-20 → 2026-05-20") in an admin panel.
At checkout, the cashier sees which promotions are eligible for the current
cart and explicitly picks one (or none) to apply. No automatic rule engine
evaluation — the cashier is always in control.

**Strategic Lever:** Clarity (cashier keeps control of pricing) + Activation
(owner runs seasonal campaigns without staff retraining).

**Key architectural decision — NOT auto-applied:**

Per explicit product call: promotions do **not** apply themselves to
qualifying carts. The system surfaces eligible promotions for the current
cart; the cashier picks one. Rationale:
1. Cashier retains judgment (e.g., don't stack promotions, don't apply to
   staff purchases, apply best-value promotion for customer).
2. Avoids spec ambiguity about promotion stacking rules.
3. Simpler mental model: "promotion = pre-built voucher the cashier can
   apply without typing a code."

---

## Architecture

### Data model

```
pos.promotions
  id, tenant_id, name, description,
  discount_type ('amount'|'percent'), value,
  scope ('all'|'items'|'category'),
  starts_at, ends_at,         -- eligibility window; cart-time must fall within
  min_purchase,               -- optional threshold on cart subtotal
  max_discount,               -- optional cap for percent promos
  status ('active'|'paused'|'expired'),
  tenant_id + RLS + tenant+name unique,
  created_at, updated_at

pos.promotion_items
  promotion_id, drug_code     -- when scope='items'

pos.promotion_categories
  promotion_id, drug_cluster  -- when scope='category'

pos.promotion_applications   -- audit log of actual applications
  id, promotion_id, txn_id, applied_at,
  cashier_staff_id, discount_applied
```

### Lifecycle

1. **Admin creates** a promotion via `/settings/promotions/new` — name, type,
   value, scope (all/items/category), item picker or category picker, date
   range, optional thresholds. Status defaults to `paused` on creation so
   admin can preview before going live.
2. **Admin activates** by toggling status to `active`. No retroactive
   application — promotions only apply to transactions started *after*
   activation.
3. **Cashier at checkout** clicks a new "Promotions" button → modal lists
   all promotions where:
   - `status = active`
   - `now BETWEEN starts_at AND ends_at`
   - cart has items matching `scope` (for items/category)
   - `subtotal >= min_purchase` (if set)
4. **Cashier picks one** → it's attached to the cart like a voucher (reuses
   the `voucher` cart slice renamed to `applied_discount` — see Phase 1b
   refactor below).
5. **Commit** records a row in `pos.promotion_applications` atomically
   with the transaction INSERT.

### Why reuse the voucher path

The Phase 1b discount-line rendering + `CommitRequest.voucher_code` path
was designed as the single canonical cart-level discount primitive. Phase 2
extends it by adding a second *source* of that discount (a promotion
reference instead of a voucher code). The cart never holds both — cashier
picks one.

This means Phase 1b's `CommitRequest` field gets renamed from `voucher_code`
to `applied_discount: { source: 'voucher'|'promotion', ref: str }`. Server
routes the ref to the right redemption function. See §"Phase 1b refactor"
below.

---

## Scope

### In scope

- Admin CRUD for promotions
- Item picker (drug_code multi-select, autocomplete)
- Category picker (drug_cluster dropdown — reuse existing dim_product)
- Date-range picker (reuse `react-day-picker` already in the project)
- Cashier "Promotions" button at checkout → eligible promotions modal
- Server-side eligibility evaluation endpoint (`POST /pos/promotions/eligible`)
- Atomic record-of-application in `pos.promotion_applications`
- Audit: admin views "used N times, total discount given EGP X" per promotion

### Out of scope (parked)

- **Stacking** — one discount per transaction (voucher OR promotion, never
  both). UI explicitly disables the other button when one is attached.
- **Customer-segment targeting** — ("VIP customers only") defer to a Phase 3
  customer-loyalty system.
- **Buy-X-get-Y promotions** — this system only handles flat amount/percent
  off. Complex bundles need a separate rules engine.
- **Auto-application** — explicit product decision; see top of doc.
- **Promotion conflicts** — if two promotions are eligible, the cashier
  sees both and picks one. No ranking/scoring.

---

## File Map

### Backend

| Action | File |
|--------|------|
| Create | `migrations/09N_create_pos_promotions.sql` |
| Create | `migrations/09N+1_add_pos_promotion_permissions.sql` (`pos:promotion:manage`, `pos:promotion:apply`) |
| Create | `src/datapulse/pos/promotion_repository.py` |
| Create | `src/datapulse/pos/promotion_service.py` |
| Create | `src/datapulse/api/routes/promotions.py` |
| Modify | `src/datapulse/pos/models.py` — add `Promotion*` models |
| Modify | `src/datapulse/pos/commit.py` — route `applied_discount` to voucher OR promotion redemption |
| Create | `tests/test_pos_promotion_repository.py` |
| Create | `tests/test_pos_promotion_service.py` |
| Create | `tests/test_pos_promotions_endpoint.py` |
| Modify | `tests/test_pos_commit.py` — add promotion-application cases |

### Admin UI

| Action | File |
|--------|------|
| Create | `frontend/src/app/(app)/settings/promotions/page.tsx` (list) |
| Create | `frontend/src/app/(app)/settings/promotions/new/page.tsx` (create) |
| Create | `frontend/src/app/(app)/settings/promotions/[id]/page.tsx` (edit + activate/pause toggle) |
| Create | `frontend/src/hooks/use-promotions.ts` |
| Create | `frontend/src/hooks/use-promotion-applications.ts` (audit view) |
| Create | `frontend/src/components/promotions/ItemPicker.tsx` |
| Create | `frontend/src/components/promotions/CategoryPicker.tsx` |
| Create | `frontend/src/types/promotions.ts` |
| Create | tests for all of the above |

### Cashier UI

| Action | File |
|--------|------|
| Create | `frontend/src/components/pos/PromotionsModal.tsx` |
| Create | `frontend/src/hooks/use-eligible-promotions.ts` (POSTs current cart → gets list) |
| Modify | `frontend/src/app/(pos)/terminal/page.tsx` — add Promotions button near PaymentPanel |
| Modify | `frontend/src/contexts/pos-cart-context.tsx` — rename `voucher` slice to `applied_discount` (union type) |
| Modify | `frontend/src/components/pos/CartPanel.tsx` — generic discount line works for both sources |
| Create | test files |

---

## Phase 1b refactor — needed before Phase 2 starts cleanly

The cart discount slice added in Phase 1b is voucher-specific. Before Phase 2,
rename the slice to be source-agnostic:

**Before (Phase 1b):**
```ts
cart.voucher: { code, discount_type, value, computed_discount } | null
```

**After (Phase 2 prep):**
```ts
cart.applied_discount: 
  | { source: 'voucher'; code: string; ...discount fields }
  | { source: 'promotion'; id: number; name: string; ...discount fields }
  | null
```

`CommitRequest`:
```python
# Instead of: voucher_code: str | None
applied_discount: AppliedDiscount | None = None

class AppliedDiscount(BaseModel):
    source: Literal['voucher', 'promotion']
    ref: str    # voucher code OR str(promotion_id)
```

The server routes `applied_discount` to the appropriate redemption function.
One cart slice, two sources, consistent rendering.

**Recommendation:** do the refactor as the first commit of Phase 2 so the
whole PR is coherent, rather than a separate refactor PR.

---

## Verification gate

- [ ] Migration applied on staging; RLS confirmed
- [ ] `pytest` green, coverage ≥ existing threshold
- [ ] `tsc --noEmit` clean
- [ ] `vitest` suites green
- [ ] Manual smoke:
  1. Admin creates `Ramadan-25 15% off` for drug_cluster = 'antibiotics',
     dates 2026-04-20 → 2026-05-20, status=paused
  2. Admin previews — not visible to cashier yet
  3. Admin activates
  4. Cashier adds antibiotic to cart → Promotions button shows "1 eligible"
  5. Cashier opens modal → sees `Ramadan-25 15% off`
  6. Cashier applies → cart shows discount line + reduced grand total
  7. Finalize → receipt prints discount line + `pos.promotion_applications`
     has a new row
  8. Cashier adds non-antibiotic only → Promotions button shows "0 eligible"
- [ ] Audit: admin views promotion detail → sees usage count + total
      discount given

---

## Estimated effort

3-5 days of focused work. Split into 2 PRs:
1. **Backend + admin UI** (~2-3 days)
2. **Cashier UI + Phase 1b refactor** (~1-2 days)
