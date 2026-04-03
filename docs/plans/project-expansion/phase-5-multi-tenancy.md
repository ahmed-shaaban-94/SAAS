# Phase 5 — Multi-tenancy & Billing

> **Status**: PLANNED
> **Priority**: CRITICAL
> **Dependencies**: None (foundation for all other expansion phases)
> **Goal**: Transform DataPulse from a single-tenant system into a true multi-tenant SaaS with self-service onboarding, subscription billing, and usage metering.

---

## Why This Phase First

DataPulse already has tenant-scoped RLS on `bronze.sales` and all marts tables, plus a `bronze.tenants` table with 1 row. But there's no:
- Self-service tenant creation
- Billing or subscription management
- Usage tracking or limits enforcement
- Tenant admin panel for managing users

**Without this, DataPulse cannot onboard paying customers.**

---

## Visual Overview

```
Phase 5 — Multi-tenancy & Billing
═══════════════════════════════════════════════════════════════

  5.1 Tenant Service        Tenant CRUD, invitation system
       │
       v
  5.2 Subscription Billing  Stripe integration, plans, webhooks
       │
       v
  5.3 Usage Metering        Track rows, API calls, storage per tenant
       │
       v
  5.4 Tenant Admin Panel    Settings, user management, billing portal
       │
       v
  5.5 Limits & Enforcement  Quota enforcement, graceful degradation
       │
       v
  5.6 Testing & Security    Pen-test tenant isolation, billing edge cases

═══════════════════════════════════════════════════════════════
```

---

## Sub-Phases

### 5.1 Tenant Service

**Goal**: Full tenant lifecycle management.

**Backend**:
- `src/datapulse/tenants/` module:
  - `models.py` — Pydantic models: `TenantCreate`, `TenantResponse`, `TenantUpdate`, `TenantInvite`
  - `repository.py` — SQLAlchemy CRUD for `bronze.tenants` (expand table schema)
  - `service.py` — Business logic: create tenant, invite users, deactivate
- Expand `bronze.tenants` table:
  ```sql
  ALTER TABLE bronze.tenants ADD COLUMN
    slug VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(200),
    owner_user_id UUID NOT NULL,
    plan VARCHAR(20) DEFAULT 'free',
    status VARCHAR(20) DEFAULT 'active',  -- active, suspended, cancelled
    settings JSONB DEFAULT '{}',
    max_rows BIGINT DEFAULT 1000,
    max_users INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now();
  ```
- API routes: `POST /api/v1/tenants`, `GET /api/v1/tenants/me`, `PATCH /api/v1/tenants/me`
- Keycloak: auto-create realm group per tenant, map `tenant_id` to JWT claims

**Frontend**:
- Onboarding wizard: company name, slug, industry → auto-provision tenant
- Tenant settings page under `/settings/organization`

**Tests**: ~25 unit + integration tests

---

### 5.2 Subscription Billing (Stripe)

**Goal**: Monetize with subscription tiers.

**Pricing Tiers**:

| Plan | Price/mo | Rows | Users | Sources | Dashboards |
|------|----------|------|-------|---------|-----------|
| Free | $0 | 1K | 1 | CSV/Excel | 1 |
| Starter | $29 | 100K | 5 | + Sheets | 5 |
| Pro | $99 | 1M | 25 | + DB | Unlimited |
| Enterprise | Custom | Unlimited | Unlimited | All | Unlimited |

**Backend**:
- `src/datapulse/billing/` module:
  - `models.py` — `SubscriptionCreate`, `SubscriptionResponse`, `BillingEvent`
  - `stripe_client.py` — Stripe SDK wrapper (customers, subscriptions, checkout sessions)
  - `webhook_handler.py` — Handle Stripe webhooks (subscription created/updated/cancelled, payment succeeded/failed)
  - `service.py` — Sync Stripe state with tenant plan
- API routes:
  - `POST /api/v1/billing/checkout` — Create Stripe checkout session
  - `GET /api/v1/billing/portal` — Redirect to Stripe customer portal
  - `POST /api/v1/billing/webhook` — Stripe webhook receiver
  - `GET /api/v1/billing/subscription` — Current plan details
