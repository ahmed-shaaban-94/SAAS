# Handoff: DataPulse Pharmacy POS

## Overview
High-fidelity prototype of a pharmacy point-of-sale terminal for DataPulse — an Egyptian pharmacy chain. Covers the full cashier workflow: scan-to-cart, four payment methods (cash / card / insurance / voucher), sync-issue reconciliation, shift close, a searchable inventory (Drugs) tab with quantity-aware add-to-cart, a printable stocktaking worksheet, and a full A4 customer tax invoice. Bilingual (Arabic RTL default + English LTR).

## About the Design Files
The files in this bundle are **design references created in HTML** — React prototypes showing the intended look, behavior, keyboard model, and copy. They are **not production code to copy directly**. The task is to **recreate these HTML designs in your target codebase** using its existing patterns (component library, state management, i18n, routing). If no environment exists yet, pick the most appropriate stack for the project and implement there.

## Fidelity
**High-fidelity (hifi).** All colors, typography, spacing, radii, shadows, keyboard shortcuts, and copy are final. Recreate pixel-for-pixel using your component library.

## Screens / Views

### 1. Terminal (F1)
Primary sales screen. Two-column layout (≈ 1.45fr / 1fr).
- **Left:** scan bar (with animated cyan scan-pulse) → 3×3 Quick Pick grid (press 1–9) → Cart table with numbered rows, per-line qty steppers, hairline dividers, amber rail + "queued" badge on unsynced lines.
- **Right:** Totals Hero (Fraunces italic grand total with cyan glow + VAT/discount/voucher/coverage chips) → Keypad v2 (3×4 numeric + live "last key" indicator + shortcut legend grid) → Payment Panel v2 (2×2 method tiles: Cash/Card/Insurance/Voucher, each with F-key badge, side accent rail when active) → active-method detail strip (cash tendered + change + EGP denomination breakdown; card pinpad status; insurer split; voucher validity) → large Charge button (cyan gradient, shows total + Enter kbd).

### 2. Drugs (F4)
Searchable inventory with quantity-aware add-to-cart.
- **Left:** Search bar (by name / SKU / category / manufacturer, `/` focuses) with filter chips (All / Low / Out / Rx / OTC) and a **"Stocktaking sheet" button (F6)** styled as a purple pill at end of filter row → sortable data table (Item, SKU, On-hand, Price, Add Qty, Add).
- **Rows:** stock pill color-coded (out=red, low=amber, watch=gold, ok=green) with qty + reorder point; qty stepper per row; disabled Add when out of stock.
- **Right sidebar:** Stock Snapshot (Fraunces italic on-hand value + 4 stat tiles) → Focused Drug detail card (batch / expiry / shelf / SKU + Add-to-cart CTA) → "Cart" link back to Terminal.
- **Keyboard:** `/` focus search, ↑/↓ navigate, Enter adds top result.

### 3. Sync Issues (F2)
Reconciliation list. Rejected transactions with reason tags (PRICE_MISMATCH, STOCK_NEGATIVE, EXPIRED_VOUCHER, INSURANCE_REJECT, DUPLICATE_BARCODE). Each row offers Override / Loss / Void actions.

### 4. Shift Close (F3)
Thermal-receipt-styled summary: opening float, cash sales, expected cash, counted cash input, variance. Print button.

### 5. Stocktaking Modal (F6 from Drugs)
**Printable A4 blank-count worksheet.**
- Off-white #fbfaf7 paper, letterhead with pharmacy name + address + CR number, doc number (`STK-YYMMDD-NN`), date.
- Meta grid: Counted by / Witness / Date-Time / Aisle / Temperature / Shift #.
- Table columns: # · Shelf · Barcode · Item · Batch · Expiry · System qty · **Counted** (blank) · **Δ** (blank) · **✓** (blank).
- Totals row (SKU count + system value).
- Instructions block + two signature lines (Counter / Supervisor).
- `window.print()` trigger — @media print strips dark chrome, emits B&W A4.

