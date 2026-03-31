# Security Audit

Security validation checklist for the DataPulse platform: authentication, authorization, data isolation, network security, and OWASP controls.

## Current State (DONE)

- **Authentication**: Keycloak OIDC with JWT validation
- **Authorization**: Tenant-scoped RLS on all data tables
- **Users**: `demo-admin` (admin role), `demo-viewer` (viewer role)
- **Rate limiting**: 60/min analytics, 5/min pipeline mutations
- **CORS**: Restricted origins and headers
- **Security headers**: X-Content-Type-Options, X-Frame-Options, Referrer-Policy
- **Docker**: Ports bound to `127.0.0.1`

## Authentication Validation

### Keycloak OIDC

| Check | How to Validate | Status |
|-------|----------------|--------|
| JWT signature validation | Send request with tampered JWT -- expect 401 | DONE |
| Expired token rejection | Send request with expired JWT -- expect 401 | DONE |
| Missing token rejection | Send request with no Authorization header -- expect 401 | DONE |
| Role-based access | `demo-viewer` cannot trigger pipeline -- expect 403 | DONE |
| Token refresh flow | Frontend refreshes token before expiry | DONE |

```bash
# Test: missing token
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/analytics/summary
# Expected: 401

# Test: invalid token
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer invalid.token.here" \
  http://localhost:8000/api/v1/analytics/summary
# Expected: 401

# Test: valid token (obtain from Keycloak first)
TOKEN=$(curl -s -X POST http://localhost:8080/realms/datapulse/protocol/openid-connect/token \
  -d "client_id=datapulse-api" \
  -d "username=demo-admin" \
  -d "password=<password>" \
  -d "grant_type=password" | jq -r '.access_token')

curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/analytics/summary
# Expected: 200
```

### JWT Validation (`src/datapulse/api/jwt.py`)

- [x] Validates token signature against Keycloak public key
- [x] Checks `exp` (expiry) claim
- [x] Checks `iss` (issuer) claim matches Keycloak realm
- [x] Extracts `tenant_id` from custom claims
- [x] Extracts roles from `realm_access.roles`

## Row-Level Security (RLS)

### Tables with RLS

| Table | Policy | Status |
|-------|--------|--------|
| `bronze.sales` | `tenant_id = current_setting('app.tenant_id')` | DONE |
| `public_staging.stg_sales` | `security_invoker=on` (view) | DONE |
| `public_marts.dim_*` | RLS policy on tenant_id | DONE |
| `public_marts.fct_sales` | RLS policy on tenant_id | DONE |
| `public_marts.agg_*` | RLS policy on tenant_id | DONE |
| `public.pipeline_runs` | RLS policy on tenant_id | DONE |
| `public.quality_checks` | RLS policy on tenant_id | DONE |

### RLS Validation Commands

```sql
-- Connect as the app user (not superuser)
-- Verify RLS is enabled
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname IN ('bronze', 'public_staging', 'public_marts', 'public')
  AND rowsecurity = true;

-- Verify FORCE ROW LEVEL SECURITY
SELECT relname, relforcerowsecurity
FROM pg_class
WHERE relname IN ('sales', 'fct_sales', 'pipeline_runs', 'quality_checks');

-- Test tenant isolation: set tenant A, query, verify no tenant B data
SET LOCAL app.tenant_id = 'tenant-a-uuid';
SELECT COUNT(*) FROM bronze.sales;  -- Should return only tenant A rows

SET LOCAL app.tenant_id = 'tenant-b-uuid';
SELECT COUNT(*) FROM bronze.sales;  -- Should return only tenant B rows

-- Test: no tenant_id set -> zero rows (not an error)
RESET app.tenant_id;
SELECT COUNT(*) FROM bronze.sales;  -- Should return 0
```

### Owner Bypass Prevention

```sql
-- Verify FORCE ROW LEVEL SECURITY is set (prevents table owner from bypassing)
SELECT relname, relforcerowsecurity
FROM pg_class c
JOIN pg_namespace n ON c.relnamespace = n.oid
WHERE n.nspname = 'bronze' AND c.relname = 'sales';
-- relforcerowsecurity should be TRUE
```

## CORS Validation

### Allowed Configuration

```python
# src/datapulse/api/app.py
CORS_ORIGINS = ["http://localhost:3000"]
CORS_HEADERS = ["Content-Type", "Authorization", "X-API-Key", "X-Pipeline-Token"]
```

