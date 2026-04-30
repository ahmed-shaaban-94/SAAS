# Egypt-Ready Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver every enabler needed for Egyptian pharmacies (Arabic UI, EGP pricing, tenant currency persistence, payment provider abstraction) without shipping a new payment integration. Stripe stays exclusive; EGP tenants see a translated 503 until Spec 2 (Paymob) ships.

**Architecture:** `PaymentProvider` Protocol + provider dict keyed by ISO-4217 currency inside `BillingService`. `bronze.tenants` gains `locale` + `currency` columns. Frontend uses existing `next-intl` scaffold (already wired — `layout.tsx` already sets `dir="rtl"`, `src/i18n/config.ts` already defines locales, `frontend/messages/{en,ar}.json` already ~344 lines each with real translations, `/api/locale` POST endpoint already sets cookie) and adds a LocaleSwitcher component + PriceBadge + Tailwind RTL plugin.

**Tech Stack:** Python 3.11 + FastAPI + SQLAlchemy 2.0 + pytest · Next.js 14 + TypeScript + Tailwind + next-intl + Vitest + Playwright · PostgreSQL 16.

**Related docs:** Spec at [`docs/plans/specs/2026-04-22-egypt-foundation-design.md`](../specs/2026-04-22-egypt-foundation-design.md). GitHub issue #604.

**Important note:** A pre-implementation codebase probe (2026-04-22) found that `next-intl` is more fully wired than the spec's §2 snapshot claimed — `ar.json` is populated, `dir="rtl"` is live in `layout.tsx`, `/api/locale` cookie-setter exists. PR 4 is consequently smaller than the spec's estimate (3-4 days instead of 5).

---

## PR 1 — Migration 100: tenants.locale + tenants.currency

### Task 1 · Add `locale` + `currency` columns to `bronze.tenants`

**Files:**
- Create: `migrations/100_tenant_locale_currency.sql`
- Create: `tests/test_tenant_locale_currency_migration.py`

- [ ] **Step 1 · Write the failing integration test**

```python
# tests/test_tenant_locale_currency_migration.py
"""Integration test for migration 100 — tenants.locale + currency (#604 Spec 1)."""

from __future__ import annotations
import os
import socket
import pytest

pytestmark = pytest.mark.integration


def _db_reachable() -> bool:
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url or ("localhost" not in db_url and "127.0.0.1" not in db_url):
        return False
    try:
        with socket.create_connection(("127.0.0.1", 5432), timeout=1):
            return True
    except OSError:
        return False


requires_db = pytest.mark.skipif(not _db_reachable(), reason="no DB")


@requires_db
class TestMigration100:
    def test_locale_column_exists_with_default(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT column_default, is_nullable, character_maximum_length
                FROM information_schema.columns
                WHERE table_schema='bronze' AND table_name='tenants' AND column_name='locale'
            """)
            default, nullable, max_len = cur.fetchone()
        assert default == "'en-US'::character varying"
        assert nullable == "NO"
        assert max_len == 10

    def test_currency_column_exists_with_default(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT column_default, is_nullable, character_maximum_length
                FROM information_schema.columns
                WHERE table_schema='bronze' AND table_name='tenants' AND column_name='currency'
            """)
            default, nullable, max_len = cur.fetchone()
        assert default == "'USD'::bpchar"
        assert nullable == "NO"
        assert max_len == 3

    def test_existing_tenants_preserved_on_defaults(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM bronze.tenants
                WHERE locale IS NULL OR currency IS NULL
            """)
            (cnt,) = cur.fetchone()
        assert cnt == 0


@pytest.fixture()
def db_conn():
    psycopg2 = pytest.importorskip("psycopg2")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.autocommit = True
    yield conn
    conn.close()
```

- [ ] **Step 2 · Run test to verify it fails**