- Migration: `008_add_billing_columns.sql` — `stripe_customer_id`, `stripe_subscription_id`, `plan_expires_at`

**Frontend**:
- Billing page: current plan, usage, upgrade CTA
- Checkout flow via Stripe embedded checkout
- Plan comparison modal

**Tests**: ~20 tests (mock Stripe SDK)

---

### 5.3 Usage Metering

**Goal**: Track and expose resource usage per tenant.

**What to Track**:

| Metric | How | Storage |
|--------|-----|---------|
| Row count | COUNT on bronze.sales WHERE tenant_id = ? | Cached in Redis, refresh hourly |
| API calls | Middleware counter per request | Redis INCR, flush to DB daily |
| Storage (bytes) | SUM of Parquet file sizes | Calculated on ingest |
| Active users | Distinct JWT sub per day | Redis HyperLogLog |

**Backend**:
- `src/datapulse/metering/` module:
  - `models.py` — `UsageSnapshot`, `UsageHistory`
  - `collector.py` — Redis-backed counters, periodic DB flush
  - `middleware.py` — FastAPI middleware to increment API call counter
- API routes:
  - `GET /api/v1/usage` — Current usage vs limits
  - `GET /api/v1/usage/history` — Usage over time

**Frontend**:
- Usage dashboard in settings: bar charts showing rows used / limit, API calls, etc.
- Warning banners when approaching limits (80%, 90%, 100%)

**Tests**: ~15 tests

---

### 5.4 Tenant Admin Panel

**Goal**: Let tenant admins manage their organization.

**Frontend Pages**:
- `/settings/organization` — Name, slug, logo
- `/settings/members` — Invite, remove, change roles (admin/editor/viewer)
- `/settings/billing` — Plan, invoices, payment method (Stripe portal)
- `/settings/usage` — Usage meters and history

**Backend**:
- `src/datapulse/tenants/members.py` — Member management (CRUD, role assignment)
- Keycloak integration: sync member roles to Keycloak groups
- API routes:
  - `GET /api/v1/tenants/me/members` — List members
  - `POST /api/v1/tenants/me/members/invite` — Send invitation email
  - `PATCH /api/v1/tenants/me/members/{id}/role` — Update role
  - `DELETE /api/v1/tenants/me/members/{id}` — Remove member

**Tests**: ~20 tests

---

### 5.5 Limits & Enforcement

**Goal**: Enforce plan limits gracefully.

**Enforcement Points**:

| Limit | Where | Behavior |
|-------|-------|----------|
| Max rows | Bronze loader | Reject import with clear error |
| Max users | Invite endpoint | 403 with upgrade CTA |
| Max API calls/min | Rate limiter | 429 with retry-after header |
| Max dashboards | Dashboard create | 403 with upgrade CTA |
| Max sources | Source connect | 403 with upgrade CTA |