### 6. Invoice Modal (auto-opens after Charge)
**Customer-facing A4 tax invoice.**
- Navy gradient ribbon (#0b1a29 → #163452) with cyan glow orb, Fraunces italic "DataPulse Pharmacy" wordmark, invoice number (`INV-YYMMDD-####`), date/time.
- Three beige meta blocks: **Issued by** (branch + address + tax no. 428-893-011) · **Customer** (walk-in or insurer + coverage%) · **Transaction** (cashier, method, reference).
- Itemized table (navy header, zebra rows): # · SKU · Description (with "unit price incl. VAT" subline) · Qty · Unit ex-VAT · VAT 14% · Line total.
- **Totals box** (tinted #f1ede4 with navy border): Subtotal ex-VAT · VAT · Discounts · Insurer pays · heavy rule · **grand total in large Fraunces italic #0b1a29**.
- Notes column (VAT-inclusive, return policy, retain-for-claims).
- Three signature lines: Cashier (prefilled Fraunces italic) · Pharmacy stamp · Customer.
- Printable via `window.print()`.

## Interactions & Behavior
- **Keyboard-first:** F1–F4 tabs; F5 promos; F6 stocktaking; F7/F12 voucher; F9–F11 payment methods; `/` search; `1–9` Quick Pick; Enter = charge or add-top-result; Esc closes modals.
- **Charge flow:** Click Charge (or Enter) → invoice modal opens with snapshot of cart/totals/method → cart clears → print or close.
- **Offline mode:** top bar shows amber "Provisional" + queue depth; new cart lines get amber rail + "QUEUED" pill; diagonal amber rail runs down content left edge.
- **Scan toast:** bottom-left pill, auto-dismiss 1.6s, cyan glow, animates up.
- **Animations:** dpRowEnter (cart row fade-up 220ms), dpScan (scan bar pulse 2.6s), dpSlideUp (toast 220ms cubic-bezier).

## State Management
- Persisted to localStorage: `lang`, `online`, `cartPreset`, `screen`, `openModal` (Tweaks-controlled).
- Session: `cart[]` (lineId, sku, name, price, qty, vatRate, synced), `voucher`, `promo`, `insurance`, `activePayment`, `scanToast`, `lastKey`, `lastReceipt` (snapshot for invoice).
- Invoice is derived from `lastReceipt` — invoice can be reopened/reprinted after charge.

## Design Tokens
**Colors**
- Surface: `#050e17` (bg), `#081826` cards, `#163452` gradient top
- Ink: `#e8ecf2`, `#b8c0cc`, `#7a8494`, `#3f4a5a`
- Lines: `rgba(255,255,255,0.06)` / `rgba(255,255,255,0.12)` strong
- Accent cyan: `#00c7f2` / hi `#5cdfff`
- Green: `#1dd48b` · Amber: `#ffab3d` · Red: `#ff7b7b` · Purple: `#7467f8`
- Paper (print): `#fbfaf7` body, `#0b1a29` ink, `#f1ede4` totals panel, `#f4f4f4` zebra

**Typography**
- UI body: Inter (weights 400/500/600/700)
- Arabic: IBM Plex Sans Arabic
- Display/italic: Fraunces italic (grand totals, invoice title, signature lines)
- Mono: JetBrains Mono (SKUs, barcodes, numbers, timestamps, kbd chips)

**Spacing / radii**
- Container padding: 14 · Card padding: 12–16 · Row padding: 10–14px vertical
- Radii: 6 (pills), 8 (buttons), 10–14 (cards/panels), 999 (chips)

**Shadows / glow**
- Cyan glow: `0 0 24px rgba(0,199,242,0.35)`
- Card: `0 0 0 1px rgba(0,199,242,0.12), 0 0 28px rgba(0,199,242,0.1)`

## Assets
No bitmap assets. All iconography is inline SVG. Logos are CSS radial-gradients. Fonts via Google Fonts (Fraunces, JetBrains Mono, IBM Plex Sans Arabic) + Inter.

## Files
All in `frames/pos/`:
- `app_v2.jsx` — root component, routing, modal coordination, charge flow
- `shell.jsx` — TopBar (brand, pulse line, queue chip, cashier/time, tabs)
- `terminal_v2.jsx` — Terminal screen + all payment sub-components
- `drugs.jsx` — Drugs tab (search + table + sidebar)
- `stocktaking.jsx` — printable worksheet modal
- `invoice.jsx` — printable tax invoice modal
- `modals.jsx` — voucher / promo / insurance
- `sync.jsx` — Sync Issues screen
- `shift.jsx` — Shift Close
- `tweaks.jsx` — runtime design tweaks panel
- `i18n.jsx` — all strings (ar / en)
- `data.jsx` — catalog, stock (STOCK map), promos, insurers, vouchers, computeTotals
- `POS Terminal v2.html` — entry point with global CSS and script graph
