# Architecture TODO — Pre-Production Hardening

These 4 items were identified during the full project security scan (March 2026).
All are required before production deployment.

---

## 1. API Authentication (API Key)

**Problem:** All API endpoints are publicly accessible — no auth required.

**Scope:** All routes in `src/datapulse/api/routes/` (analytics, pipeline, ai_light).
Health endpoint (`/health`) should remain public.

**Implementation:**
- Add `X-API-Key` header validation via FastAPI dependency
- Store valid API key(s) in `config.py` via `API_KEY` env var
- Create a shared dependency in `src/datapulse/api/deps.py`:
  ```python
  from fastapi import Header, HTTPException

  async def verify_api_key(x_api_key: str = Header(...)):
      if x_api_key != get_settings().api_key:
          raise HTTPException(status_code=401, detail="Invalid API key")
  ```
- Apply to all routers except health:
  ```python
  router = APIRouter(prefix="/analytics", dependencies=[Depends(verify_api_key)])
  ```
- Add `API_KEY` to `.env.example`, `docker-compose.yml` (api + frontend services)
- Update frontend `api-client.ts` to send the header:
  ```typescript
  headers: { "X-API-Key": process.env.NEXT_PUBLIC_API_KEY }
  ```
- Update existing tests: add `X-API-Key` header to all test requests in `conftest.py`

**Files to modify:**
- `src/datapulse/config.py` — add `api_key: str = ""`
- `src/datapulse/api/deps.py` — add `verify_api_key` dependency
- `src/datapulse/api/routes/analytics.py` — add dependency to router
- `src/datapulse/api/routes/pipeline.py` — add dependency to router
- `src/datapulse/api/routes/ai_light.py` — add dependency to router
- `frontend/src/lib/api-client.ts` — add header
- `docker-compose.yml` — add API_KEY env var
- `.env.example` — document API_KEY
- `tests/conftest.py` — add header to test client fixture

---

## 2. Rate Limiting

**Problem:** No request throttling — API can be DDoS'd or abused.

**Implementation:**
- Install `slowapi`: add to `pyproject.toml` dependencies
- Configure in `src/datapulse/api/app.py`:
  ```python
  from slowapi import Limiter
  from slowapi.util import get_remote_address
  from slowapi.errors import RateLimitExceeded

  limiter = Limiter(key_func=get_remote_address)
  app.state.limiter = limiter
  app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
  ```
- Apply limits:
  - Analytics endpoints: `100/minute`
  - Pipeline trigger: `10/minute` (expensive operation)
  - AI-Light endpoints: `20/minute` (external API calls)
  - Health: `200/minute`

**Files to modify:**
- `pyproject.toml` — add `slowapi` dependency
- `src/datapulse/api/app.py` — configure limiter
- `src/datapulse/api/routes/analytics.py` — add `@limiter.limit()` decorators
- `src/datapulse/api/routes/pipeline.py` — add `@limiter.limit()` decorators
- `src/datapulse/api/routes/ai_light.py` — add `@limiter.limit()` decorators

---

## 3. CSP Headers (Content Security Policy)

**Problem:** No browser-side protection against XSS or script injection.

**Implementation:**
- Create `frontend/src/middleware.ts`:
  ```typescript
  import { NextResponse } from "next/server";
  import type { NextRequest } from "next/server";

  export function middleware(request: NextRequest) {
    const response = NextResponse.next();
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    response.headers.set(
      "Content-Security-Policy",
      [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  // Next.js needs these
        "style-src 'self' 'unsafe-inline'",                   // Tailwind needs inline
        "img-src 'self' data: https:",
        "font-src 'self'",
        `connect-src 'self' ${apiUrl}`,
        "frame-ancestors 'none'",
      ].join("; ")
    );

    // Additional security headers
    response.headers.set("X-Frame-Options", "DENY");
    response.headers.set("X-Content-Type-Options", "nosniff");
    response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");

    return response;
  }

  export const config = {
    matcher: "/((?!_next/static|_next/image|favicon.ico).*)",
  };
  ```

**Files to create/modify:**
- `frontend/src/middleware.ts` — new file (the middleware above)

---

## 4. Audit Logging (Nice to Have)

**Problem:** No record of who accessed what data or triggered which operations.

**Implementation:**
- Create migration `migrations/008_create_audit_log.sql`:
  ```sql
  CREATE TABLE IF NOT EXISTS public.audit_log (
      id BIGSERIAL PRIMARY KEY,
      action TEXT NOT NULL,           -- 'pipeline_trigger', 'analytics_query', etc.
      endpoint TEXT NOT NULL,         -- '/api/v1/pipeline/trigger'
      method TEXT NOT NULL,           -- 'GET', 'POST'
      ip_address TEXT,
      user_agent TEXT,
      request_params JSONB DEFAULT '{}',
      response_status INT,
      duration_ms FLOAT,
      created_at TIMESTAMPTZ DEFAULT now()
  );

  CREATE INDEX idx_audit_log_created_at ON public.audit_log (created_at DESC);
  CREATE INDEX idx_audit_log_action ON public.audit_log (action);
  ```
- Add audit middleware in `src/datapulse/api/app.py` (extend existing request logger)
- Log to DB asynchronously (don't slow down requests)

**Priority:** Lower than items 1-3. Can be done after production launch.

---

## Order of Implementation

1. **API Authentication** — do first (blocks other security)
2. **Rate Limiting** — do second (depends on auth being in place)
3. **CSP Headers** — do third (frontend only, independent)
4. **Audit Logging** — do last (nice to have)

Each item is independent and can be a separate commit.