**Implementation**:
- `src/datapulse/tenants/limits.py` — `check_limit(tenant_id, resource) -> bool`
- Dependency injection: `deps.py` → `get_tenant_limits()` available in all routes
- Graceful degradation: read-only mode when payment fails (don't delete data)

**Tests**: ~20 tests (boundary conditions, grace periods)

---

### 5.6 Testing & Security Audit

**Goal**: Ensure tenant isolation is bulletproof.

**Testing Plan**:
- Cross-tenant data access tests (Tenant A must NEVER see Tenant B's data)
- RLS bypass attempts (direct SQL, API parameter manipulation)
- Billing edge cases (downgrade mid-cycle, payment failure, reactivation)
- Concurrent tenant operations (race conditions)
- Keycloak token manipulation tests

**Deliverables**:
- Security test suite: ~20 dedicated isolation tests
- Pen-test checklist document
- Incident response runbook for tenant data leaks

---

## Database Changes

```sql
-- 008_expand_tenants.sql
ALTER TABLE bronze.tenants ADD COLUMN slug VARCHAR(50) UNIQUE;
ALTER TABLE bronze.tenants ADD COLUMN display_name VARCHAR(200);
ALTER TABLE bronze.tenants ADD COLUMN owner_user_id UUID;
ALTER TABLE bronze.tenants ADD COLUMN plan VARCHAR(20) DEFAULT 'free';
ALTER TABLE bronze.tenants ADD COLUMN status VARCHAR(20) DEFAULT 'active';
ALTER TABLE bronze.tenants ADD COLUMN settings JSONB DEFAULT '{}';
ALTER TABLE bronze.tenants ADD COLUMN max_rows BIGINT DEFAULT 1000;
ALTER TABLE bronze.tenants ADD COLUMN max_users INT DEFAULT 1;
ALTER TABLE bronze.tenants ADD COLUMN stripe_customer_id VARCHAR(100);
ALTER TABLE bronze.tenants ADD COLUMN stripe_subscription_id VARCHAR(100);
ALTER TABLE bronze.tenants ADD COLUMN plan_expires_at TIMESTAMPTZ;
ALTER TABLE bronze.tenants ADD COLUMN created_at TIMESTAMPTZ DEFAULT now();
ALTER TABLE bronze.tenants ADD COLUMN updated_at TIMESTAMPTZ DEFAULT now();

-- 009_create_usage_log.sql
CREATE TABLE public.usage_log (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES bronze.tenants(tenant_id),
    metric VARCHAR(50) NOT NULL,  -- 'api_calls', 'rows', 'storage_bytes'
    value BIGINT NOT NULL,
    recorded_at DATE NOT NULL DEFAULT CURRENT_DATE,
    UNIQUE (tenant_id, metric, recorded_at)
);
ALTER TABLE public.usage_log ENABLE ROW LEVEL SECURITY;

-- 010_create_tenant_members.sql
CREATE TABLE public.tenant_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES bronze.tenants(tenant_id),
    user_id UUID NOT NULL,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'viewer',  -- admin, editor, viewer
    invited_at TIMESTAMPTZ DEFAULT now(),
    accepted_at TIMESTAMPTZ,
    UNIQUE (tenant_id, user_id)
);
ALTER TABLE public.tenant_members ENABLE ROW LEVEL SECURITY;
```

---

## New Python Modules

```
src/datapulse/
├── tenants/
│   ├── __init__.py
│   ├── models.py          # Pydantic: TenantCreate/Response/Update, MemberInvite
│   ├── repository.py      # SQLAlchemy CRUD for tenants + members
│   ├── service.py         # Tenant lifecycle (create, suspend, cancel)
│   ├── members.py         # Member management (invite, role, remove)
│   └── limits.py          # Quota checking + enforcement
├── billing/
│   ├── __init__.py
│   ├── models.py          # SubscriptionCreate/Response, BillingEvent
│   ├── stripe_client.py   # Stripe SDK wrapper
│   ├── webhook_handler.py # Stripe webhook processing
│   └── service.py         # Billing orchestration
├── metering/
│   ├── __init__.py
│   ├── models.py          # UsageSnapshot, UsageHistory
│   ├── collector.py       # Redis counters + DB flush
│   └── middleware.py       # API call counting middleware
└── api/routes/
    ├── tenants.py         # Tenant + member endpoints
    ├── billing.py         # Billing + checkout endpoints
    └── usage.py           # Usage metering endpoints
```

---

## Frontend Pages

```
frontend/src/app/(app)/settings/
├── page.tsx               # Settings overview / redirect
├── organization/
│   └── page.tsx           # Tenant name, slug, logo
├── members/
│   └── page.tsx           # User list, invite, roles
├── billing/
│   └── page.tsx           # Plan, usage, upgrade, invoices
└── usage/
    └── page.tsx           # Usage meters + history charts
```

---

## Acceptance Criteria

- [ ] New tenant can sign up and see empty dashboard in < 2 minutes
- [ ] Stripe checkout creates subscription and upgrades plan
- [ ] Downgrade/cancel preserves data but restricts access
- [ ] Usage meters update in near-real-time (< 1 hour lag)
- [ ] Tenant A cannot access Tenant B's data via any API endpoint
- [ ] Rate limits enforced per tenant, not globally
- [ ] 120+ new tests, all passing
- [ ] Zero regression on existing 95%+ coverage
