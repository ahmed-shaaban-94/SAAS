# Phase 4: Trust & Commercial Readiness — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Productionize lead capture (enriched Postgres-backed modal form), complete the marketing site's missing Use Cases section, add a SourceHealthBadge to the dashboard, and build a `/demo` page — all commercial readiness signals for the pilot phase.

**Architecture:** Backend adds a `leads` table + service + public FastAPI route following the route→service→repo pattern but without tenant/auth scoping. Frontend marketing gains a `LeadCaptureModal` (Radix Dialog) wrapping an enriched form that forwards to the FastAPI backend; a `UseCasesSection` fills the `#use-cases` nav anchor. Dashboard gets a `SourceHealthBadge` that reads `usePipelineRuns` and replaces the static `LastUpdated` clock with a real freshness signal. A static `/demo` page gives the CTA button a destination.

**Tech Stack:** FastAPI, SQLAlchemy (plain session), PostgreSQL migration, Next.js App Router, Radix UI `@radix-ui/react-dialog`, SWR, Vitest + Testing Library, Tailwind CSS

---

## File Map

### Create
| File | Responsibility |
|------|---------------|
| `migrations/087_create_leads.sql` | `public.leads` table — email, name, company, use_case, team_size, tier |
| `src/datapulse/leads/__init__.py` | Package init |
| `src/datapulse/leads/models.py` | `LeadRequest` + `LeadResponse` Pydantic models |
| `src/datapulse/leads/repository.py` | `email_exists()` + `insert()` SQL |
| `src/datapulse/leads/service.py` | `capture()` — dedup check + insert |
| `src/datapulse/api/routes/leads.py` | `POST /api/v1/leads` — public, rate-limited 5/min |
| `tests/test_leads.py` | Unit + integration tests for leads service & route |
| `frontend/src/components/marketing/lead-capture-modal.tsx` | Radix Dialog + enriched form (name, company, email, use_case, tier) |
| `frontend/src/components/marketing/use-cases-section.tsx` | `#use-cases` marketing section |
| `frontend/src/components/dashboard/source-health-badge.tsx` | Last pipeline run freshness badge |
| `frontend/src/app/(marketing)/demo/page.tsx` | `/demo` static showcase page |
| `frontend/src/__tests__/components/marketing/lead-capture-modal.test.tsx` | Modal behaviour tests |
| `frontend/src/__tests__/components/dashboard/source-health-badge.test.tsx` | Badge state tests |

### Modify
| File | Change |
|------|--------|
| `src/datapulse/api/app.py` | Import + register `leads` router at `/api/v1` |
| `frontend/src/app/api/waitlist/route.ts` | Forward enriched payload to `DATAPULSE_API_URL/api/v1/leads` |
| `frontend/src/components/marketing/cta-section.tsx` | Replace anchor with `<LeadCaptureModal trigger="Request Pilot Access" />` |
| `frontend/src/components/marketing/pricing-card.tsx` | CTA buttons for Explorer/Operations tiers open `<LeadCaptureModal tier={name} />` |
| `frontend/src/app/(marketing)/page.tsx` | Add `<UseCasesSection />` before `<PricingSection />` |
| `frontend/src/app/(app)/dashboard/page.tsx` | Replace `<LastUpdated />` with `<SourceHealthBadge />` |

---

## Task 1: Backend — leads table + service + route

**Files:**
- Create: `migrations/087_create_leads.sql`
- Create: `src/datapulse/leads/__init__.py`
- Create: `src/datapulse/leads/models.py`
- Create: `src/datapulse/leads/repository.py`
- Create: `src/datapulse/leads/service.py`
- Create: `src/datapulse/api/routes/leads.py`
- Modify: `src/datapulse/api/app.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_leads.py`:

```python
"""Tests for the leads capture service and POST /api/v1/leads route."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from datapulse.leads.models import LeadRequest, LeadResponse
from datapulse.leads.service import LeadService


def make_repo(email_exists: bool = False) -> MagicMock:
    repo = MagicMock()
    repo.email_exists.return_value = email_exists
    return repo


def test_capture_new_lead_inserts():
    repo = make_repo(email_exists=False)
    svc = LeadService(repo)
    result = svc.capture(LeadRequest(email="new@example.com", name="Ali", company="Pharma Co"))
    assert result.success is True
    repo.insert.assert_called_once()


def test_capture_duplicate_does_not_insert():
    repo = make_repo(email_exists=True)
    svc = LeadService(repo)
    result = svc.capture(LeadRequest(email="dup@example.com"))
    assert result.success is True
    repo.insert.assert_not_called()


def test_lead_request_requires_valid_email():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        LeadRequest(email="not-an-email")


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from datapulse.api.app import create_app
    return TestClient(create_app())


def test_post_leads_success(client, monkeypatch):
    """POST /api/v1/leads returns 200 for a valid payload."""
    from datapulse.leads import service as svc_module
    mock_svc = MagicMock()
    mock_svc.capture.return_value = LeadResponse(success=True, message="You're on the list!")
    monkeypatch.setattr(svc_module, "LeadService", lambda repo: mock_svc)
    resp = client.post("/api/v1/leads", json={"email": "test@company.com", "name": "Test"})
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_post_leads_invalid_email(client):
    resp = client.post("/api/v1/leads", json={"email": "bad-email"})
    assert resp.status_code == 422
```

