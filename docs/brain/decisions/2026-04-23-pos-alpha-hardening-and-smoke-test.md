# 2026-04-23 — POS v1.0.0-alpha hardening + tailored smoke test

## Decision

Single-tenant pilot path for `pos-desktop-v1.0.0-alpha`:

- Ship **unsigned** Windows installer (SmartScreen "Unknown publisher" accepted for pilot).
- Ship with **existing placeholder icons** (regenerated cleaner: white DP on teal, rounded-rectangle outer, pure-disk tray icon).
- Fix three security critical findings that apply even for a single-tenant pilot: **C4** (insurance gateway fail-closed), **C5** (remove `tenant_id=1` fallback in `idempotency.py` + `devices.py`), **C6** (peppered HMAC-SHA256 for pharmacist PIN hashes).
- Defer cross-tenant hardening (C2/C3/H1/C7) to before onboarding customer #2 — tracked as follow-up issues.
- Reduce #477 DoD to the hardware the owner actually has on hand (USB scanner + 80mm thermal printer), deferring cash-drawer kick and QR-scanback-phone steps.

## Rationale

The security audit (2026-04-23) found 7 CRITICAL/HIGH items. Cross-tenant findings (C2/C3/H1) are theoretical for a single-pilot pharmacy but catastrophic at customer #2 — perfect split to fix now vs fix-before-expansion.

Insurance-gateway (C4) is the one that matters regardless of tenancy: the prior stub returned `success=True` for any non-empty insurance number, giving any cashier a one-field fraud path. Fixed: fails closed, cashier must take cash/card or capture the claim out-of-band.

Pharmacist PIN (C6) was unsalted SHA-256 — 4–6 digit PIN rainbow-tableable in milliseconds. Upgraded to HMAC-SHA256 peppered with `settings.secret_key`. A proper scrypt+salt migration is filed as follow-up before multi-tenant expansion.

Tenant-id fallback (C5) was silently defaulting to `1` when middleware missed setting the request state. Now fails with 401 "request missing tenant context" — a middleware regression surfaces immediately instead of silently mis-scoping idempotency keys or device proofs.

