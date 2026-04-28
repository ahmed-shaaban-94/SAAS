# pos.smartdatapulse.tech — POS API Subdomain

**Date:** 2026-04-28  
**Status:** approved  
**Scope:** Nginx config + installer `.env` only — no new containers, no FastAPI changes

---

## Problem

The POS desktop app (Electron + embedded Next.js) calls the FastAPI backend at
`smartdatapulse.tech/api/v1/`. That shared vhost also serves the dashboard
frontend, Grafana, OpenAPI docs, NextAuth, and file uploads. POS traffic is
mixed into the same logs, rate-limit zone, and attack surface as every other
client.

---

## Solution

Add `pos.smartdatapulse.tech` as a dedicated Nginx server block on the same
droplet pointing at the same `api_upstream` (FastAPI, port 8000). No new
containers, no new ports, no extra cost.

### What the POS subdomain exposes

| Path | Behaviour |
|------|-----------|
| `/api/v1/` | proxied to FastAPI |
| `/health` | proxied to FastAPI (health probe) |
| everything else | `404` — not reachable |

`/grafana/`, `/docs`, `/openapi.json`, `/_next/`, NextAuth (`/api/auth/`),
and the entire frontend are **not reachable** from the POS subdomain. This
is the primary security win over sharing the main vhost.

### What stays unchanged

- `smartdatapulse.tech/api/v1/` continues to serve the API — backward compat,
  no existing pilot breaks.
- FastAPI CORS is unchanged: `middleware.py` already allows
  `http://localhost:3847` unconditionally. The subdomain is transparent to
  FastAPI.
- Origin cert (`traefik/certs/origin.crt`) already carries
  `subjectAltName=DNS:*.smartdatapulse.tech` — no cert change needed.

---

## Architecture

```
Cloudflare DNS
  pos.smartdatapulse.tech  A → 164.92.243.3  (orange-cloud, proxied)

Droplet (164.92.243.3)
  Nginx
  ├── :80  pos.smartdatapulse.tech  → 301 HTTPS
  └── :443 pos.smartdatapulse.tech
        /api/v1/  → api_upstream (FastAPI :8000)
        /health   → api_upstream
        /*        → 404
```

---

## Nginx changes

### 1. New rate-limit zone (http context, top of file)

```nginx
limit_req_zone $binary_remote_addr zone=pos_api_zone:10m rate=10r/s;
```

Same rate as the existing zones, but isolated — POS burst traffic cannot
exhaust the dashboard's `api_zone` bucket.

### 2. Security headers include file

Extract the 5 common security headers into `nginx/security-headers.inc` and
`include` from both the main server block and the new POS block. Avoids
duplication and guarantees HSTS/nosniff/etc. are never forgotten on a new vhost.

### 3. Two new server blocks

```nginx
# HTTP redirect
server {
    listen 80;
    server_name pos.smartdatapulse.tech;
    return 301 https://$host$request_uri;
}

# HTTPS POS-only vhost
server {
    listen 443 ssl;
    http2 on;
    server_name pos.smartdatapulse.tech;

    ssl_certificate     /etc/nginx/certs/origin.crt;
    ssl_certificate_key /etc/nginx/certs/origin.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers   ECDHE-ECDSA-AES128-GCM-SHA256:...;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    resolver 127.0.0.11 valid=30s;

    # Isolated log — key reason for a separate vhost
    access_log /var/log/nginx/pos_access.log json_combined;

    # POS payloads are JSON cart mutations (<10 KB) — not file uploads
    client_max_body_size 1M;

    # Never swap API JSON errors for branded HTML error pages
    proxy_intercept_errors off;

    keepalive_timeout 65;
    keepalive_requests 1000;
    proxy_buffering on;
    proxy_buffer_size 16k;
    proxy_buffers 8 32k;
    proxy_busy_buffers_size 64k;
    proxy_connect_timeout 10s;
    proxy_send_timeout 120s;
    proxy_read_timeout 300s;

    include /etc/nginx/conf.d/security-headers.inc;

    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Connection        "";
    proxy_http_version 1.1;

    location /api/v1/ {
        proxy_pass http://api_upstream;
        proxy_pass_request_headers on;
        limit_req zone=pos_api_zone burst=20 nodelay;
        add_header Content-Security-Policy "default-src 'none'; frame-ancestors 'none';" always;
        add_header X-Content-Type-Options "nosniff" always;
    }

    location /health {
        proxy_pass http://api_upstream;
        access_log off;
    }

    location / {
        return 404;
    }
}
```

---

## Installer `.env` rollout

**New installer** (next release): set in the bundled `.env`:
```
NEXT_PUBLIC_API_URL=https://pos.smartdatapulse.tech
```

**Existing pilots**: no change. Their `.env` either has
`NEXT_PUBLIC_API_URL=https://smartdatapulse.tech` explicitly, or they fall
through to the hardcoded fallback in `push.ts:50` (`"https://smartdatapulse.tech"`).
Both continue working — the main vhost `/api/v1/` block is untouched.

**Hardcoded fallback**: keep `"https://smartdatapulse.tech"` in `push.ts:50`
for this release. Flip to `"https://pos.smartdatapulse.tech"` in a follow-up
cleanup PR after all active pilots have upgraded.

---

## Pre-merge checklist

- [ ] Cloudflare DNS: `dig pos.smartdatapulse.tech` resolves to a **Cloudflare IP**
      (orange-cloud/proxied), not directly to `164.92.243.3`. If grey-cloud,
      browsers will reject the origin cert (not CA-trusted).
- [ ] `nginx -t` passes on the droplet after applying the config
- [ ] `curl -I https://pos.smartdatapulse.tech/health` returns 200
- [ ] `curl -I https://pos.smartdatapulse.tech/docs` returns 404
- [ ] `curl -I https://pos.smartdatapulse.tech/grafana/` returns 404
- [ ] `curl -I https://smartdatapulse.tech/api/v1/health` still returns 200
      (backward compat check)
- [ ] HSTS header present on POS subdomain response

---

## Files changed

| File | Change |
|------|--------|
| `nginx/default.conf` | Add `pos_api_zone`, extract security headers include, add 2 server blocks |
| `nginx/security-headers.inc` | New — extracted security headers shared by both vhosts |
| `pos-desktop/.env.example` | Document `NEXT_PUBLIC_API_URL=https://pos.smartdatapulse.tech` |