- [ ] **Step 2: Run tests — expect failures**

```bash
docker compose exec api python -m pytest tests/test_leads.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'datapulse.leads'`

- [ ] **Step 3: Write the migration**

Create `migrations/087_create_leads.sql`:

```sql
-- Migration: 087 – Lead capture table
-- Layer: application (public schema, no RLS — admin-owned, no tenant scoping)
-- Idempotent: safe to run multiple times

CREATE TABLE IF NOT EXISTS public.leads (
    id          SERIAL PRIMARY KEY,
    email       TEXT NOT NULL,
    name        TEXT,
    company     TEXT,
    use_case    TEXT,
    team_size   TEXT,
    tier        TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_email
    ON public.leads(email);

CREATE INDEX IF NOT EXISTS idx_leads_created_at
    ON public.leads(created_at DESC);

COMMENT ON TABLE public.leads IS 'Pilot access / waitlist lead capture — one row per email';
```

- [ ] **Step 4: Apply migration**

```bash
docker compose exec postgres psql -U datapulse -d datapulse -f /migrations/087_create_leads.sql
```

Expected: `CREATE TABLE`, `CREATE INDEX`, `COMMENT`

- [ ] **Step 5: Write `src/datapulse/leads/__init__.py`**

```python
"""Lead capture module."""
```

- [ ] **Step 6: Write `src/datapulse/leads/models.py`**

```python
"""Pydantic models for lead capture."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr


class LeadRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    email: EmailStr
    name: str | None = None
    company: str | None = None
    use_case: str | None = None
    team_size: str | None = None
    tier: str | None = None


class LeadResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool
    message: str
```

- [ ] **Step 7: Write `src/datapulse/leads/repository.py`**

```python
"""Lead capture repository — raw SQL, no business logic."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


class LeadRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def email_exists(self, email: str) -> bool:
        row = self._session.execute(
            text("SELECT 1 FROM public.leads WHERE email = :email LIMIT 1"),
            {"email": email},
        ).fetchone()
        return row is not None

    def insert(
        self,
        email: str,
        name: str | None,
        company: str | None,
        use_case: str | None,
        team_size: str | None,
        tier: str | None,
    ) -> None:
        self._session.execute(
            text("""
                INSERT INTO public.leads (email, name, company, use_case, team_size, tier)
                VALUES (:email, :name, :company, :use_case, :team_size, :tier)
                ON CONFLICT (email) DO NOTHING
            """),
            {
                "email": email,
                "name": name,
                "company": company,
                "use_case": use_case,
                "team_size": team_size,
                "tier": tier,
            },
        )
        self._session.commit()
```

- [ ] **Step 8: Write `src/datapulse/leads/service.py`**

```python
"""Lead capture service — orchestrates dedup check and insert."""

from __future__ import annotations

from .models import LeadRequest, LeadResponse
from .repository import LeadRepository


class LeadService:
    def __init__(self, repo: LeadRepository) -> None:
        self._repo = repo

    def capture(self, data: LeadRequest) -> LeadResponse:
        if self._repo.email_exists(data.email):
            return LeadResponse(success=True, message="You're already on the list!")
        self._repo.insert(
            email=data.email,
            name=data.name,
            company=data.company,
            use_case=data.use_case,
            team_size=data.team_size,
            tier=data.tier,
        )
        return LeadResponse(success=True, message="You're on the list! We'll be in touch soon.")
```

- [ ] **Step 9: Write `src/datapulse/api/routes/leads.py`**

```python
"""Lead capture API route — public, no auth required."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from datapulse.api.deps import get_db_session
from datapulse.api.limiter import limiter
from datapulse.leads.models import LeadRequest, LeadResponse
from datapulse.leads.repository import LeadRepository
from datapulse.leads.service import LeadService

router = APIRouter(prefix="/leads", tags=["leads"])


def get_lead_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> LeadService:
    return LeadService(LeadRepository(session))


LeadServiceDep = Annotated[LeadService, Depends(get_lead_service)]


@router.post("", response_model=LeadResponse)
@limiter.limit("5/minute")
async def capture_lead(
    request: Request,
    data: LeadRequest,
    service: LeadServiceDep,
) -> LeadResponse:
    """Record a pilot access / waitlist request. Public endpoint — no auth."""
    return service.capture(data)
```

- [ ] **Step 10: Register leads router in `src/datapulse/api/app.py`**

Add `leads` to the existing import block (alphabetically between `health` and `insights_first`):

```python
# In the import block, add:
from datapulse.api.routes import (
    ...
    leads,
    ...
)
```

Then in `create_app()` where routers are included, add:
```python
app.include_router(leads.router, prefix="/api/v1")
```

Find the existing `app.include_router` block and add this line alongside the others.

- [ ] **Step 11: Run tests — expect green**