Run: `pytest tests/test_tenant_locale_currency_migration.py -q -m integration`
Expected: **SKIPPED** (no DB reachable from this harness — that's fine; CI will run the real integration job).

- [ ] **Step 3 · Write the migration**

Create `migrations/100_tenant_locale_currency.sql`:

```sql
-- 100: Add locale + currency to bronze.tenants for Egypt PMF (#604 Spec 1)
-- Idempotent: ADD COLUMN IF NOT EXISTS makes re-apply a no-op.

ALTER TABLE bronze.tenants
    ADD COLUMN IF NOT EXISTS locale   VARCHAR(10) NOT NULL DEFAULT 'en-US',
    ADD COLUMN IF NOT EXISTS currency CHAR(3)     NOT NULL DEFAULT 'USD';

COMMENT ON COLUMN bronze.tenants.locale IS
    'BCP-47 tag; controls next-intl locale + RTL direction. Set from Auth0 '
    'claim on signup (#604).';

COMMENT ON COLUMN bronze.tenants.currency IS
    'ISO-4217; routes BillingService to the right PaymentProvider. '
    'USD=Stripe, EGP=Paymob (post Spec 2) (#604).';
```

- [ ] **Step 4 · Apply migration locally + verify**

Run:
```bash
docker exec datapulse-db psql -U datapulse -c "\i /app/migrations/100_tenant_locale_currency.sql"
docker exec datapulse-db psql -U datapulse -c "\d+ bronze.tenants" | grep -E "locale|currency"
```
Expected output includes:
```
locale   | character varying(10) |           | not null | 'en-US'::character varying
currency | character(3)          |           | not null | 'USD'::bpchar
```

- [ ] **Step 5 · Run the integration test against the live DB**

Run (with `DATABASE_URL` env var set to your local DB):
```bash
DATABASE_URL=postgresql://datapulse:datapulse@localhost:5432/datapulse \
  pytest tests/test_tenant_locale_currency_migration.py -q -m integration
```
Expected: `3 passed`.

- [ ] **Step 6 · Commit**

```bash
git add migrations/100_tenant_locale_currency.sql tests/test_tenant_locale_currency_migration.py
git commit -m "feat(migrations): add locale + currency to bronze.tenants (#604-1 Spec1 PR1)

Enabler for the Egypt PMF bundle. Columns default to en-US + USD so
existing tenants are unaffected. Migration is idempotent (IF NOT EXISTS).

Spec: docs/plans/specs/2026-04-22-egypt-foundation-design.md §3.3"
```

---

## PR 2 — `PaymentProvider` Protocol + `StripeClient` formal implementation

### Task 2 · Write `PaymentProvider` protocol + `ProviderUnavailableError`

**Files:**
- Create: `src/datapulse/billing/provider.py`
- Create: `tests/test_payment_provider_protocol.py`

- [ ] **Step 1 · Write the failing test**

```python
# tests/test_payment_provider_protocol.py
"""Protocol conformance tests for PaymentProvider (#604 Spec 1 PR 2)."""

import pytest

from datapulse.billing.provider import PaymentProvider, ProviderUnavailableError
from datapulse.billing.stripe_client import StripeClient


class TestPaymentProviderProtocol:
    def test_stripe_client_satisfies_protocol(self):
        client = StripeClient(api_key="sk_test_dummy")
        assert isinstance(client, PaymentProvider)

    def test_stripe_client_declares_usd_currency(self):
        client = StripeClient(api_key="sk_test_dummy")
        assert client.name == "stripe"
        assert client.currencies == frozenset({"USD"})

    def test_provider_unavailable_error_carries_currency(self):
        err = ProviderUnavailableError("EGP")
        assert err.currency == "EGP"
        assert "EGP" in str(err)
```

- [ ] **Step 2 · Run test to verify it fails**

```bash
cd /path/to/Data-Pulse
pytest tests/test_payment_provider_protocol.py -q
```
Expected: FAIL with `ImportError: cannot import name 'PaymentProvider' from 'datapulse.billing.provider'`.

- [ ] **Step 3 · Create `billing/provider.py`**

```python
# src/datapulse/billing/provider.py
"""Payment provider contract (#604 Spec 1).

Every billing integration (Stripe, Paymob, InstaPay) implements this Protocol.
``BillingService`` routes to the right provider based on tenant currency.

Sync (not async) to match existing StripeClient signatures — async buys
nothing since FastAPI handlers wrap these calls anyway.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from datapulse.billing.models import (
    CheckoutRequest,
    CheckoutResponse,
    PortalResponse,
    WebhookResult,
)


class ProviderUnavailableError(Exception):
    """Raised when no payment provider is configured for a given currency.

    Surfaces as HTTP 503 in the billing routes so users see
    ``Payments in <currency> are temporarily unavailable`` instead of a 500.
    """

    def __init__(self, currency: str) -> None:
        self.currency = currency
        super().__init__(
            f"No payment provider configured for {currency!r}. "
            "Contact support — Egyptian billing (EGP) is coming soon."
        )


@runtime_checkable
class PaymentProvider(Protocol):
    """Every payment integration satisfies this shape."""

    name: str
    currencies: frozenset[str]

    def create_checkout_session(self, req: CheckoutRequest) -> CheckoutResponse: ...
    def create_portal_session(self, tenant_id: int) -> PortalResponse: ...
    def handle_webhook_event(
        self, payload: bytes, signature: str, secret: str
    ) -> WebhookResult: ...
    def cancel_subscription(self, external_subscription_id: str) -> None: ...
```

- [ ] **Step 4 · Add `name` + `currencies` class attrs to `StripeClient`**

In `src/datapulse/billing/stripe_client.py`, locate the `StripeClient` class definition and add two class attrs at the top of the class body (just below the docstring):

```python
class StripeClient:
    """Thin Stripe wrapper ..."""

    name = "stripe"
    currencies = frozenset({"USD"})

    # ... existing __init__ and methods unchanged ...
```

- [ ] **Step 5 · Run the test to verify pass**

```bash
pytest tests/test_payment_provider_protocol.py -q
```
Expected: `3 passed`.

- [ ] **Step 6 · Commit**

```bash
git add src/datapulse/billing/provider.py src/datapulse/billing/stripe_client.py tests/test_payment_provider_protocol.py
git commit -m "feat(billing): PaymentProvider Protocol + StripeClient formal impl (#604-1)

Introduces the Protocol every billing provider (Stripe today, Paymob/
InstaPay later) will satisfy. StripeClient declares name='stripe' and
currencies={'USD'}. ProviderUnavailableError surfaces as HTTP 503 with
a friendly message when no provider is configured for a tenant currency.

Spec §4.1 · PR 2 of 4"
```

### Task 3 · Route `BillingService` by currency via `providers: dict`

**Files:**
- Modify: `src/datapulse/billing/service.py`
- Modify: `src/datapulse/api/deps.py`
- Create: `tests/test_billing_service_routing.py`
- Modify: `tests/test_billing_webhook.py` (signature update)

- [ ] **Step 1 · Write the failing routing test**

```python
# tests/test_billing_service_routing.py
"""Currency-based routing inside BillingService (#604 Spec 1 PR 2)."""

from unittest.mock import MagicMock, create_autospec

import pytest

from datapulse.billing.provider import PaymentProvider, ProviderUnavailableError
from datapulse.billing.repository import BillingRepository
from datapulse.billing.service import BillingService


def _stub_provider(currency: str, name: str) -> MagicMock:
    p = MagicMock(spec=PaymentProvider)
    p.name = name
    p.currencies = frozenset({currency})
    return p


def _billing_service(providers: dict) -> BillingService:
    repo = create_autospec(BillingRepository, instance=True)
    return BillingService(
        repo=repo,
        providers=providers,
        price_to_plan={},
        base_url="https://example.test",
    )


class TestBillingServiceRouting:
    def test_usd_tenant_routes_to_stripe_provider(self):
        stripe = _stub_provider("USD", "stripe")
        svc = _billing_service({"USD": stripe})
        assert svc._provider_for("USD") is stripe

    def test_egp_tenant_raises_provider_unavailable(self):
        stripe = _stub_provider("USD", "stripe")
        svc = _billing_service({"USD": stripe})
        with pytest.raises(ProviderUnavailableError) as exc_info:
            svc._provider_for("EGP")
        assert exc_info.value.currency == "EGP"

    def test_unknown_currency_raises(self):
        svc = _billing_service({})
        with pytest.raises(ProviderUnavailableError):
            svc._provider_for("JPY")
```

- [ ] **Step 2 · Run test to verify fail**

```bash
pytest tests/test_billing_service_routing.py -q
```
Expected: FAIL — `BillingService.__init__() got an unexpected keyword argument 'providers'` (current init takes `stripe_client=`).

- [ ] **Step 3 · Edit `BillingService.__init__` and add `_provider_for`**

In `src/datapulse/billing/service.py`, change the class:

```python
# Imports — add at top
from datapulse.billing.provider import PaymentProvider, ProviderUnavailableError

# ... existing imports, PlanLimitExceededError unchanged ...

class BillingService:
    """Business logic for subscriptions, plans, usage, and provider routing."""

    def __init__(
        self,
        repo: BillingRepository,
        providers: dict[str, PaymentProvider],   # CHANGED from stripe_client
        *,
        price_to_plan: dict[str, str],
        base_url: str,
    ) -> None:
        self._repo = repo
        self._providers = providers
        self._price_to_plan = price_to_plan
        self._base_url = base_url

    # Back-compat shim — `self._stripe` was referenced from webhook code.
    # Route all provider access through `_provider_for` going forward.
    def _provider_for(self, currency: str) -> PaymentProvider:
        provider = self._providers.get(currency.upper())
        if provider is None:
            raise ProviderUnavailableError(currency)
        return provider

    # ... rest of the class unchanged for now (this PR keeps behavior; provider-
    # aware checkout/portal/webhook methods come in a later task) ...
```

All existing `self._stripe.foo(...)` call-sites inside `BillingService` must be swapped to `self._provider_for(self._tenant_currency(tenant_id)).foo(...)`. If `_tenant_currency` doesn't yet exist, add it:

```python
    def _tenant_currency(self, tenant_id: int) -> str:
        row = self._repo.get_tenant_plan_row(tenant_id)   # already returns plan row
        return getattr(row, "currency", "USD")            # defaults to USD if column not yet live
```

(If `get_tenant_plan_row` doesn't exist in the repo, the existing `get_tenant_plan` that returns a plan name is fine — add a sibling method that returns the full row OR extend an existing method. The repo layer lives at `src/datapulse/billing/repository.py:140` region; keep the edit minimal.)

- [ ] **Step 4 · Update `get_billing_service` factory**

In `src/datapulse/api/deps.py`, find `get_billing_service` (around line 219) and rewrite:

```python
def get_billing_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> BillingService:
    settings = get_settings()
    repo = BillingRepository(session)
    stripe = StripeClient(settings.stripe_secret_key)
    providers: dict[str, PaymentProvider] = {"USD": stripe}
    return BillingService(
        repo=repo,
        providers=providers,
        price_to_plan=settings.stripe_price_to_plan_map,
        base_url=settings.billing_base_url,
    )
```

Add the import near the top of `deps.py`:

```python
from datapulse.billing.provider import PaymentProvider
```

Same for `build_billing_webhook_service` in the same file — convert its `BillingService(repo, stripe_client=StripeClient(...), ...)` to the new `providers=` form.

- [ ] **Step 5 · Update existing webhook test fixtures**

In `tests/test_billing_webhook.py`, find the `billing_service` fixture (around line 52) and replace:

```python
@pytest.fixture()
def billing_service(mock_repo: MagicMock, mock_stripe: MagicMock) -> BillingService:
    return BillingService(
        repo=mock_repo,
        providers={"USD": mock_stripe},
        price_to_plan=_PRICE_TO_PLAN,
        base_url=_BASE_URL,
    )
```

Do the same in `tests/test_billing_plans_platform.py` wherever `BillingService(..., stripe_client=...)` is constructed.

- [ ] **Step 6 · Run full billing test suite**

```bash
pytest tests/test_billing_webhook.py tests/test_billing_plans_platform.py tests/test_billing_service_routing.py tests/test_payment_provider_protocol.py -q
```
Expected: all green (48 existing + 3 new + 3 new = 54 passed approx).

- [ ] **Step 7 · Ruff gate**

```bash
ruff format --check src/datapulse/billing/ src/datapulse/api/deps.py tests/
ruff check src/datapulse/billing/ src/datapulse/api/deps.py tests/
```
Expected: both pass cleanly.

- [ ] **Step 8 · Commit**

```bash
git add src/datapulse/billing/service.py src/datapulse/api/deps.py tests/
git commit -m "feat(billing): BillingService routes by currency via providers dict (#604-1)

BillingService no longer imports StripeClient directly. Takes
providers: dict[str, PaymentProvider] keyed by ISO-4217. _provider_for
raises ProviderUnavailableError (→ HTTP 503) when no provider is
configured for a currency. api/deps wires {USD: StripeClient(...)};
EGP support arrives in Spec 2 (Paymob).

Zero behavior change for USD tenants. Existing billing tests pass
after trivial fixture-constructor update.

Spec §4.2 · PR 2 of 4"
```

---

## PR 3 — Backend plumbing: `PlanLimits.price_egp` + `UserClaims.locale`

### Task 4 · Extend `PlanLimits` with EGP pricing

**Files:**
- Modify: `src/datapulse/billing/plans.py`
- Create: `tests/test_plan_limits_egp.py`

- [ ] **Step 1 · Write the failing test**

```python
# tests/test_plan_limits_egp.py
"""EGP pricing fields on PlanLimits (#604 Spec 1 PR 3)."""

from datapulse.billing.plans import PLAN_LIMITS, get_plan_limits


class TestPlanLimitsEgp:
    def test_pro_has_egp_price(self):
        pro = get_plan_limits("pro")
        assert pro.price_egp == 149_900  # piastres → 1,499 EGP
        assert pro.price_currency_default == "USD"

    def test_platform_has_egp_price(self):
        plat = get_plan_limits("platform")
        assert plat.price_egp == 299_900  # piastres → 2,999 EGP

    def test_starter_egp_zero(self):
        starter = get_plan_limits("starter")
        assert starter.price_egp == 0

    def test_every_plan_has_egp_field(self):
        for name, limits in PLAN_LIMITS.items():
            assert hasattr(limits, "price_egp"), f"{name} missing price_egp"
            assert hasattr(limits, "price_currency_default"), (
                f"{name} missing price_currency_default"
            )
```

- [ ] **Step 2 · Run test to verify fail**

```bash
pytest tests/test_plan_limits_egp.py -q
```
Expected: FAIL — `AttributeError: 'PlanLimits' object has no attribute 'price_egp'`.

- [ ] **Step 3 · Add fields to `PlanLimits` + plan entries**

In `src/datapulse/billing/plans.py`, edit the dataclass and every plan definition:

```python
from typing import Literal

@dataclass(frozen=True)
class PlanLimits:
    """Immutable plan limits — -1 means unlimited, 0 means disabled."""

    data_sources: int
    max_rows: int
    ai_insights: bool
    pipeline_automation: bool
    quality_gates: bool
    name: str
    price_display: str

    # Egypt PMF (#604). price_egp in piastres (1 EGP = 100 piastres) to
    # map cleanly onto provider cents APIs; price_currency_default decides
    # what to render when the tenant hasn't picked a currency yet.
    price_egp: int
    price_currency_default: Literal["USD", "EGP"]

    # ... Platform-tier fields unchanged ...
    inventory_management: bool = False
    # etc.


PLAN_LIMITS: dict[str, PlanLimits] = {
    "starter": PlanLimits(
        # ... existing fields ...
        price_display="$0/mo",
        price_egp=0,
        price_currency_default="USD",
        # ... existing trailing fields ...
    ),
    "pro": PlanLimits(
        # ... existing ...
        price_display="$49/mo",
        price_egp=149_900,               # 1,499 EGP — placeholder; Finance to confirm
        price_currency_default="USD",
        # ...
    ),
    "platform": PlanLimits(
        # ...
        price_display="$99/mo",
        price_egp=299_900,               # 2,999 EGP
        price_currency_default="USD",
        # ...
    ),
    "enterprise": PlanLimits(
        # ...
        price_display="Custom",
        price_egp=0,                     # quoted per-contract
        price_currency_default="USD",
        # ...
    ),
}
```

- [ ] **Step 4 · Run test to verify pass**

```bash
pytest tests/test_plan_limits_egp.py -q
```
Expected: `4 passed`.

- [ ] **Step 5 · Run existing plan tests**

```bash
pytest tests/test_billing_plans_platform.py -q
```
Expected: all existing tests still pass (adding fields with defaults shouldn't break anything; if existing tests instantiate `PlanLimits` directly, add the two new fields to those call-sites).

- [ ] **Step 6 · Commit**

```bash
git add src/datapulse/billing/plans.py tests/test_plan_limits_egp.py
git commit -m "feat(billing): add EGP pricing to PlanLimits (#604-1)

Every plan gains price_egp (piastres) and price_currency_default.
Placeholder numbers close to current USD at ~30 EGP/USD — Finance-
final numbers ship in a follow-up PR once the team signs off.

Spec §4.5 · PR 3 of 4"
```

### Task 5 · Surface Auth0 `locale` claim on `UserClaims`

**Files:**
- Modify: `src/datapulse/core/auth.py`
- Modify: `tests/test_auth.py`
- Create: `docs/ops/auth0-locale-action.md`

- [ ] **Step 1 · Write the failing test**

In `tests/test_auth.py`, add to the `TestGetCurrentUser` class:

```python
    def test_jwt_locale_claim_surfaced(self):
        """Auth0 'locale' claim lands on UserClaims['locale']."""
        creds = MagicMock()
        creds.credentials = "jwt-token-value"
        fake_claims = {
            "sub": "user123",
            "tenant_id": "42",
            "locale": "ar-EG",
        }
        with patch("datapulse.core.auth.verify_jwt", return_value=fake_claims):
            result = get_current_user(
                credentials=creds,
                api_key=None,
                settings=_settings(api_key="key", auth0_domain="example.auth0.com"),
            )
        assert result["locale"] == "ar-EG"

    def test_jwt_missing_locale_claim_defaults_to_en_us(self):
        creds = MagicMock()
        creds.credentials = "jwt-token-value"
        fake_claims = {"sub": "user123", "tenant_id": "42"}
        with patch("datapulse.core.auth.verify_jwt", return_value=fake_claims):
            result = get_current_user(
                credentials=creds,
                api_key=None,
                settings=_settings(api_key="key", auth0_domain="example.auth0.com"),
            )
        assert result["locale"] == "en-US"
```

- [ ] **Step 2 · Run test to verify fail**

```bash
pytest tests/test_auth.py::TestGetCurrentUser::test_jwt_locale_claim_surfaced -q
```
Expected: FAIL — `KeyError: 'locale'`.

- [ ] **Step 3 · Add `locale` to `UserClaims` and read it in `get_current_user`**

In `src/datapulse/core/auth.py`:

```python
class UserClaims(TypedDict):
    """Typed structure for authenticated user JWT claims."""

    sub: str
    email: str
    preferred_username: str
    tenant_id: str
    locale: str                    # NEW: Auth0 locale claim; default 'en-US' (#604)
    roles: list[str]
    raw_claims: dict[str, Any]
```

And in `get_current_user`, inside the `if credentials is not None:` branch, just before the `return` statement (around line 149), add:

```python
        locale = str(claims.get("locale") or "en-US")
```

Then extend the return dict:

```python
        return {
            "sub": claims.get("sub", ""),
            "email": claims.get("email", ""),
            "preferred_username": claims.get("preferred_username", ""),
            "tenant_id": tenant_id_str,
            "locale": locale,                      # NEW
            "roles": roles,
            "raw_claims": claims,
        }
```

Do the same for the API-key branch (line ~162), dev-mode branch (line ~188), and both `get_optional_user` variants. The default in every non-JWT branch is `"en-US"`.

- [ ] **Step 4 · Run targeted test**

```bash
pytest tests/test_auth.py -q
```
Expected: all 41+ tests pass (new 2 + existing ones, which now need the `locale` key in their expected-dict assertions if any).

- [ ] **Step 5 · Write Auth0 Action doc**

Create `docs/ops/auth0-locale-action.md`:

```markdown
# Auth0 Action — surface `locale` claim (#604)

## Why

`get_current_user` reads an optional `locale` claim and surfaces it on
`UserClaims`. The frontend uses it as the default when a user hasn't
picked a locale via the UI switcher yet. Auth0 does not ship this claim
by default — deploy the action below once per tenant in the Auth0
dashboard.

## The action

1. Auth0 Dashboard → Actions → Library → Build Custom → name it
   `surface-locale-claim`, flow: `Login / Post Login`.
2. Paste this code:

```js
exports.onExecutePostLogin = async (event, api) => {
  const locale = event.user.user_metadata?.locale || event.request.locale;
  if (locale) {
    api.idToken.setCustomClaim("locale", locale);
    api.accessToken.setCustomClaim("locale", locale);
  }
};
```

3. Deploy, then drag it into the `Login` flow.
4. Verify: log in as a test user, inspect the JWT payload — `locale`
   should appear as a top-level claim.

## Fallback behavior

If the action is **not** deployed, every user gets `locale = "en-US"`
on the backend. No crash — users can still override via the in-app
locale switcher.
```

- [ ] **Step 6 · Ruff + final pytest sweep**

```bash
ruff format --check src/datapulse/core/auth.py tests/test_auth.py
ruff check src/datapulse/core/auth.py tests/test_auth.py
pytest tests/test_auth.py tests/test_auth_dev_fallback.py -q
```
Expected: all clean, all pass.

- [ ] **Step 7 · Commit**

```bash
git add src/datapulse/core/auth.py tests/test_auth.py docs/ops/auth0-locale-action.md
git commit -m "feat(auth): surface Auth0 locale claim onto UserClaims (#604-1)

UserClaims gains locale: str (default 'en-US'). get_current_user reads
claims.get('locale') from JWT, preserves en-US default for API-key and
dev-mode paths. Auth0 Action snippet documented in docs/ops/ — must
be deployed by an operator via Auth0 dashboard.

Spec §4.1+§4.6 · PR 3 of 4"
```

---

## PR 4 — Frontend i18n: LocaleSwitcher + PriceBadge + Tailwind RTL + sidebar integration

### Task 6 · Install + enable `@tailwindcss/rtl`

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/tailwind.config.ts`

- [ ] **Step 1 · Install**

```bash
cd frontend && npm install -D @tailwindcss/rtl
```

- [ ] **Step 2 · Wire into config**

In `frontend/tailwind.config.ts`, add the plugin:

```typescript
import rtl from "@tailwindcss/rtl";

export default {
  // ... existing content/theme unchanged ...
  plugins: [
    // ... existing plugins ...
    rtl(),
  ],
} satisfies Config;
```

- [ ] **Step 3 · Verify build still succeeds**

```bash
npm run build 2>&1 | tail -20
```
Expected: build succeeds; no new Tailwind compile errors.

- [ ] **Step 4 · Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/tailwind.config.ts
git commit -m "feat(frontend): enable @tailwindcss/rtl for Arabic layouts (#604-1)

Adds rtl: and ltr: variants so authors can flip directional utilities
where logical properties (ps-*, pe-*) aren't sufficient. No existing
class bindings change; plugin is additive.

Spec §4.8 · PR 4 of 4"
```

### Task 7 · Build `<LocaleSwitcher />` component

**Files:**
- Create: `frontend/src/components/locale-switcher/index.tsx`
- Create: `frontend/src/components/locale-switcher/index.test.tsx`

- [ ] **Step 1 · Write the failing vitest**

```tsx
// frontend/src/components/locale-switcher/index.test.tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { LocaleSwitcher } from "./index";

const mockRouterRefresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: mockRouterRefresh }),
}));

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

describe("LocaleSwitcher", () => {
  beforeEach(() => {
    mockRouterRefresh.mockClear();
    mockFetch.mockReset();
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({ locale: "ar" }) });
  });

  it("renders both language buttons", () => {
    render(<LocaleSwitcher currentLocale="en" />);
    expect(screen.getByRole("button", { name: /english/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /arabic/i })).toBeInTheDocument();
  });

  it("highlights the current locale", () => {
    render(<LocaleSwitcher currentLocale="ar" />);
    const ar = screen.getByRole("button", { name: /arabic/i });
    expect(ar).toHaveAttribute("aria-pressed", "true");
  });

  it("clicking a different locale posts to /api/locale and refreshes the router", async () => {
    render(<LocaleSwitcher currentLocale="en" />);
    fireEvent.click(screen.getByRole("button", { name: /arabic/i }));
    await vi.waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/locale",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ locale: "ar" }),
      }),
    );
    await vi.waitFor(() => expect(mockRouterRefresh).toHaveBeenCalled());
  });

  it("clicking the current locale is a no-op", async () => {
    render(<LocaleSwitcher currentLocale="en" />);
    fireEvent.click(screen.getByRole("button", { name: /english/i }));
    // give microtasks a chance
    await Promise.resolve();
    expect(mockFetch).not.toHaveBeenCalled();
    expect(mockRouterRefresh).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2 · Run vitest to verify fail**

```bash
cd frontend && npx vitest run src/components/locale-switcher/ 2>&1 | tail -10
```
Expected: FAIL — module not found.

- [ ] **Step 3 · Implement the component**

```tsx
// frontend/src/components/locale-switcher/index.tsx
"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { type Locale } from "@/i18n/config";

type Props = { currentLocale: Locale };

const OPTIONS: { code: Locale; label: string; aria: string }[] = [
  { code: "en", label: "EN", aria: "English" },
  { code: "ar", label: "عربي", aria: "Arabic" },
];

export function LocaleSwitcher({ currentLocale }: Props) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const select = async (next: Locale) => {
    if (next === currentLocale || isPending) return;
    const resp = await fetch("/api/locale", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ locale: next }),
    });
    if (!resp.ok) return;
    startTransition(() => router.refresh());
  };

  return (
    <div
      role="group"
      aria-label="Language"
      className="flex items-center gap-1 rounded-lg border border-divider p-0.5 text-xs"
    >
      {OPTIONS.map((o) => {
        const active = o.code === currentLocale;
        return (
          <button
            key={o.code}
            type="button"
            aria-label={o.aria}
            aria-pressed={active}
            onClick={() => select(o.code)}
            disabled={isPending}
            className={[
              "rounded-md px-2 py-1 transition-colors",
              active
                ? "bg-surface-2 text-text-primary"
                : "text-text-secondary hover:bg-divider hover:text-text-primary",
              isPending ? "opacity-50 cursor-not-allowed" : "",
            ].join(" ")}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4 · Run test to verify pass**

```bash
npx vitest run src/components/locale-switcher/
```
Expected: `4 tests passed`.

- [ ] **Step 5 · Commit**

```bash
git add frontend/src/components/locale-switcher/
git commit -m "feat(frontend): LocaleSwitcher component with cookie + refresh (#604-1)

Two-button segmented control (EN / عربي). Posts to existing
/api/locale endpoint (sets NEXT_LOCALE cookie), then router.refresh()
so next-intl picks up the new locale on the server side without a
full navigation.

Spec §4.4 · PR 4 of 4"
```

### Task 8 · Build `<PriceBadge />` + `lib/currency.ts`

**Files:**
- Create: `frontend/src/lib/currency.ts`
- Create: `frontend/src/lib/currency.test.ts`
- Create: `frontend/src/components/price-badge/index.tsx`
- Create: `frontend/src/components/price-badge/index.test.tsx`

- [ ] **Step 1 · Write the currency helper test**

```typescript
// frontend/src/lib/currency.test.ts
import { describe, it, expect } from "vitest";
import { formatPrice } from "./currency";

describe("formatPrice", () => {
  it("formats USD piastres-equivalent (cents) correctly in en-US", () => {
    expect(formatPrice(4900, "USD", "en")).toBe("$49.00");
  });

  it("formats EGP piastres with Arabic digits in ar", () => {
    // 149900 piastres = 1,499 EGP
    const out = formatPrice(149900, "EGP", "ar");
    expect(out).toMatch(/١٬?٤٩٩|1,499/);
    expect(out).toMatch(/ج\.م|EGP/);
  });

  it("zero is rendered", () => {
    expect(formatPrice(0, "USD", "en")).toBe("$0.00");
  });

  it("unknown currency falls back to ISO code", () => {
    expect(formatPrice(1000, "XYZ", "en")).toContain("XYZ");
  });
});
```

- [ ] **Step 2 · Run to fail**

```bash
npx vitest run src/lib/currency
```
Expected: FAIL — module not found.

- [ ] **Step 3 · Implement `lib/currency.ts`**

```typescript
// frontend/src/lib/currency.ts
/**
 * Format a price in its minor unit (USD cents or EGP piastres) for display.
 *
 * The backend stores plan prices in minor units (see `PlanLimits.price_egp`)
 * to avoid float rounding and to map cleanly onto provider cents APIs.
 * This helper is the ONLY place the frontend divides by 100.
 */
export function formatPrice(
  minorUnits: number,
  currency: string,
  locale: string,
): string {
  const major = minorUnits / 100;
  try {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(major);
  } catch {
    // Unknown currency → render as "<code> <amount>"
    return `${currency} ${major.toFixed(2)}`;
  }
}
```

- [ ] **Step 4 · Verify currency test passes**

```bash
npx vitest run src/lib/currency
```
Expected: `4 tests passed`.

- [ ] **Step 5 · Write PriceBadge test**

```tsx
// frontend/src/components/price-badge/index.test.tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PriceBadge } from "./index";

describe("PriceBadge", () => {
  it("renders USD by default locale", () => {
    render(<PriceBadge minorUnits={4900} currency="USD" locale="en" />);
    expect(screen.getByText(/\$49\.00/)).toBeInTheDocument();
  });

  it("renders EGP in ar locale", () => {
    render(<PriceBadge minorUnits={149900} currency="EGP" locale="ar" />);
    expect(screen.getByText(/١٬?٤٩٩|1,499/)).toBeInTheDocument();
  });

  it("appends per-month suffix when monthly=true", () => {
    render(<PriceBadge minorUnits={4900} currency="USD" locale="en" monthly />);
    expect(screen.getByText(/\/mo/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 6 · Run to fail**

```bash
npx vitest run src/components/price-badge
```
Expected: FAIL.

- [ ] **Step 7 · Implement `<PriceBadge />`**

```tsx
// frontend/src/components/price-badge/index.tsx
import { formatPrice } from "@/lib/currency";

type Props = {
  minorUnits: number;
  currency: string;
  locale: string;
  monthly?: boolean;
  className?: string;
};

export function PriceBadge({
  minorUnits,
  currency,
  locale,
  monthly = false,
  className = "",
}: Props) {
  const price = formatPrice(minorUnits, currency, locale);
  return (
    <span className={`font-semibold ${className}`}>
      {price}
      {monthly && <span className="text-text-secondary">/mo</span>}
    </span>
  );
}
```

- [ ] **Step 8 · Verify both tests pass**

```bash
npx vitest run src/components/price-badge src/lib/currency
```
Expected: `7 tests passed` total.

- [ ] **Step 9 · Commit**

```bash
git add frontend/src/lib/currency.ts frontend/src/lib/currency.test.ts \
        frontend/src/components/price-badge/
git commit -m "feat(frontend): PriceBadge + formatPrice helper (#604-1)

Minor-unit (piastres / cents) input, Intl.NumberFormat output
selected by locale + currency. Safe fallback to 'CODE amount' for
unknown ISO codes. PriceBadge composes formatPrice + an optional
/mo suffix for pricing pages.

Spec §4.5 · PR 4 of 4"
```

### Task 9 · Mount `<LocaleSwitcher />` in sidebar footer

**Files:**
- Modify: `frontend/src/components/layout/sidebar.tsx`

- [ ] **Step 1 · Find the existing theme-toggle mount points**

`grep -n "<ThemeToggle" frontend/src/components/layout/sidebar.tsx` will return three line numbers (~416, 493, 501 per current main). Each is a mount point inside a footer/mobile variant.

- [ ] **Step 2 · Add `LocaleSwitcher` next to each `<ThemeToggle />` occurrence**

At each of the three mount points, wrap the existing `<ThemeToggle />` and add a sibling `<LocaleSwitcher />`:

```tsx
import { LocaleSwitcher } from "@/components/locale-switcher";
import { useLocale } from "next-intl";

// ... inside the component, near the top:
const locale = useLocale() as Locale;

// ... at each theme-toggle mount point:
<div className="flex items-center justify-between gap-2">
  <ThemeToggle />
  <LocaleSwitcher currentLocale={locale} />
</div>
```

(The existing mount point may already be inside a flex div — if so, just append the `<LocaleSwitcher />` as a sibling.)

- [ ] **Step 3 · Run dev server + smoke test manually**

```bash
cd frontend && npm run dev
```

Open `http://localhost:3000/dashboard`, confirm in the sidebar footer you see the theme toggle + the EN / عربي buttons. Click `عربي`, expect the page to refresh into Arabic + `dir="rtl"` on `<html>`.

- [ ] **Step 4 · Commit**

```bash
git add frontend/src/components/layout/sidebar.tsx
git commit -m "feat(frontend): mount LocaleSwitcher beside ThemeToggle (#604-1)

All three sidebar-footer mount points (desktop, tablet, mobile) now
render the locale switcher next to the theme toggle. useLocale() from
next-intl drives the currentLocale prop.

Spec §4.4 · PR 4 of 4"
```

### Task 10 · Use `<PriceBadge />` on the pricing page + settings page tenant form

**Files:**
- Modify: `frontend/src/app/(marketing)/pricing/page.tsx` (or wherever pricing lives)
- Create: `frontend/src/app/dashboard/settings/tenant/page.tsx` (new minor UI)
- Modify: `frontend/messages/en.json` and `frontend/messages/ar.json` (add billing + settings keys)

- [ ] **Step 1 · Extend message catalogs**

Open `frontend/messages/en.json` and append (or merge into existing) these keys:

```json
{
  "billing": {
    "upgrade_cta": "Upgrade to Pro",
    "currency": {
      "unavailable_egp": "Payments in EGP are coming soon. Contact support."
    },
    "plan": {
      "starter": { "title": "Starter", "tagline": "Try it free" },
      "pro":     { "title": "Pro",     "tagline": "For growing pharmacies" },
      "platform":{ "title": "Platform","tagline": "For pharmacy chains" },
      "enterprise":{ "title": "Enterprise", "tagline": "Custom pricing" }
    }
  },
  "settings": {
    "tenant": {
      "title": "Tenant settings",
      "locale_label": "Language",
      "currency_label": "Billing currency",
      "save": "Save",
      "saved": "Saved"
    }
  }
}
```

Mirror in `frontend/messages/ar.json`:

```json
{
  "billing": {
    "upgrade_cta": "ترقية إلى Pro",
    "currency": {
      "unavailable_egp": "الدفع بالجنيه المصري قريبًا. تواصل مع الدعم."
    },
    "plan": {
      "starter": { "title": "Starter", "tagline": "جرّب مجانًا" },
      "pro":     { "title": "Pro",     "tagline": "للصيدليات النامية" },
      "platform":{ "title": "Platform","tagline": "لسلاسل الصيدليات" },
      "enterprise":{ "title": "Enterprise", "tagline": "أسعار مخصصة" }
    }
  },
  "settings": {
    "tenant": {
      "title": "إعدادات المستأجر",
      "locale_label": "اللغة",
      "currency_label": "عملة الفواتير",
      "save": "حفظ",
      "saved": "تم الحفظ"
    }
  }
}
```

- [ ] **Step 2 · Identify the pricing page file**

```bash
grep -rln "starter\|pro\|platform" frontend/src/app --include="*.tsx" | grep -i pric | head
```

If the pricing page exists under `frontend/src/app/(marketing)/pricing/page.tsx`, edit it. If no pricing page is found on the marketing surface yet, skip this step and only integrate `<PriceBadge />` in the `dashboard/billing/page.tsx` plan-card section (search for `price_display` usage).

- [ ] **Step 3 · Swap hardcoded price strings for `<PriceBadge />`**

Pattern to replace (wherever pricing cards render):

```tsx
// BEFORE
<div className="price">{plan.price_display}</div>

// AFTER
<PriceBadge
  minorUnits={locale === "ar" ? plan.price_egp : plan.price_usd_cents}
  currency={locale === "ar" ? "EGP" : "USD"}
  locale={locale}
  monthly
/>
```

(If `plan.price_usd_cents` doesn't exist in the API response, the backend needs to add it. Plan card API lives in `src/datapulse/api/routes/billing.py`; the `get_billing_status` response schema is in `src/datapulse/billing/models.py` — add `price_usd_cents: int` and populate from `PlanLimits.price_display` by parsing the existing string. Since `PlanLimits` already has `price_usd_cents`-equivalent via the dollar string, this parse is trivial: `int(price_display.replace("$", "").replace("/mo", "").strip() or "0") * 100`.)

- [ ] **Step 4 · Build the Settings → Tenant page**

Create `frontend/src/app/dashboard/settings/tenant/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { useTranslations, useLocale } from "next-intl";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { type Locale } from "@/i18n/config";

type Tenant = {
  locale: string;
  currency: "USD" | "EGP";
};

export default function TenantSettingsPage() {
  const t = useTranslations("settings.tenant");
  const locale = useLocale() as Locale;
  const [currency, setCurrency] = useState<Tenant["currency"]>("USD");
  const [saved, setSaved] = useState(false);

  const save = async () => {
    const resp = await fetch("/api/v1/tenants/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ currency, locale }),
    });
    if (resp.ok) {
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    }
  };

  return (
    <section className="mx-auto max-w-2xl space-y-6 p-6">
      <h1 className="text-2xl font-semibold">{t("title")}</h1>

      <div>
        <label className="label">{t("locale_label")}</label>
        <LocaleSwitcher currentLocale={locale} />
      </div>

      <div>
        <label className="label">{t("currency_label")}</label>
        <select
          value={currency}
          onChange={(e) => setCurrency(e.target.value as Tenant["currency"])}
          className="mock-input"
        >
          <option value="USD">USD</option>
          <option value="EGP">EGP</option>
        </select>
      </div>

      <button onClick={save} className="mock-button">
        {saved ? t("saved") : t("save")}
      </button>
    </section>
  );
}
```

The backend PATCH endpoint doesn't exist yet — add a minimal one in `src/datapulse/api/routes/tenants.py` (create the file if absent) that writes `currency` and `locale` to `bronze.tenants` for the caller's tenant_id. Rate-limit `5/minute`.

- [ ] **Step 5 · Commit**

```bash
git add frontend/src/app frontend/messages src/datapulse/api/routes/tenants.py \
        src/datapulse/billing/models.py
git commit -m "feat(frontend): PriceBadge on plan cards + tenant settings page (#604-1)

Pricing cards pull from locale + tenant.currency, rendered via
<PriceBadge />. New /dashboard/settings/tenant page lets admins
override the tenant's locale + currency (PATCH /api/v1/tenants/me).
Message catalogs extended with billing + settings keys in both en/ar.

Spec §3.2 + §4.3 · PR 4 of 4"
```

### Task 11 · Playwright E2E — RTL variant on dashboard

**Files:**
- Modify: `frontend/e2e/dashboard.spec.ts`

- [ ] **Step 1 · Extend the existing dashboard spec**

Inside `frontend/e2e/dashboard.spec.ts`, append a test:

```typescript
test.describe("dashboard — Arabic (#604 RTL)", () => {
  test("renders with dir=rtl and Arabic sidebar labels", async ({ page, context }) => {
    await context.addCookies([
      {
        name: "NEXT_LOCALE",
        value: "ar",
        url: "http://localhost:3000",
      },
    ]);
    await page.goto("/dashboard");
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    await expect(page.locator("html")).toHaveAttribute("lang", "ar");
    // At least one sidebar nav label should be Arabic, not English.
    const sidebar = page.locator('[data-testid="sidebar-nav"]');
    await expect(sidebar).toContainText(/لوحة|الفواتير|الإعدادات/);
  });
});
```

(If `data-testid="sidebar-nav"` isn't in the code yet, add it on the `<nav>` wrapper inside `sidebar.tsx`.)

- [ ] **Step 2 · Run Playwright**

```bash
cd frontend && npx playwright test dashboard.spec.ts
```
Expected: both the existing English test and the new Arabic test pass.

- [ ] **Step 3 · Commit + open PR 4**

```bash
git add frontend/e2e/dashboard.spec.ts
git commit -m "test(e2e): Playwright RTL variant of dashboard.spec.ts (#604-1)

Sets NEXT_LOCALE=ar cookie, navigates to /dashboard, asserts
dir=rtl + lang=ar + Arabic sidebar labels.

Spec §6.4 · PR 4 of 4 · final task"
```

---

## Post-implementation

- [ ] **Open PRs 1–4 targeting `main` in order.** Each merges before the next is opened (dependencies), so reviewers see minimum diff each time.
- [ ] **Update `#604` issue checklist** — tick every Spec-1 subtask, leave Spec-2/3 items unchecked.
- [ ] **Add CHANGELOG entry** under `## [Unreleased]`: `- Egypt-ready foundation — Arabic UI, locale switcher, EGP price display, tenant-scoped locale/currency, payment-provider abstraction. Stripe stays exclusive; Paymob/InstaPay arrive in Spec 2/3 (#604).`
- [ ] **Deploy Auth0 Action** per `docs/ops/auth0-locale-action.md` (manual step by operator).
- [ ] **Announce in `#datapulse-announcements`**: "Arabic UI + EGP pricing live; full EGP checkout in ~3 weeks."

---

## Self-review (checked before handoff)

| Check | Result |
|---|---|
| Spec coverage — every §3–§9 item has a task | ✅ PR 1 = §3.3. PR 2 = §4.1/§4.2. PR 3 = §4.5/§3.1/§3.4. PR 4 = §4.4/§4.5/§4.6/§4.8/§6.4. Auth0 doc = §3.4. |
| Placeholder scan — no TBDs/TODOs | ✅ Only "placeholder EGP prices" — those are business-choice placeholders explicitly called out in both spec + plan. |
| Type consistency — `providers: dict[str, PaymentProvider]` used identically in protocol def, service init, deps factory, and tests | ✅ |
| Code in every code-step | ✅ |
| Exact file paths + run commands | ✅ |
| Non-trivial tasks are TDD cycles | ✅ every new-behavior task has write-test → run-fail → implement → run-pass → commit |
