# ADR-004: CSP scoped to API routes, not global Nginx

**Status**: Accepted  
**Date**: 2026-04-09  
**Deciders**: Platform Engineer

## Context

During the hardening sprint, a strict Content Security Policy (CSP) was added. The initial implementation placed it as a global `add_header` directive in the Nginx `server {}` block, which applied to all responses.

This caused an immediate conflict: Next.js 14 requires `'unsafe-inline'` in `script-src` for its hydration mechanism. A strict `default-src 'none'` global CSP broke the frontend completely.

Two middleware layers own CSP:
1. **Nginx** — at the network edge, for FastAPI responses
2. **Next.js middleware** (`frontend/src/middleware.ts`) — for Next.js page responses, with inline script nonces

## Decision

**Scope CSP to API routes only in Nginx.** Remove the global `add_header Content-Security-Policy` and add a targeted CSP only inside the `/api/v1/` location block:

```nginx
location /api/v1/ {
    add_header Content-Security-Policy "default-src 'none'; frame-ancestors 'none';" always;
}
```

The Next.js middleware (`frontend/src/middleware.ts`) continues to own the frontend CSP with appropriate `'unsafe-inline'` allowances for hydration.

This follows the principle that **each layer owns its own CSP** — the API backend has no need for `script-src`, `style-src`, or `img-src` (it only serves JSON), so a strict `default-src 'none'` is correct and safe.

## Consequences

**Good:**
- API endpoints have the strictest possible CSP (`default-src 'none'`) with no exceptions
- Frontend CSP is managed by Next.js middleware which understands its own nonce requirements
- No cross-layer CSP conflicts

**Risks/trade-offs:**
- Two places manage CSP (Nginx for API, Next.js middleware for frontend) — maintainers must know to update both
- If a new API location block is added in Nginx without a CSP header, it gets no CSP (acceptable since API responses are JSON)
