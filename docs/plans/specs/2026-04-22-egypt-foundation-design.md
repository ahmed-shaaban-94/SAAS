# Egypt-ready foundation — design spec

**Date:** 2026-04-22
**Bundle:** #604 (Egypt PMF)
**Spec:** 1 of 3 (this doc) · 2 is Paymob integration · 3 is InstaPay + compliance
**Estimated effort:** 2–3 weeks · 4 independently-reviewable PRs
**Status:** Design approved · ready for implementation plan

---

## 1 · Context and goal

DataPulse's 2026-04-22 strategic audit identified Egypt-market product-market-fit gaps as the highest-revenue-unlock initiative. The full Egypt PMF bundle (#604) covers payment providers (Paymob + InstaPay), Arabic i18n / RTL, and EGP pricing display. "Production-grade at Egyptian scale" is legitimately three specs of work; this spec is the enabling foundation.

**Goal of Spec 1:** ship every piece of infrastructure that makes shipping Specs 2 and 3 safe, without introducing any new external payment integration. At the end of Spec 1, the system has:

- A working Arabic UI (critical path) with RTL direction.
- Tenant-level currency + locale persistence.
- A `PaymentProvider` protocol so adding Paymob in Spec 2 is a plug-in, not a rewrite.
- EGP price display on the pricing page and billing dashboard.
- Auth0 locale claim threaded through to `UserClaims`.

Crucially, Spec 1 **does not take any money in EGP**. Egyptian-currency tenants are identified and shown Arabic EGP prices, but checkout returns a clear "Paymob integration coming soon" 503 until Spec 2 ships. This decoupling lets Spec 1 merge without vendor contracts or production credentials.