Code-signing deferred (#476 closed wontfix) because owner declined the $200–500/yr cost. Cheap upgrade paths (Azure Trusted Signing ~$10/mo, Certum OSS ~€25/yr) are documented in the closure comment.

## Tailored #477 smoke test (alpha DoD, pilot-hardware-reduced)

Hardware on-hand: **Windows PC + USB barcode scanner + 80mm thermal printer**. No cash drawer, no separate QR-scan phone.

### Install + boot
- [ ] Install `DataPulse-POS-1.0.0-alpha-Setup.exe` via NSIS wizard (SmartScreen "More info → Run anyway" expected on first install)
- [ ] App auto-launches to system tray on boot
- [ ] Tray icon renders (pure teal disk; "DP" letters would be illegible at 32px so they're dropped — tooltip shows "DataPulse POS")

### Shift open (D5)
- [ ] Open a shift with opening cash on a terminal → server accepts
- [ ] Second concurrent terminal open attempt is rejected
- [ ] Manager PIN override modal accepts a valid PIN for privileged actions

### Barcode scan + cart (D1, D2)
- [ ] Scan 10 items with the USB scanner → cart populates, total updates live
- [ ] On active SKU, ClinicalPanel (col 3) renders: counseling tip (cyan bubble, largest surface), live stock + nearest expiry + shelf location + margin, cross-sell with reason tags, generic alternatives with savings
- [ ] Items with no clinical data return 200 + empty panels (no crash, no 404 surfaced to cashier)

### Customer lookup + churn (D3)
- [ ] Type an Egyptian mobile (`01XXXXXXXXX`) → CustomerBar shows loyalty + credit + tier
- [ ] Matched customer with churn data → ChurnAlertCard (red) lists late refills
- [ ] No-match phone → inline create-customer affordance; no error toast

### Top status strip (D4)
- [ ] Green sync pill on left reflects online/offline state
- [ ] Gold commission pill updates after each confirmed sale
- [ ] Daily sales target trophy bar advances proportionally to shift sales

### Checkout + receipt (D0, C-series)
- [ ] Complete a **cash** transaction → CheckoutConfirmModal renders with totals
- [ ] Receipt prints on 80mm thermal printer marked `CONFIRMED`
- [ ] Printed receipt variants render correctly: **Sales** and **Delivery** (Insurance fails closed — verify cashier sees "Insurance payment gateway not yet configured" and falls back to cash/card)
- [ ] Receipt counseling block renders as inverted ink (only always-black chunk of receipt)
- [ ] Receipt QR + Code-128 barcode **visually present and correctly sized** (phone-scan verification deferred to beta)
- [ ] Cash drawer kick **not tested** — no drawer attached. Change-due amount **displayed on screen** correctly for the cashier to pay out manually
- [ ] Branding on invoice + receipt matches what's set via `NEXT_PUBLIC_POS_BRANCH_NAME` / `_ADDRESS` / `_TAX_NUMBER` env vars (no more hardcoded "Maadi" defaults)

### Offline / sync (K3 + sync engine)
- [ ] Unplug network → ring up 5 more transactions → all succeed, receipts print marked `PROVISIONAL — awaiting confirmation`, UI shows offline banner
- [ ] Plug network back in → queued transactions sync within 30s, banner flashes `synced`, history rows flip provisional → confirmed

### Reconciliation
- [ ] Simulate a queued transaction rejection → surfaces in `/sync-issues` page; retry / record-loss / corrective-void workflow; shift-close blocked until reconciled

### Shift close (D5)
- [ ] Close the shift with closing cash → variance calculated, shift summary prints
- [ ] Commission earned displayed on shift summary

### Restart + updater (K4)
- [ ] Restart the machine → app auto-launches to tray, checks for auto-update; update gated when queue non-empty

### Promotions (shipped pre-v9)
- [ ] Cashier-picked promotion via PromotionsModal applies discount at checkout; discount printed on receipt

### Deferred (gated on future hardware / integration)
- [ ] Cash-drawer kick signal — not tested (no drawer on hand)
- [ ] QR scan-back from receipt to transaction URL on a phone — visual presence verified only
- [ ] Insurance payment success path — gateway fails closed by design until real insurer API is wired
- [ ] Code-signing Digital Signatures tab — not applicable, shipped unsigned

## Follow-ups filed

- Live Twilio WhatsApp send (issue #671)
- TBD — multi-tenant repo predicate hardening (C2 — 15+ `_repo_*.py` methods need explicit `WHERE tenant_id = :tid`)
- TBD — `public.tenant_members` tenant predicate on `get_pharmacist_pin_hash` (C3)
- TBD — `pos.idempotency_keys` composite PK `(tenant_id, key)` migration (H1)
- TBD — scrypt + per-user salt for pharmacist PIN (proper C6 fix)
- TBD — layer-boundary cleanup: repos + services raising `HTTPException` (python-reviewer blocker)
- TBD — multi-tenant `tenant_branding` fetch to replace `NEXT_PUBLIC_POS_*` env var letterhead

## Test status

- 3259 unit tests pass, 32 skipped, after the C4/C5/C6 fixes
- Two test harnesses needed `request.state.tenant_id=1` middleware stubs to replace the prior silent fallback: `test_pos_device_verifier.py`, `test_pos_routes.py`

## Files touched

- `src/datapulse/pos/payment.py` — InsuranceGateway fails closed (C4)
- `src/datapulse/pos/idempotency.py` — fail fast on missing tenant context (C5)
- `src/datapulse/pos/devices.py` — fail fast on missing tenant context (C5)
- `src/datapulse/pos/pharmacist_verifier.py` — peppered HMAC-SHA256 for PIN hashing (C6)
- `tests/test_pos_payment.py` — insurance tests flipped to assert fail-closed
- `tests/test_pos_b7.py` — regression test that PIN hash ≠ plain SHA-256
- `tests/test_pos_device_verifier.py` — tenant middleware stub in `_make_app`
- `tests/test_pos_routes.py` — tenant middleware stub in `_make_app`
- `frontend/src/lib/pos-branding.ts` — new module; env-var-backed letterhead
- `frontend/src/app/(pos)/checkout/page.tsx` — use `getPosBranding()`
- `frontend/src/app/(pos)/drugs/page.tsx` — use `getPosBranding()`
- `pos-desktop/scripts/generate_icons.py` — committed regen script
- `pos-desktop/assets/{icon.ico,icon.png,tray.png}` — regenerated