```bash
docker compose exec api python -m pytest tests/test_leads.py -v
```

Expected: 5 passed

- [ ] **Step 12: Smoke-test the endpoint**

```bash
curl -X POST http://localhost:8000/api/v1/leads \
  -H "Content-Type: application/json" \
  -d '{"email":"pilot@example.com","name":"Ahmed","company":"Pharma Co","tier":"Operations Pilot"}'
```

Expected: `{"success":true,"message":"You're on the list! We'll be in touch soon."}`

- [ ] **Step 13: Commit**

```bash
git add migrations/087_create_leads.sql src/datapulse/leads/ src/datapulse/api/routes/leads.py src/datapulse/api/app.py tests/test_leads.py
git commit -m "feat(leads): add lead capture table, service, and public POST /api/v1/leads"
```

---

## Task 2: Next.js API upgrade + LeadCaptureModal

**Files:**
- Modify: `frontend/src/app/api/waitlist/route.ts`
- Create: `frontend/src/components/marketing/lead-capture-modal.tsx`
- Test: `frontend/src/__tests__/components/marketing/lead-capture-modal.test.tsx`

- [ ] **Step 1: Write failing tests**

Create `frontend/src/__tests__/components/marketing/lead-capture-modal.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LeadCaptureModal } from "@/components/marketing/lead-capture-modal";

global.fetch = vi.fn();

describe("LeadCaptureModal", () => {
  beforeEach(() => {
    vi.mocked(fetch).mockReset();
  });

  it("renders the trigger button", () => {
    render(<LeadCaptureModal trigger="Request Pilot Access" />);
    expect(screen.getByRole("button", { name: /request pilot access/i })).toBeInTheDocument();
  });

  it("opens the dialog on trigger click", async () => {
    render(<LeadCaptureModal trigger="Request Pilot Access" />);
    await userEvent.click(screen.getByRole("button", { name: /request pilot access/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/company/i)).toBeInTheDocument();
  });

  it("submits the form and shows success state", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    } as Response);

    render(<LeadCaptureModal trigger="Request Pilot Access" />);
    await userEvent.click(screen.getByRole("button", { name: /request pilot access/i }));
    await userEvent.type(screen.getByLabelText(/email/i), "pilot@example.com");
    await userEvent.type(screen.getByLabelText(/name/i), "Ahmed");
    await userEvent.type(screen.getByLabelText(/company/i), "DataPharma");
    await userEvent.click(screen.getByRole("button", { name: /submit|apply|request/i }));

    await waitFor(() =>
      expect(screen.getByText(/you're on the list/i)).toBeInTheDocument()
    );
  });

  it("shows error message on API failure", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      json: async () => ({ message: "Server error" }),
    } as Response);

    render(<LeadCaptureModal trigger="Request Pilot Access" />);
    await userEvent.click(screen.getByRole("button", { name: /request pilot access/i }));
    await userEvent.type(screen.getByLabelText(/email/i), "bad@example.com");
    await userEvent.click(screen.getByRole("button", { name: /submit|apply|request/i }));

    await waitFor(() =>
      expect(screen.getByText(/server error|something went wrong/i)).toBeInTheDocument()
    );
  });
});
```

- [ ] **Step 2: Run tests — expect failures**

```bash
docker compose exec frontend npx vitest run src/__tests__/components/marketing/lead-capture-modal.test.tsx 2>&1 | tail -20
```

Expected: `Cannot find module '@/components/marketing/lead-capture-modal'`

- [ ] **Step 3: Create `frontend/src/components/marketing/lead-capture-modal.tsx`**