### Validation Commands

```bash
# Test: allowed origin
curl -s -o /dev/null -w "%{http_code}" \
  -H "Origin: http://localhost:3000" \
  -X OPTIONS \
  http://localhost:8000/api/v1/analytics/summary
# Expected: 200 with Access-Control-Allow-Origin header

# Test: disallowed origin
curl -s -D - \
  -H "Origin: http://evil.com" \
  -X OPTIONS \
  http://localhost:8000/api/v1/analytics/summary
# Expected: No Access-Control-Allow-Origin header in response

# Test: disallowed header
curl -s -D - \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Headers: X-Evil-Header" \
  -X OPTIONS \
  http://localhost:8000/api/v1/analytics/summary
# Expected: X-Evil-Header not in Access-Control-Allow-Headers
```

## Security Headers

### Expected Headers

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limit referrer leakage |

```bash
# Verify headers
curl -s -D - http://localhost:8000/health | grep -E "X-Content-Type|X-Frame|Referrer"
```

## Rate Limiting

| Endpoint Group | Limit | Status |
|---------------|-------|--------|
| Analytics (`/api/v1/analytics/*`) | 60 requests/minute | DONE |
| Pipeline mutations (`POST /api/v1/pipeline/*`) | 5 requests/minute | DONE |
| Health (`/health`) | No limit | DONE |

### Validation

```bash
# Test rate limiting (send 61 requests rapidly)
for i in $(seq 1 61); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -H "Authorization: Bearer $TOKEN" \
    http://localhost:8000/api/v1/analytics/summary
done
# Expected: first 60 return 200, 61st returns 429
```

## SQL Injection Prevention

| Control | Location | Status |
|---------|----------|--------|
| Column whitelist before INSERT | `bronze/loader.py` | DONE |
| SQLAlchemy parameterised queries | `analytics/repository.py` | DONE |
| No raw SQL string concatenation | All modules | DONE |
| Pydantic validation on all inputs | `api/routes/*.py` | DONE |

## OWASP Top 10 Checklist

| # | Risk | Mitigation | Status |
|---|------|-----------|--------|
| A01 | Broken Access Control | Keycloak OIDC + RLS + role checks | DONE |
| A02 | Cryptographic Failures | TLS in production, NUMERIC for money | DONE |
| A03 | Injection | Parameterised queries, column whitelist | DONE |
| A04 | Insecure Design | Tenant isolation by design, RLS | DONE |
| A05 | Security Misconfiguration | CORS restricted, ports 127.0.0.1 only | DONE |
| A06 | Vulnerable Components | Pin dependency versions | DONE |
| A07 | Auth Failures | Keycloak, JWT validation, rate limiting | DONE |
| A08 | Data Integrity Failures | Quality gates, schema validation | DONE |
| A09 | Logging Failures | structlog JSON logging, error tracking | DONE |
| A10 | SSRF | No user-controlled URLs in backend | DONE |

## Docker Network Security

| Control | Status |
|---------|--------|
| All ports bound to `127.0.0.1` (not `0.0.0.0`) | DONE |
| Internal services (Redis) not exposed on host | DONE |
| Keycloak admin console on localhost only | DONE |
| `.env` file excluded from Docker image (`.dockerignore`) | DONE |

## Recommended Additions (TODO)

### Dependency Scanning

- [ ] Add `pip-audit` to CI for Python dependency CVE scanning
- [ ] Add `npm audit` to CI for frontend dependency scanning

```bash
pip install pip-audit
pip-audit

cd frontend && npm audit
```

### Secret Scanning

- [ ] Verify no secrets in git history: `git log --all -p | grep -i "password\|secret\|api_key"`
- [ ] Add pre-commit hook with `detect-secrets`

### Penetration Testing Checklist

- [ ] Test IDOR: can user A access user B's pipeline runs by UUID?
- [ ] Test privilege escalation: can `demo-viewer` call pipeline trigger?
- [ ] Test session fixation: does Keycloak rotate session on login?
- [ ] Test CSRF: are state-changing requests protected?

### Monitoring

- [ ] Alert on repeated 401/403 responses (brute force detection)
- [ ] Alert on rate limit hits (429 responses)
- [ ] Log and alert on RLS policy violations
