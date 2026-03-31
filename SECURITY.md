# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.6.x (latest) | :white_check_mark: |
| < 0.6.0 | :x: |

## Reporting a Vulnerability

If you discover a security vulnerability in DataPulse, please report it responsibly.

**Email**: ahmed.shaaban.94@outlook.com

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours and work with you to resolve the issue.

## Security Measures

### Authentication & Authorization
- **Keycloak OIDC**: OAuth2/OpenID Connect authentication
- **JWT Validation**: Backend validates tokens via `src/datapulse/api/jwt.py`
- **NextAuth**: Frontend session management via `frontend/src/lib/auth.ts`
- **Demo Users**: `demo-admin` (admin role), `demo-viewer` (viewer role)
- **Tenant-Scoped RLS**: Row Level Security on all data layers with `SET LOCAL app.tenant_id`
- **FORCE ROW LEVEL SECURITY**: Owner bypass prevented on all RLS-enabled tables

### API Security
- **Rate Limiting**: 60 req/min analytics, 5 req/min pipeline mutations
- **CORS Whitelist**: Restricted to configured origins
- **Security Headers**: X-Content-Type-Options, X-Frame-Options, Referrer-Policy
- **Global Exception Handler**: Generic 500 responses (no stack traces to clients)
- **Health Endpoint**: Returns 503 when DB unreachable (not 200)
- **Pipeline Token**: Webhook trigger requires `X-Pipeline-Token` header

### Data Protection
- **SQL Column Whitelist**: Prevents injection on INSERT operations
- **Financial Precision**: `NUMERIC(18,4)` for all monetary values
- **JsonDecimal**: Internal Decimal precision, float serialization in JSON
- **Credentials**: All secrets via `.env` file (never hardcoded in source)

### Network Security
- **Docker Ports**: Bound to `127.0.0.1` only in development
- **Traefik**: Reverse proxy with TLS in production
- **Internal Services**: Redis, PostgreSQL not exposed externally

### Resolved Findings
- See [The Great Fix](./docs/reports/The%20Great%20Fix.md) for the full security remediation report (10 CRITICAL + 29 HIGH findings resolved)