```tsx
"use client";

import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

type FormState = "idle" | "loading" | "success" | "error";

const USE_CASES = [
  "Sales & Revenue Reporting",
  "Inventory & Expiry Monitoring",
  "Branch Performance Tracking",
  "Operations Reporting",
  "Other",
] as const;

const TEAM_SIZES = ["1–5", "6–20", "21–100", "100+"] as const;

interface Props {
  trigger: string;
  tier?: string;
  triggerClassName?: string;
}

export function LeadCaptureModal({ trigger, tier, triggerClassName }: Props) {
  const [open, setOpen] = useState(false);
  const [formState, setFormState] = useState<FormState>("idle");
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = Object.fromEntries(new FormData(form).entries());

    setFormState("loading");
    try {
      const res = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...data, tier: tier ?? data.tier }),
      });
      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        throw new Error(json.message || "Something went wrong. Please try again.");
      }
      setFormState("success");
    } catch (err) {
      setFormState("error");
      setErrorMessage(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <button
          type="button"
          className={triggerClassName ?? "rounded-full bg-accent px-8 py-3.5 text-sm font-semibold text-page shadow-[0_0_24px_rgba(0,199,242,0.35)] transition-all hover:shadow-[0_0_32px_rgba(0,199,242,0.5)] hover:scale-[1.02]"}
        >
          {trigger}
        </button>
      </Dialog.Trigger>

      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-[1.75rem] border border-border bg-card p-8 shadow-2xl focus:outline-none"
          aria-describedby="lead-modal-desc"
        >
          <Dialog.Close className="absolute right-4 top-4 rounded-full p-1.5 text-text-secondary hover:bg-background/60 hover:text-text-primary">
            <X className="h-4 w-4" />
            <span className="sr-only">Close</span>
          </Dialog.Close>

          {formState === "success" ? (
            <div className="flex flex-col items-center gap-3 py-6 text-center">
              <CheckCircle2 className="h-10 w-10 text-accent" />
              <Dialog.Title className="text-lg font-semibold">You&apos;re on the list!</Dialog.Title>
              <p className="text-sm text-text-secondary">We&apos;ll be in touch soon to set up your pilot.</p>
              <button
                type="button"
                onClick={() => { setOpen(false); setFormState("idle"); }}
                className="mt-2 rounded-full bg-accent px-6 py-2 text-sm font-semibold text-page"
              >
                Done
              </button>
            </div>
          ) : (
            <>
              <Dialog.Title className="text-lg font-semibold">
                {tier ? `Apply for ${tier}` : "Request Pilot Access"}
              </Dialog.Title>
              <p id="lead-modal-desc" className="mt-1 text-sm text-text-secondary">
                Tell us a bit about your team and we&apos;ll be in touch to get started.
              </p>

              <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                <div>
                  <label htmlFor="lm-email" className="mb-1 block text-xs font-medium text-text-primary">
                    Work Email *
                  </label>
                  <input
                    id="lm-email"
                    name="email"
                    type="email"
                    required
                    placeholder="you@company.com"
                    className="w-full rounded-lg border border-border bg-background/60 px-3 py-2 text-sm placeholder:text-text-secondary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                    aria-label="Email address"
                  />
                </div>

                <div>
                  <label htmlFor="lm-name" className="mb-1 block text-xs font-medium text-text-primary">
                    Your Name
                  </label>
                  <input
                    id="lm-name"
                    name="name"
                    type="text"
                    placeholder="Ahmed Hassan"
                    className="w-full rounded-lg border border-border bg-background/60 px-3 py-2 text-sm placeholder:text-text-secondary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                    aria-label="Name"
                  />
                </div>

                <div>
                  <label htmlFor="lm-company" className="mb-1 block text-xs font-medium text-text-primary">
                    Company
                  </label>
                  <input
                    id="lm-company"
                    name="company"
                    type="text"
                    placeholder="Pharma Group"
                    className="w-full rounded-lg border border-border bg-background/60 px-3 py-2 text-sm placeholder:text-text-secondary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                    aria-label="Company"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="lm-use-case" className="mb-1 block text-xs font-medium text-text-primary">
                      Primary Use Case
                    </label>
                    <select
                      id="lm-use-case"
                      name="use_case"
                      className="w-full rounded-lg border border-border bg-background/60 px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                    >
                      <option value="">Select…</option>
                      {USE_CASES.map((uc) => (
                        <option key={uc} value={uc}>{uc}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="lm-team-size" className="mb-1 block text-xs font-medium text-text-primary">
                      Team Size
                    </label>
                    <select
                      id="lm-team-size"
                      name="team_size"
                      className="w-full rounded-lg border border-border bg-background/60 px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                    >
                      <option value="">Select…</option>
                      {TEAM_SIZES.map((ts) => (
                        <option key={ts} value={ts}>{ts}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {formState === "error" && (
                  <div className="flex items-center gap-1.5 text-growth-red" aria-live="polite">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    <span className="text-xs">{errorMessage}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={formState === "loading"}
                  className="mt-2 w-full rounded-lg bg-accent py-3 text-sm font-semibold text-page transition-colors hover:bg-accent/90 disabled:opacity-60"
                >
                  {formState === "loading" ? (
                    <Loader2 className="mx-auto h-4 w-4 animate-spin" />
                  ) : (
                    "Submit Request"
                  )}
                </button>
              </form>
            </>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
```

- [ ] **Step 4: Update `frontend/src/app/api/waitlist/route.ts` to forward to FastAPI**

Replace the entire file with:

