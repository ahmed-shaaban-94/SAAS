# ADR-001: Multi-strategy authentication (Auth0 + API Key + dev fallback)

**Status**: Accepted  
**Date**: 2026-04-09  
**Deciders**: Platform Engineer

## Context

DataPulse serves two types of callers:
1. **Browser clients** — end users interacting via the Next.js dashboard
2. **Service accounts** — n8n workflows, pipeline triggers, and internal automation

Both callers need secure API access, but their auth flows differ fundamentally: browser clients use OAuth2/OIDC (redirect flows, cookies, token refresh), while service accounts use long-lived API keys.

In addition, local development requires a way to run the API without a full Auth0 tenant configured.

## Decision

Implement three authentication strategies in `src/datapulse/api/auth.py` with a strict priority order:

1. **Bearer JWT** (primary) — Auth0-issued OIDC tokens, validated against Auth0's JWKS endpoint. Extracts `tenant_id`, `email`, and `role` from claims. Used by the Next.js frontend.
2. **API Key** (`X-API-Key` header) — Long-lived key from the `API_KEY` env var. Used by n8n workflows and pipeline automation. Returns a fixed service account identity.
3. **Dev mode fallback** — Only active when `AUTH_DISABLED=true` (never set in production). Returns a mock superuser. Gated by a startup warning log.

`get_optional_user` in `auth.py` catches only `401`/`403` HTTP exceptions; `503` (Auth0 outage) is re-raised to surface infrastructure problems rather than silently granting anonymous access.

## Consequences

**Good:**
- Browser and service-to-service auth are handled without separate middleware stacks
- Dev mode allows running the full API locally without a live Auth0 tenant
- Single `get_current_user` dependency used across all route handlers

**Risks/trade-offs:**
- API Key is a single shared secret — no per-consumer rotation or revocation
- Dev mode is a footgun if accidentally enabled in production (mitigated by startup assertion in `config.py`)
- Auth0 JWKS keys are cached in memory — a key rotation requires a container restart unless JWKS TTL cache is configured