**Non-goals** (explicit, documented so they don't creep):

- Paymob integration (Spec 2).
- InstaPay integration (Spec 3).
- Egyptian tax invoicing / VAT compliance (Spec 3).
- KYC/AML pharmacy verification (Spec 3).
- Bilingual product names on `dim_product` (depends on Regulatory bundle #606).
- Full-Arabic translation of all 60 pages (separate translation initiative; Spec 1 covers critical path only).
- POS terminal Arabic UI (covered under POS Desktop v1.0 epic #474).
- Admin page translation (resellers, RBAC, scheduler — deferred).
- Print report at `/dashboard/report` (stays LTR English for launch).

---

## 2 · Current-state snapshot

Observed via grep/read during brainstorm, 2026-04-22:

| Area | State |
|---|---|
| `next-intl` | `^4.9.1` installed in `frontend/package.json`. `frontend/src/i18n/` directory exists. `frontend/messages/{en,ar}.json` exist but are stubs. |
| Locale switcher UI | Not present anywhere in the frontend. |
| `dir="rtl"` wiring | Not present. No Tailwind RTL plugin. |
| `BillingService` | Imports `StripeClient` directly. No provider abstraction. |
| `PlanLimits` | Hardcoded USD prices via `price_display: "$49/mo"` strings. No `price_egp` field. No `currency` field. |
| `bronze.tenants` | No `locale` or `currency` columns. |
| Auth0 claims | `get_current_user` reads `tenant_id`, `sub`, `email`, `roles`. Does not read `locale`. |
| Product Arabic names | `bronze.column_map` has English `material_desc` only; no separate Arabic column. Out of scope for Spec 1. |

---

## 3 · Architecture changes

### 3.1 Backend module diff

```
src/datapulse/
├── billing/
│   ├── provider.py        NEW    PaymentProvider Protocol (see §4.1)
│   ├── service.py         EDIT   inject providers: dict[str, PaymentProvider]; route by currency
│   ├── stripe_client.py   EDIT   formally implement PaymentProvider (no behavior change)
│   ├── plans.py           EDIT   PlanLimits gains price_egp (piastres) + price_currency_default
│   └── models.py          EDIT   CheckoutResponse gains optional currency + provider_name fields
├── api/
│   └── deps.py            EDIT   get_payment_provider() factory; get_billing_service wires provider dict
└── core/
    └── auth.py            EDIT   UserClaims TypedDict gains locale: str; get_current_user propagates it
```

### 3.2 Frontend module diff

```
frontend/
├── src/i18n/              EDIT   next-intl config: routing, getRequestConfig, defaultLocale
├── messages/
│   ├── en.json            EDIT   critical-path catalog filled out
│   └── ar.json            EDIT   critical-path catalog translated (see §5.3 method)
├── src/
│   ├── components/
│   │   ├── locale-switcher/
│   │   │   ├── index.tsx   NEW   sidebar-footer two-button toggle (EN / عربي)
│   │   │   └── index.test.tsx NEW
│   │   └── price-badge/
│   │       ├── index.tsx   NEW   renders formatted price for current tenant currency
│   │       └── index.test.tsx NEW
│   ├── lib/
│   │   └── currency.ts     NEW   formatPrice(amount, currency, locale) helper
│   ├── app/
│   │   ├── layout.tsx      EDIT   set dir={locale === 'ar' ? 'rtl' : 'ltr'}, lang={locale}
│   │   └── (pricing)/page.tsx EDIT   use <PriceBadge /> instead of hardcoded $ strings
│   └── dashboard/
│       └── sidebar-footer.tsx EDIT   mount <LocaleSwitcher /> beside existing theme toggle
└── tailwind.config.ts     EDIT   enable rtl: variant support (@tailwindcss/rtl or manual)
```

### 3.3 Database migration

**New migration:** `migrations/100_tenant_locale_currency.sql`

```sql
-- 100: Add locale + currency to bronze.tenants for Egypt PMF (#604 spec 1)
ALTER TABLE bronze.tenants
  ADD COLUMN IF NOT EXISTS locale   VARCHAR(10) NOT NULL DEFAULT 'en-US',
  ADD COLUMN IF NOT EXISTS currency CHAR(3)     NOT NULL DEFAULT 'USD';

-- No RLS change: these columns are not tenant-spanning. Existing
-- tenant_id-based policies on bronze.tenants already cover row access.
COMMENT ON COLUMN bronze.tenants.locale IS
  'BCP-47 tag; controls next-intl locale + RTL direction. Set from Auth0 claim on signup (#604).';
COMMENT ON COLUMN bronze.tenants.currency IS
  'ISO-4217; routes BillingService to the right PaymentProvider. USD=Stripe, EGP=Paymob (post spec 2) (#604).';
```

No backfill job needed — defaults preserve existing tenant behavior.

### 3.4 Auth0 action patch

Not code in this repo — a config change in Auth0 dashboard. Shipped as documentation:

- `docs/ops/auth0-locale-action.md` — one-liner Action snippet:
  ```js
  exports.onExecutePostLogin = async (event, api) => {
    if (event.user.user_metadata?.locale) {
      api.idToken.setCustomClaim('locale', event.user.user_metadata.locale);
      api.accessToken.setCustomClaim('locale', event.user.user_metadata.locale);
    }
  };
  ```
- `core/auth.py` reads `claims.get("locale", "en-US")` into `UserClaims["locale"]` with a safe default.

---

## 4 · Key design decisions

### 4.1 `PaymentProvider` protocol

```python
# src/datapulse/billing/provider.py
from typing import Protocol, runtime_checkable
from datapulse.billing.models import (
    CheckoutRequest, CheckoutResponse,
    PortalResponse, WebhookResult,
)

@runtime_checkable
class PaymentProvider(Protocol):
    """Contract every billing provider must satisfy.

    Kept sync to match existing StripeClient signature and because FastAPI
    handlers wrap these calls anyway — async buys nothing here. A provider
    is selected per-tenant-currency via ``get_payment_provider(currency)``.
    """

    name: str                    # "stripe" | "paymob" | "instapay"
    currencies: frozenset[str]   # e.g. {"USD"} or {"EGP"}

    def create_checkout_session(self, req: CheckoutRequest) -> CheckoutResponse: ...
    def create_portal_session(self, tenant_id: int) -> PortalResponse: ...
    def handle_webhook_event(self, payload: bytes, sig: str, secret: str) -> WebhookResult: ...
    def cancel_subscription(self, external_subscription_id: str) -> None: ...
```

`StripeClient` adds `name = "stripe"`, `currencies = frozenset({"USD"})`. No method body changes. `test_payment_provider_protocol.py` asserts `isinstance(StripeClient(...), PaymentProvider)` at runtime.

### 4.2 Provider routing inside `BillingService`

```python
# src/datapulse/billing/service.py (edited)
class BillingService:
    def __init__(
        self,
        repo: BillingRepository,
        providers: dict[str, PaymentProvider],   # CHANGED: was stripe_client
        *,
        price_to_plan: dict[str, str],
        base_url: str,
    ) -> None:
        self._repo = repo
        self._providers = providers               # keyed by ISO-4217
        ...

    def _provider_for(self, currency: str) -> PaymentProvider:
        p = self._providers.get(currency)
        if p is None:
            raise ProviderUnavailableError(
                f"No payment provider configured for {currency!r}. "
                "Contact support — Egyptian billing (EGP) is coming soon."
            )
        return p
```

`api/deps.get_billing_service` wires the dict; during Spec 1 it contains only `{"USD": StripeClient(...)}`. Egyptian tenants attempting checkout receive HTTP 503 with the friendly message above. This is deliberate — makes the EGP-capable surface area visible in staging for Spec 2 to test against.

### 4.3 Tenant currency determination

Three inputs, resolved in order:

1. **Signup wizard:** pre-fills `currency` from Auth0 `locale` claim (`ar-EG → EGP`, anything else → USD), shows the user a confirm toggle. User choice is authoritative.
2. **Admin override:** `/dashboard/settings/tenant` page has a two-field form (locale + currency) that admin roles can edit.
3. **Default on RBAC-bootstrap / legacy tenants:** `USD` + `en-US` via migration defaults.

Once set on `bronze.tenants`, the column is the source of truth for all downstream routing (Billing, PricingBadge, LocaleSwitcher default).

### 4.4 Locale switcher placement and flow

- **Where:** Sidebar footer, directly adjacent to the existing dark/light theme toggle (same spatial grouping, same interaction model — users already know to look there for preference toggles).
- **UI:** Two-button segmented control, not a dropdown. Two choices don't earn a dropdown.
  - Button 1: `EN` (English)
  - Button 2: `عربي` (Arabic)
- **Click behavior:** Writes the `NEXT_LOCALE` cookie (30-day expiry), triggers `router.refresh()` so next-intl picks up the new locale on the server side.
- **Also mirrored at:** `/dashboard/settings/tenant` — the "source of truth" page for users who prefer explicit settings.
- **First-visit resolution order:**
  1. `NEXT_LOCALE` cookie
  2. Auth0 `locale` claim
  3. Browser `Accept-Language` header
  4. Fallback `en-US`

### 4.5 Plan pricing data model

`PlanLimits` dataclass gains two fields:

```python
@dataclass(frozen=True)
class PlanLimits:
    ...existing fields...
    price_egp: int                         # piastres (1 EGP = 100 piastres)
    price_currency_default: Literal["USD", "EGP"]  # display fallback when tenant has no currency yet
```

**Why piastres and not `NUMERIC(18,4)`:** plan prices are catalog data (set by humans, not computed), integer piastres maps 1:1 to Stripe/Paymob integer-cents APIs, and avoids any float rounding in the display layer. The `price_display` string field is kept for backward-compat and now gets computed from `(price_egp, price_currency_default, locale)` via the shared `formatPrice` helper.

**Placeholder numbers (final numbers are a business decision):**

| Plan | USD/mo | EGP/mo (piastres) | EGP/mo (human) | Currency default |
|------|-------:|------------------:|---------------:|---|
| starter  | $0  | 0        | 0 EGP      | matches locale |
| pro      | $49 | 149 900  | 1,499 EGP  | matches locale |
| platform | $99 | 299 900  | 2,999 EGP  | matches locale |
| enterprise | Custom | Custom | Custom | matches locale |

These are placeholders close to current USD values at ~30-EGP-per-dollar — adjust in one follow-up PR after Finance confirms.

Plans stay Python-dataclass (hardcoded) rather than moving to a DB table. DB-driven plans are a separate concern (runtime pricing experiments, A/B testing) and are explicitly out of scope.

### 4.6 Arabic / RTL scope

**In-scope critical path (≈15 screens, ≈400 translation strings):**

- Login + signup + tenant-onboarding wizard
- Sidebar nav labels + footer
- Dashboard home (KPI tiles, "welcome back" copy, main nav cards)
- Billing page (plan cards, invoice history, subscription status, checkout error messages)
- Settings → tenant page (locale + currency form)
- Marketing landing page (`(marketing)` — headline, CTAs, feature bullets only)
- Global toast + error messages

**Out-of-scope for Spec 1 (deferred translation):**

- Deep dashboard pages: scenarios, forecasting, anomalies, AI-light insights, explore, gamification, annotations, targets
- POS terminal UI (separate POS Desktop epic)
- Admin-only pages: resellers, RBAC, scheduler, control_center
- Print report `/dashboard/report`
- E2E test fixtures (Playwright specs stay English-only)

Deferred pages will render their English text inside the RTL layout. Mildly ugly but clearly flags "not yet translated" — better than blocking Spec 1 on a 60-page translation.

### 4.7 Translation method (Spec 1)

- **GPT-4 / Claude translation of `en.json` → `ar.json`**, reviewed line-by-line by the Arabic-speaking team member before merge.
- Professional translator engagement is deferred to Spec 3 (compliance bundle). Spec 1 optimizes for speed-to-launch; polish is a follow-up PR, not a blocker.
- Right-to-left idioms (e.g. numeric formatting, date ordering) handled by next-intl + a thin `lib/currency.ts` helper, not by manual string editing.

### 4.8 Tailwind RTL

- Add `@tailwindcss/rtl` plugin to `tailwind.config.ts`.
- Adds `rtl:` and `ltr:` variants so authors can write `class="pl-4 rtl:pr-4 rtl:pl-0"` where needed. Most components work without changes because Tailwind's logical properties (`ps-4`, `pe-4` = padding-start / padding-end) auto-flip based on `dir`.
- Audit sweep on the critical path: ensure chevron icons, breadcrumb `/` separators, and numeric charts use logical positioning. Do NOT force RTL on chart axes (Recharts axis direction stays LTR by data contract — EGP numbers still read left-to-right as numbers).

---

## 5 · Data flow

### 5.1 Signup → currency selection

```
User hits /signup
 └─> Auth0 login (may carry user_metadata.locale)
 └─> Auth0 Action sets custom claim 'locale' on the id/access token
 └─> Frontend reads locale from NextAuth session
 └─> Onboarding wizard step 'Choose your region':
      ├─ Pre-fills locale = session.locale
      ├─ Pre-fills currency = locale.startsWith('ar-EG') ? 'EGP' : 'USD'
      └─ User confirms or overrides, then POST /tenants/onboard
 └─> API: bronze.tenants INSERT with (locale, currency)
 └─> Redirect to /dashboard (already rendered in chosen locale + dir)
```

### 5.2 Checkout routing (Spec 1 behavior)

```
User clicks 'Upgrade to Pro' on /dashboard/billing
 └─> POST /api/v1/billing/checkout { price_id, success_url, cancel_url }
 └─> BillingService.create_checkout_session(tenant_id):
      ├─ Look up tenant.currency from bronze.tenants
      ├─ provider = self._provider_for(tenant.currency)
      │   └─ USD tenant:  StripeClient → Stripe Checkout URL
      │   └─ EGP tenant:  ProviderUnavailableError
      └─ Return CheckoutResponse with url
 └─> 503 for EGP path, rendered in Arabic by a dedicated error page
```

After Spec 2 ships, the EGP path returns a Paymob iframe URL without any changes to Spec 1 code.

### 5.3 Locale-switcher click

```
User clicks 'عربي' in sidebar footer
 └─> LocaleSwitcher.handleClick('ar'):
      ├─ document.cookie = 'NEXT_LOCALE=ar; Path=/; Max-Age=2592000'
      ├─ router.refresh()
 └─> Next.js re-renders server components:
      ├─ getRequestConfig reads NEXT_LOCALE cookie → ar
      ├─ Layout sets dir="rtl" lang="ar"
      ├─ Messages loaded from messages/ar.json
 └─> UI appears in Arabic without page navigation
```

---

## 6 · Testing strategy

### 6.1 Backend unit tests (new)

- `tests/test_payment_provider_protocol.py` — `isinstance(StripeClient(...), PaymentProvider) is True`; placeholder-Paymob stub also satisfies the protocol at runtime.
- `tests/test_billing_service_routing.py` — `BillingService(..., providers={"USD": stub})` routes USD tenant to stub, raises `ProviderUnavailableError` for EGP tenant.
- `tests/test_tenant_locale_currency_migration.py` — after migration, `bronze.tenants` has both columns with expected defaults (integration-mark, real DB).
- `tests/test_auth_locale_claim.py` — `get_current_user` with a JWT bearing `locale=ar-EG` returns `UserClaims["locale"] == "ar-EG"`; missing claim → `en-US` default.

### 6.2 Backend existing tests (update)

- `tests/test_billing_webhook.py` and `tests/test_billing_plans_platform.py` — update constructor calls from `stripe_client=...` to `providers={"USD": stripe_client}`. Pure signature churn; no coverage loss.

### 6.3 Frontend unit tests (new)

- `components/locale-switcher/index.test.tsx` — click sets cookie; click again on same locale is a no-op.
- `components/price-badge/index.test.tsx` — `(4900, 'USD', 'en-US')` → `$49.00`; `(149900, 'EGP', 'ar-EG')` → `١٬٤٩٩ ج.م` (Arabic-Indic digits + EGP suffix).
- `lib/currency.test.ts` — `formatPrice` edge cases: 0, negative, non-ISO currency string.

### 6.4 Frontend E2E (update)

- Extend `frontend/e2e/dashboard.spec.ts` with a locale-toggle variant:
  - Set `NEXT_LOCALE=ar` cookie before `goto('/dashboard')`.
  - Assert `html[dir="rtl"]` and `html[lang="ar"]`.
  - Assert one sidebar nav label renders in Arabic from `ar.json`.
- No new spec files — reuse the existing dashboard spec so CI stays within its time budget.

### 6.5 Visual regression (optional, deferred)

Not in scope — Spec 1's visual changes are RTL-layout flips, which are easier to eyeball than to snapshot-regression. Consider Percy / Chromatic in a future spec if design team asks.

---

## 7 · Error handling

| Scenario | Surface | Observability |
|---|---|---|
| Signup: Auth0 has no `locale` claim | Wizard falls back to browser `Accept-Language`, ultimately `en-US`. Never crashes. | `structlog.warning("auth0_locale_claim_missing", sub=...)` rate-limited via existing `_log_dev_tenant_fallback_once` pattern. |
| Checkout: no provider for tenant currency | HTTP 503 `{detail: "Payments in EGP are coming soon..."}` | `structlog.warning("payment_provider_unavailable", currency=tenant.currency, tenant_id=...)`. |
| Locale switcher clicked but message catalog missing | Next-intl falls back to `en-US` catalog. UI text stays English, rest of layout stays RTL. | `structlog.error("locale_catalog_missing", locale=...)` — alert to `#datapulse-alerts` via existing notifications helper. |
| Migration 100 applied twice | `ADD COLUMN IF NOT EXISTS` makes it idempotent — no-op on second apply. | No special handling. |
| Admin changes tenant.currency while user has active Stripe subscription | For Spec 1: UI allows the change; checkout for the old currency is still routed to the old provider. Document the caveat inline in the settings form. | No automation — Spec 2 handles real provider migration. |

---

## 8 · Observability

No new metrics/spans in Spec 1 — refactor only. Existing `billing_*` metrics continue to fire. Spec 2 introduces Paymob-specific metrics; Spec 1 stays silent on that front to keep the PR surface small.

Added structured-log events (all using existing `structlog`):

- `tenant_currency_set` (INFO) — on signup wizard submission
- `locale_switched` (INFO) — on locale-switcher click
- `auth0_locale_claim_missing` (WARN, rate-limited) — when Auth0 doesn't send the claim
- `payment_provider_unavailable` (WARN) — when Egyptian checkout hits the 503
- `locale_catalog_missing` (ERROR) — when a locale is requested whose JSON catalog doesn't exist

---

## 9 · Rollout plan — 4 independently-reviewable PRs

Order matters; each PR leaves `main` in a shippable state.

### PR 1 · Migration + tenants backfill (< 1 day)

- `migrations/100_tenant_locale_currency.sql`
- `tests/test_tenant_locale_currency_migration.py` (integration-mark)
- No Python/frontend changes.
- **Acceptance:** migration applies cleanly; existing tenants stay on defaults; new tenants get the defaults; re-apply is no-op.

### PR 2 · `PaymentProvider` protocol + `StripeClient` formal implementation (~2 days)

- `src/datapulse/billing/provider.py` (new, ~30 LOC)
- `src/datapulse/billing/stripe_client.py` (edit: `name`, `currencies` class attrs)
- `src/datapulse/billing/service.py` (edit: `providers: dict[str, PaymentProvider]` constructor)
- `src/datapulse/api/deps.py` (edit: `get_billing_service` wires `{"USD": StripeClient(...)}`)
- `tests/test_payment_provider_protocol.py` (new)
- `tests/test_billing_service_routing.py` (new)
- Update existing billing tests to new constructor signature.
- **Acceptance:** all existing billing routes still work unchanged; Egyptian tenant attempting checkout gets 503 with friendly message; `isinstance(StripeClient(...), PaymentProvider) is True`.

### PR 3 · Backend plumbing for currency + locale awareness (~2 days)

- `src/datapulse/billing/plans.py` — `PlanLimits.price_egp`, `price_currency_default`, placeholder numbers per §4.5.
- `src/datapulse/core/auth.py` — `UserClaims["locale"]`, `get_current_user` reads claim with default.
- `tests/test_auth_locale_claim.py` (new).
- Existing auth tests updated for the new `UserClaims` field.
- `docs/ops/auth0-locale-action.md` — one-page Action template for manual Auth0 dashboard config.
- **Acceptance:** auth tests pass; plans export both USD and EGP; Auth0 doc exists and is accurate.

### PR 4 · Frontend i18n end-to-end (~5 days)

Largest PR — justifies its size because i18n is intrinsically a cross-cutting change.

- `frontend/src/i18n/` — finished next-intl config (routing, getRequestConfig).
- `frontend/messages/en.json` — critical-path strings extracted.
- `frontend/messages/ar.json` — Arabic translation, team-reviewed.
- `frontend/tailwind.config.ts` — `@tailwindcss/rtl` wired.
- `frontend/src/app/layout.tsx` — `dir` + `lang` on `<html>`.
- `frontend/src/components/locale-switcher/` (new).
- `frontend/src/components/price-badge/` (new).
- `frontend/src/lib/currency.ts` (new).
- `frontend/src/app/(pricing)/page.tsx` — use `<PriceBadge />`.
- `frontend/src/app/dashboard/settings/tenant/page.tsx` — locale + currency form (new minor UI).
- `frontend/e2e/dashboard.spec.ts` — RTL variant.
- Unit tests for locale switcher + price badge.
- **Acceptance:** cashier with no English can navigate login → dashboard → billing → settings in Arabic; locale switcher persists across page refresh; Playwright RTL variant passes; no English strings leak on the critical path; no untranslated pages crash (they fall back to English inside RTL layout).

---

## 10 · Dependencies and risks

### 10.1 External / human dependencies

- **Auth0 Action deployment** — section §3.4. Owner must paste the snippet into Auth0 dashboard before PR 3's behavior is fully observable in prod. If it isn't deployed, backend still works (falls back to `en-US`) — not a hard blocker.
- **Arabic translation review** — need at least one Arabic-speaking reviewer on PR 4 before merge. Not Claude's role.
- **Finance sign-off on placeholder EGP prices** — can land with placeholders and adjust in a small follow-up PR; not PR-4-blocking.

### 10.2 Technical risks + mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| `@tailwindcss/rtl` conflicts with existing custom component classes | Medium | Audit sweep on critical-path pages during PR 4; use logical properties (`ps-*` / `pe-*`) proactively. |
| Recharts (analytics charts) lays out wrong under RTL | Medium | Pre-test PR 4 with a Playwright visual snapshot of one chart; document which chart props to keep LTR. |
| Users toggle locale but subscription invoice stays in one currency | Low | Document "locale is cosmetic, currency is contractual" in the settings form. Spec 2/3 handle migration. |
| Existing Playwright E2E specs fail under `NEXT_LOCALE=ar` due to hardcoded English selectors | Medium | Spec 1 only adds the RTL variant to `dashboard.spec.ts`; other specs stay English. |
| Migration 100 conflicts with concurrent work on `bronze.tenants` | Low | `ADD COLUMN IF NOT EXISTS` is idempotent and non-locking for short durations; still applied during low-traffic window. |

---

## 11 · Done-when

Spec 1 is complete when **all four PRs are merged** and the following checklist is signed off:

- [ ] Migration 100 live in prod; `bronze.tenants` has `locale` + `currency`.
- [ ] `PaymentProvider` protocol exists; `StripeClient` satisfies it; `BillingService` takes providers dict.
- [ ] `PlanLimits` exposes both USD and EGP amounts.
- [ ] `UserClaims` exposes `locale`; `get_current_user` reads it.
- [ ] Auth0 Action snippet documented in `docs/ops/`.
- [ ] Frontend: critical-path Arabic translation reviewed + merged; `dir="rtl"` works; locale switcher persists.
- [ ] New unit + integration + E2E tests passing in CI.
- [ ] Ruff clean; tsc clean; Lighthouse no regression on critical path.
- [ ] CHANGELOG entry describing the launch.
- [ ] `#604` bundle body updated with ✅ for the four Spec-1 subtasks; Spec 2 / Spec 3 line items stay unchecked.

---

## 12 · Appendix — message-catalog seed example

Illustrative only (full catalog lands in PR 4):

```json
// frontend/messages/en.json
{
  "app.name": "DataPulse",
  "sidebar.dashboard": "Dashboard",
  "sidebar.billing": "Billing",
  "sidebar.settings": "Settings",
  "billing.upgrade_cta": "Upgrade to Pro",
  "billing.plan.pro.title": "Pro",
  "billing.plan.pro.tagline": "For growing pharmacies",
  "billing.currency.unavailable_egp": "Payments in EGP are coming soon. Contact support."
}

// frontend/messages/ar.json
{
  "app.name": "داتا بلس",
  "sidebar.dashboard": "لوحة التحكم",
  "sidebar.billing": "الفواتير",
  "sidebar.settings": "الإعدادات",
  "billing.upgrade_cta": "ترقية إلى Pro",
  "billing.plan.pro.title": "Pro",
  "billing.plan.pro.tagline": "للصيدليات النامية",
  "billing.currency.unavailable_egp": "الدفع بالجنيه المصري قريبًا. تواصل مع الدعم."
}
```