```typescript
import { NextResponse } from "next/server";

const DATAPULSE_API = process.env.DATAPULSE_API_URL ?? "http://api:8000";

// In-process rate limiter retained as a first-pass guard.
const rateLimitMap = new Map<string, { count: number; resetAt: number }>();
const RATE_LIMIT = 5;
const RATE_WINDOW = 60 * 60 * 1000;

function isRateLimited(ip: string): boolean {
  const now = Date.now();
  const entry = rateLimitMap.get(ip);
  if (!entry || now > entry.resetAt) {
    rateLimitMap.set(ip, { count: 1, resetAt: now + RATE_WINDOW });
    return false;
  }
  entry.count++;
  return entry.count > RATE_LIMIT;
}

export async function POST(request: Request) {
  try {
    const forwarded = request.headers.get("x-forwarded-for");
    const ip = forwarded?.split(",").map((s) => s.trim()).filter(Boolean).at(-1) ?? "unknown";

    if (isRateLimited(ip)) {
      return NextResponse.json(
        { success: false, message: "Too many requests. Please try again later." },
        { status: 429 },
      );
    }

    const body = await request.json();
    const email = body?.email?.trim()?.toLowerCase();

    if (!email || !/^[a-zA-Z0-9._\-+]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/.test(email)) {
      return NextResponse.json(
        { success: false, message: "Please provide a valid email address." },
        { status: 400 },
      );
    }

    const upstream = await fetch(`${DATAPULSE_API}/api/v1/leads`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        name: body?.name ?? null,
        company: body?.company ?? null,
        use_case: body?.use_case ?? null,
        team_size: body?.team_size ?? null,
        tier: body?.tier ?? null,
      }),
    });

    const data = await upstream.json().catch(() => ({}));

    if (!upstream.ok) {
      return NextResponse.json(
        { success: false, message: data.message ?? "Something went wrong." },
        { status: upstream.status },
      );
    }

    return NextResponse.json({ success: true, message: data.message });
  } catch {
    return NextResponse.json(
      { success: false, message: "Something went wrong. Please try again." },
      { status: 500 },
    );
  }
}
```

- [ ] **Step 5: Run tests — expect green**

```bash
docker compose exec frontend npx vitest run src/__tests__/components/marketing/lead-capture-modal.test.tsx
```

Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/marketing/lead-capture-modal.tsx frontend/src/app/api/waitlist/route.ts frontend/src/__tests__/components/marketing/lead-capture-modal.test.tsx
git commit -m "feat(marketing): add LeadCaptureModal with enriched form + forward lead to FastAPI backend"
```

---

## Task 3: Wire LeadCaptureModal into marketing site + UseCasesSection

**Files:**
- Modify: `frontend/src/components/marketing/cta-section.tsx`
- Modify: `frontend/src/components/marketing/pricing-card.tsx`
- Create: `frontend/src/components/marketing/use-cases-section.tsx`
- Modify: `frontend/src/app/(marketing)/page.tsx`

- [ ] **Step 1: Update `cta-section.tsx` to use modal**

Replace the "Request Pilot Access" anchor with the modal:

```tsx
"use client";

import { SectionWrapper } from "./section-wrapper";
import { LeadCaptureModal } from "./lead-capture-modal";
import { useIntersectionObserver } from "@/hooks/use-intersection-observer";

export function CTASection() {
  const { ref, isVisible } = useIntersectionObserver();

  return (
    <SectionWrapper>
      <div ref={ref} className={`reveal-up ${isVisible ? "is-visible" : ""}`}>
        <div className="viz-panel relative overflow-hidden rounded-[2rem] p-8 text-center sm:p-12">
          <div className="pointer-events-none absolute inset-0">
            <div className="absolute left-1/2 top-1/2 h-[300px] w-[300px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent/10 blur-[80px]" />
          </div>

          <div className="relative">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.26em] text-accent/80">
              Start with clarity
            </p>
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl md:text-5xl">
              See what your team should act on every day.
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-lg leading-8 text-text-secondary">
              If your sales and operations data lives across spreadsheets, manual reports,
              and disconnected workflows, DataPulse can help you turn it into one clearer
              operating view.
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <LeadCaptureModal trigger="Request Pilot Access" />
              <a
                href="/demo"
                className="rounded-full border border-white/15 bg-white/5 px-8 py-3.5 text-sm font-semibold text-text-primary transition-colors hover:bg-white/10"
              >
                See Product Demo
              </a>
            </div>
            <p className="mt-4 text-sm text-text-secondary/70">
              Best for teams that want to prove value in a focused rollout before
              expanding company-wide.
            </p>
          </div>
        </div>
      </div>
    </SectionWrapper>
  );
}
```

- [ ] **Step 2: Update `pricing-card.tsx` so CTA buttons open modal**

`PricingCard` is a server component — convert to client component and wire `LeadCaptureModal`:

```tsx
"use client";

import { Check } from "lucide-react";
import { LeadCaptureModal } from "./lead-capture-modal";
import type { PricingTier } from "@/lib/marketing-constants";

export function PricingCard({
  name,
  price,
  originalPrice,
  period,
  description,
  badge,
  features,
  cta,
  isPopular,
}: PricingTier) {
  const isPilotTier = name === "Explorer Pilot" || name === "Operations Pilot";
  const enterpriseHref = "mailto:support@smartdatapulse.tech?subject=Enterprise%20Rollout";

  const ctaButton = isPilotTier ? (
    <LeadCaptureModal
      trigger={cta}
      tier={name}
      triggerClassName={`mt-8 block w-full rounded-lg py-3 text-center text-sm font-semibold transition-colors ${
        isPopular
          ? "cta-shimmer bg-accent text-page shadow-lg shadow-accent/20 hover:bg-accent/90"
          : "viz-panel-soft text-text-primary hover:bg-white/10"
      }`}
    />
  ) : (
    <a
      href={enterpriseHref}
      className={`mt-8 block rounded-lg py-3 text-center text-sm font-semibold transition-colors viz-panel-soft text-text-primary hover:bg-white/10`}
    >
      {cta}
    </a>
  );

  const cardContent = (
    <>
      {isPopular && (
        <span className="absolute -top-3 left-1/2 z-10 -translate-x-1/2 rounded-full bg-accent px-4 py-1 text-xs font-semibold text-page">
          Popular
        </span>
      )}
      <h3 className="text-lg font-semibold">{name}</h3>
      <p className="mt-1 text-sm text-text-secondary">{description}</p>
      <div className="mt-6">
        {originalPrice && (
          <span className="mr-2 text-xl text-text-secondary line-through">{originalPrice}</span>
        )}
        <span className="text-4xl font-bold">{price}</span>
        {period && <span className="text-text-secondary">{period}</span>}
      </div>
      {badge && (
        <div className="mt-3 inline-flex items-center gap-1.5 rounded-xl bg-growth-green/10 px-3 py-1.5 text-xs font-semibold text-growth-green">
          <span>🎉</span> {badge}
        </div>
      )}
      <ul className="mt-8 flex-1 space-y-3">
        {features.map((feature) => (
          <li key={feature} className="flex items-start gap-3">
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
            <span className="text-sm text-text-secondary">{feature}</span>
          </li>
        ))}
      </ul>
      {ctaButton}
    </>
  );

  if (isPopular) {
    return (
      <div className="rotating-border">
        <div className="relative flex flex-col rounded-[1.75rem] p-8 bg-accent/5">
          {cardContent}
        </div>
      </div>
    );
  }

  return (
    <div className="viz-panel viz-card-hover relative flex flex-col rounded-[1.75rem] p-8 hover-lift">
      {cardContent}
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/src/components/marketing/use-cases-section.tsx`**

```tsx
import { SectionWrapper } from "./section-wrapper";
import { BarChart3, Package, GitBranch, FileBarChart } from "lucide-react";

const USE_CASES = [
  {
    icon: BarChart3,
    title: "Sales & Revenue Reporting",
    description:
      "Turn weekly spreadsheet exports into a live executive overview. Track revenue, product movement, and trend shifts across branches without manual compilation.",
    tag: "Commercial Teams",
  },
  {
    icon: Package,
    title: "Inventory & Expiry Monitoring",
    description:
      "Surface stockout risk and expiry exposure before they affect service levels. Know which products need attention now, not after the problem surfaces.",
    tag: "Operations Teams",
  },
  {
    icon: GitBranch,
    title: "Branch Performance Tracking",
    description:
      "Compare performance across locations. Identify which branches are lagging, which are trending, and where to focus field attention next.",
    tag: "Regional Management",
  },
  {
    icon: FileBarChart,
    title: "Operational Reporting",
    description:
      "Replace manual reporting cycles with scheduled outputs that go to the right people automatically. From daily briefings to monthly reviews.",
    tag: "Reporting Teams",
  },
] as const;

export function UseCasesSection() {
  return (
    <SectionWrapper id="use-cases">
      <div className="mb-12 text-center">
        <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.26em] text-accent/80">
          Use cases
        </p>
        <h2 className="text-3xl font-bold tracking-tight sm:text-4xl md:text-5xl">
          Built for teams that need clarity, not more reports
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-lg leading-8 text-text-secondary">
          DataPulse is used across commercial, operations, and regional management workflows
          in pharma and retail distribution.
        </p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        {USE_CASES.map(({ icon: Icon, title, description, tag }) => (
          <div
            key={title}
            className="viz-panel viz-card-hover rounded-[1.5rem] p-6 hover-lift"
          >
            <div className="mb-4 flex items-center gap-3">
              <div className="viz-panel-soft flex h-10 w-10 shrink-0 items-center justify-center rounded-xl">
                <Icon className="h-5 w-5 text-accent" />
              </div>
              <span className="rounded-full bg-accent/10 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-accent">
                {tag}
              </span>
            </div>
            <h3 className="text-base font-semibold text-text-primary">{title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-text-secondary">{description}</p>
          </div>
        ))}
      </div>
    </SectionWrapper>
  );
}
```

- [ ] **Step 4: Add `UseCasesSection` to `frontend/src/app/(marketing)/page.tsx`**

```tsx
import { UseCasesSection } from "@/components/marketing/use-cases-section";
```

Replace the PHASE 4 comment:
```tsx
{/* PHASE 4: Add <UseCasesSection /> here before PricingSection */}
<UseCasesSection />
```

- [ ] **Step 5: Type-check to verify no TypeScript errors**

```bash
docker compose exec frontend npx tsc --noEmit 2>&1 | tail -20
```

Expected: no errors

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/marketing/cta-section.tsx frontend/src/components/marketing/pricing-card.tsx frontend/src/components/marketing/use-cases-section.tsx frontend/src/app/(marketing)/page.tsx
git commit -m "feat(marketing): wire LeadCaptureModal into CTASection + PricingCard, add UseCasesSection"
```

---

## Task 4: SourceHealthBadge on dashboard

**Files:**
- Create: `frontend/src/components/dashboard/source-health-badge.tsx`
- Modify: `frontend/src/app/(app)/dashboard/page.tsx`
- Test: `frontend/src/__tests__/components/dashboard/source-health-badge.test.tsx`

- [ ] **Step 1: Write failing tests**

Create `frontend/src/__tests__/components/dashboard/source-health-badge.test.tsx`:

```tsx
import { describe, it, expect, vi, type Mock } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/hooks/use-pipeline-runs", () => ({
  usePipelineRuns: vi.fn(),
}));

import { usePipelineRuns } from "@/hooks/use-pipeline-runs";
import { SourceHealthBadge } from "@/components/dashboard/source-health-badge";

const mockHook = usePipelineRuns as unknown as Mock;

describe("SourceHealthBadge", () => {
  it("shows a shimmer placeholder while loading", () => {
    mockHook.mockReturnValue({ runs: [], isLoading: true, error: null });
    const { container } = render(<SourceHealthBadge />);
    expect(container.querySelector(".animate-pulse")).toBeInTheDocument();
  });

  it("shows 'No data yet' when no runs exist", () => {
    mockHook.mockReturnValue({ runs: [], isLoading: false, error: null });
    render(<SourceHealthBadge />);
    expect(screen.getByText(/no data yet/i)).toBeInTheDocument();
  });

  it("shows a green badge when last run succeeded", () => {
    mockHook.mockReturnValue({
      runs: [
        {
          id: "1",
          status: "success",
          finished_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(), // 30 min ago
        },
      ],
      isLoading: false,
      error: null,
    });
    render(<SourceHealthBadge />);
    expect(screen.getByTitle(/data is current/i)).toBeInTheDocument();
  });

  it("shows a red badge when last run failed", () => {
    mockHook.mockReturnValue({
      runs: [
        {
          id: "2",
          status: "failed",
          finished_at: new Date().toISOString(),
        },
      ],
      isLoading: false,
      error: null,
    });
    render(<SourceHealthBadge />);
    expect(screen.getByTitle(/last run failed/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests — expect failures**

```bash
docker compose exec frontend npx vitest run src/__tests__/components/dashboard/source-health-badge.test.tsx 2>&1 | tail -10
```

Expected: `Cannot find module '@/components/dashboard/source-health-badge'`

- [ ] **Step 3: Create `frontend/src/components/dashboard/source-health-badge.tsx`**

```tsx
"use client";

import { CheckCircle2, XCircle, Clock, AlertCircle } from "lucide-react";
import { usePipelineRuns } from "@/hooks/use-pipeline-runs";
import { cn } from "@/lib/utils";

function relativeTime(iso: string): string {
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function SourceHealthBadge() {
  const { runs, isLoading } = usePipelineRuns(1);

  if (isLoading) {
    return (
      <div className="flex items-center gap-1.5">
        <div className="h-3 w-3 animate-pulse rounded-full bg-divider" />
        <span className="inline-block h-3 w-20 animate-pulse rounded bg-divider" />
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-text-secondary">
        <AlertCircle className="h-3.5 w-3.5" />
        <span>No data yet</span>
      </div>
    );
  }

  const last = runs[0];
  const isSuccess = last.status === "success";
  const finishedAt = last.finished_at ?? last.started_at;

  return (
    <div
      title={isSuccess ? "Data is current" : "Last run failed"}
      className={cn(
        "flex items-center gap-1.5 text-xs font-medium",
        isSuccess ? "text-growth-green" : "text-growth-red",
      )}
    >
      {isSuccess ? (
        <CheckCircle2 className="h-3.5 w-3.5" />
      ) : (
        <XCircle className="h-3.5 w-3.5" />
      )}
      <span>{isSuccess ? "Current" : "Failed"}</span>
      {finishedAt && (
        <span className="text-text-secondary font-normal">
          <Clock className="mr-0.5 inline h-3 w-3" />
          {relativeTime(finishedAt)}
        </span>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Replace `LastUpdated` with `SourceHealthBadge` in dashboard page**

In `frontend/src/app/(app)/dashboard/page.tsx`:

Replace:
```tsx
import { LastUpdated } from "@/components/dashboard/last-updated";
```
With:
```tsx
import { SourceHealthBadge } from "@/components/dashboard/source-health-badge";
```

Replace:
```tsx
<LastUpdated />
```
With:
```tsx
<SourceHealthBadge />
```

- [ ] **Step 5: Run tests — expect green**

```bash
docker compose exec frontend npx vitest run src/__tests__/components/dashboard/source-health-badge.test.tsx
```

Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/dashboard/source-health-badge.tsx frontend/src/app/(app)/dashboard/page.tsx frontend/src/__tests__/components/dashboard/source-health-badge.test.tsx
git commit -m "feat(dashboard): add SourceHealthBadge replacing static LastUpdated clock"
```

---

## Task 5: Demo page

**Files:**
- Create: `frontend/src/app/(marketing)/demo/page.tsx`

- [ ] **Step 1: Create `frontend/src/app/(marketing)/demo/page.tsx`**

```tsx
import type { Metadata } from "next";
import Link from "next/link";
import { SectionWrapper } from "@/components/marketing/section-wrapper";
import { LeadCaptureModal } from "@/components/marketing/lead-capture-modal";
import {
  BarChart3,
  Package,
  TrendingUp,
  FileBarChart,
  Sparkles,
  ShieldCheck,
} from "lucide-react";

export const metadata: Metadata = {
  title: "Product Demo — DataPulse",
  description:
    "See how DataPulse turns pharma and retail sales data into daily decision-ready intelligence.",
};

const DEMO_FEATURES = [
  {
    icon: BarChart3,
    title: "Executive Revenue Dashboard",
    description:
      "Total revenue, day-over-day trends, top products and branches — all from one executive overview. Drillable by date range, branch, and product category.",
  },
  {
    icon: Package,
    title: "Inventory & Expiry Monitoring",
    description:
      "Stock level tracking, stockout risk alerts, and batch expiry timelines. Surface the items that need action before they become problems.",
  },
  {
    icon: TrendingUp,
    title: "Branch Performance Comparison",
    description:
      "Compare revenue, volume, and efficiency across all branches. Identify outliers and trend shifts at the regional and site level.",
  },
  {
    icon: Sparkles,
    title: "Explainable Insights & Anomalies",
    description:
      "DataPulse flags what changed and explains why — anomaly detection with context so teams know where to look next.",
  },
  {
    icon: FileBarChart,
    title: "Scheduled Reporting",
    description:
      "Daily briefings and monthly roll-ups delivered automatically. From executive summaries to operations team outputs.",
  },
  {
    icon: ShieldCheck,
    title: "Data Quality & Pipeline Health",
    description:
      "Every data import goes through automated cleaning, deduplication, and validation. Pipeline health is visible in the dashboard at all times.",
  },
] as const;

export default function DemoPage() {
  return (
    <>
      <SectionWrapper>
        <div className="mx-auto max-w-3xl text-center">
          <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.26em] text-accent/80">
            Product demo
          </p>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
            See DataPulse in action
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-text-secondary">
            DataPulse turns messy pharma and retail sales data into a daily
            decision-ready operating view — in hours, not weeks.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <LeadCaptureModal trigger="Request a Live Demo" />
            <Link
              href="/#pilot-access"
              className="rounded-full border border-white/15 bg-white/5 px-8 py-3.5 text-sm font-semibold text-text-primary transition-colors hover:bg-white/10"
            >
              View Pilot Options
            </Link>
          </div>
        </div>
      </SectionWrapper>

      <SectionWrapper>
        <div className="mb-10 text-center">
          <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">
            What you&apos;ll see in the dashboard
          </h2>
        </div>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {DEMO_FEATURES.map(({ icon: Icon, title, description }) => (
            <div
              key={title}
              className="viz-panel rounded-[1.5rem] p-6"
            >
              <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-accent/10">
                <Icon className="h-5 w-5 text-accent" />
              </div>
              <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-text-secondary">{description}</p>
            </div>
          ))}
        </div>
      </SectionWrapper>

      <SectionWrapper>
        <div className="viz-panel rounded-[2rem] p-8 text-center sm:p-12">
          <h2 className="text-2xl font-bold sm:text-3xl">
            Ready to see it with your own data?
          </h2>
          <p className="mx-auto mt-4 max-w-lg text-text-secondary">
            Most teams see their first useful dashboard within hours of uploading their
            first file. We can set up a pilot in a focused workflow to prove value quickly.
          </p>
          <div className="mt-8">
            <LeadCaptureModal trigger="Request Pilot Access" />
          </div>
        </div>
      </SectionWrapper>
    </>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
docker compose exec frontend npx tsc --noEmit 2>&1 | tail -10
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/(marketing)/demo/page.tsx
git commit -m "feat(marketing): add /demo page with feature showcase and LeadCaptureModal CTAs"
```

---

## Self-Review Checklist

### Spec Coverage
- [x] **Lead capture productionized** — Task 1 (backend) + Task 2 (modal + API upgrade) — enriched form (name, company, use case, team size) → Postgres `leads` table
- [x] **Demo page** — Task 5 — `/demo` route gives the CTA button a real destination
- [x] **UseCasesSection** — Task 3 — fills the missing `#use-cases` nav anchor
- [x] **Source health / data confidence** — Task 4 — `SourceHealthBadge` on dashboard shows real pipeline run status
- [x] **Marketing CTAs wired** — Task 3 — CTASection and PricingCard pilot tiers open modal

### Placeholder Scan
- No TBDs, no "add appropriate error handling", no missing code blocks found.

### Type Consistency
- `LeadRequest.email` is `EmailStr` in backend, validated by regex in Next.js API route — consistent.
- `LeadCaptureModal.tier` prop passed through `body.tier` in the API route — consistent with `LeadRequest.tier`.
- `usePipelineRuns(1)` returns `PipelineRun[]` — `SourceHealthBadge` reads `runs[0].status` and `runs[0].finished_at`, both typed in the existing hook interface.
- `PricingCard` converted to `"use client"` — required because it now renders `<LeadCaptureModal>` which has `useState`.
