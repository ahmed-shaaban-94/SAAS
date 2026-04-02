# THE WILD WOLF — Lean Beta Release Plan (v2)

> **Project**: DataPulse — Business/Sales Analytics SaaS
> **Codename**: The Wild Wolf (Lean Edition)
> **Target**: Beta release for 30 testers
> **Timeline**: 3 weeks (trimmed from 4)
> **Budget**: $0 (DigitalOcean $200 + AWS $200)
> **Philosophy**: Ship fast, add tools later. 6 tools instead of 14.

---

## What Changed from v1

| v1 (Original) | v2 (Lean) | Why |
|---------------|-----------|-----|
| 14 external tools | **6 tools** | Most were overkill for 30 users |
| Datadog ($0 Student) | **docker stats** | 30 users don't need APM |
| Doppler (secrets) | **.env on server** | Same result, zero setup |
| Codecov (CI) | **Skipped** | Coverage is 95%, we know |
| Honeybadger (uptime) | **UptimeRobot** | Free forever, same thing |
| Stripe (billing) | **Skipped** | No billing in beta |
| Lightdash (BI) | **Skipped** | Next.js dashboard already exists |
| 4 weeks | **3 weeks** | Less tools = less setup time |

### What We Keep

| Tool | Role | Cost |
|------|------|------|
| **Auth0** | Authentication (replaces Keycloak) | Free (7,500 users) |
| **Sentry** | Error tracking (FastAPI + Next.js) | Free tier (5K errors/mo) |
| **UptimeRobot** | Uptime monitoring | Free (50 monitors) |
| **DigitalOcean** | Hosting (Droplet) | $24/mo from $200 credit |
| **AWS RDS** | Database (PostgreSQL) | ~$15/mo from $200 credit |
| **GitHub Actions** | CI/CD | Free |

---

## Current Progress

| Task | Status | Date |
|------|--------|------|
| Auth0 migration (13 files) | DONE | 2026-04-01 |
| Auth0 account created | DONE | 2026-04-01 |
| Sentry SDK integration (12 files) | DONE | 2026-04-01 |
| Keycloak container removed | DONE | 2026-04-01 |
| n8n Droplet identified for deletion | DONE | 2026-04-01 |
| Android build.gradle.kts production config | DONE | 2026-04-02 |
| Release keystore + signing config | DONE | 2026-04-02 |
| Sentry Android SDK integration | DONE | 2026-04-02 |
| Signed APK built (1.0.0-beta1, 7.5 MB) | DONE | 2026-04-02 |
| Nginx DNS fix + API direct routing | DONE | 2026-04-02 |
| Auth0 Native App (Android) configured | DONE | 2026-04-02 |
| Firebase App Distribution | TODO | - |
| APK tested on real device | TODO | - |
| 30 testers invited | TODO | - |

---

## RAM Budget (Production Droplet)

```
Service              RAM        Notes
─────────────────────────────────────────
FastAPI (4 workers)  512MB      API server
Next.js (SSR)        512MB      Frontend
n8n                  512MB      Workflow automation
Celery Worker        512MB      Async tasks
Redis 7              64MB       Cache + broker
Traefik              64MB       Reverse proxy + SSL
pgAdmin              256MB      DB admin (optional)
─────────────────────────────────────────
Total                ~2.4GB
Droplet              4GB
Free Buffer          ~1.6GB     Plenty of room
```

Note: PostgreSQL moves to AWS RDS. Keycloak removed (Auth0). Jupyter/Lightdash removed (not needed in prod).

---

## PHASE 0: Pre-Flight (Day 1)

> **Goal**: Verify everything works before touching infrastructure

| # | Task | Owner | Time |
|---|------|-------|------|
| 0.1 | Run `pytest` — all tests pass (95%+) | Claude | 15min |
| 0.2 | Run Playwright E2E — 18 specs pass | Claude | 15min |
| 0.3 | `docker compose up --build` — all services healthy | Claude | 10min |
| 0.4 | Test Auth0 login flow (localhost) | User | 10min |
| 0.5 | Test Sentry error capture (trigger test error) | Claude | 5min |
| 0.6 | `pip-audit` + `npm audit` — no critical vulns | Claude | 10min |
| 0.7 | Build Android debug APK | User | 30min |

**Exit Criteria**:
- [ ] All tests green
- [ ] Auth0 login works on localhost
- [ ] Sentry receives test error
- [ ] No critical security vulnerabilities
- [ ] Android APK builds

---

## PHASE 1: Infrastructure (Days 2-5)

> **Goal**: Production server running with HTTPS

### 1.1 DigitalOcean Droplet

| Setting | Value |
|---------|-------|
| Size | s-2vcpu-4gb ($24/mo) |
| Region | Frankfurt (FRA1) — close to EU |
| OS | Ubuntu 24.04 LTS |
| Backups | Yes ($4.80/mo) |

```
User:
├── Activate DigitalOcean account
├── Apply $200 credit (Student Pack or referral)
├── Create API token
└── Give token to Claude

Claude:
├── Create Droplet via API
├── Configure firewall (22, 80, 443 only)
├── Install Docker + Docker Compose
├── Clone repo
├── Create .env with production values
├── docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
└── Verify all services healthy
```

### 1.2 AWS RDS PostgreSQL

| Setting | Value |
|---------|-------|
| Engine | PostgreSQL 16.x |
| Instance | db.t3.micro (Free Tier eligible) |
| Storage | 20GB gp3 |
| Region | eu-central-1 (same as Droplet) |
| Backup | Automated daily, 7-day retention |
| Public Access | No — VPC peering or Security Group |

```
User:
├── Create AWS account (apply $200 education credit)
├── Create IAM user with RDS + S3 permissions
└── Give Access Key + Secret to Claude

Claude:
├── Create RDS instance via CLI
├── Configure Security Group (allow Droplet IP only)
├── Create S3 bucket (datapulse-uploads)
├── pg_dump from Docker PostgreSQL
├── pg_restore to RDS
├── Update DATABASE_URL in .env on Droplet
├── Test: API connects to RDS
└── Verify: all marts tables intact
```

### 1.3 Domain + SSL

```
User:
├── Register datapulse.tech (Student Pack = FREE)
└── Point nameservers to DigitalOcean

Claude:
├── Create DNS records:
│   ├── A     datapulse.tech      → Droplet IP
│   ├── CNAME www                 → datapulse.tech
│   └── CNAME api                 → datapulse.tech
│
├── Configure Traefik:
│   ├── datapulse.tech         → Next.js :3000
│   ├── datapulse.tech/api/*   → FastAPI :8000
│   └── datapulse.tech/health  → FastAPI :8000
│
├── Let's Encrypt auto-SSL via Traefik
└── Test: https://datapulse.tech loads
```

Note: n8n stays internal (no public subdomain needed for beta).

### 1.4 Secrets Management (Simple)

No Doppler. Just a `.env` file on the Droplet:

```bash
# On the Droplet, create /opt/datapulse/.env
# Contains all production secrets:
DATABASE_URL=postgresql://datapulse:xxx@rds-endpoint:5432/datapulse
AUTH0_DOMAIN=datapulse.eu.auth0.com
AUTH0_CLIENT_ID=xxx
AUTH0_CLIENT_SECRET=xxx
SENTRY_DSN=https://xxx@o0.ingest.sentry.io/0
SENTRY_ENVIRONMENT=production
NEXTAUTH_SECRET=xxx
API_KEY=xxx
PIPELINE_WEBHOOK_SECRET=xxx
REDIS_PASSWORD=xxx
```

Security: file permissions `600`, owned by deploy user.

**Exit Criteria**:
- [ ] Droplet running with Docker
- [ ] RDS PostgreSQL accessible from Droplet
- [ ] S3 bucket created
- [ ] Data migrated to RDS
- [ ] datapulse.tech resolving with HTTPS
- [ ] All services healthy on production

---

## PHASE 2: Auth0 Configuration (Days 5-6)

> **Goal**: Auth0 fully configured for production
>
> Code migration already DONE. This phase is Auth0 dashboard setup only.

### 2.1 Auth0 Application Settings

```
Application: Data pulse (Regular Web App) — CREATED
Domain:      datapulse.eu.auth0.com — DONE

Update Callback URLs:
├── http://localhost:3000/api/auth/callback/auth0    (dev)
└── https://datapulse.tech/api/auth/callback/auth0   (prod)

Update Logout URLs:
├── http://localhost:3000    (dev)
└── https://datapulse.tech   (prod)

Update Web Origins:
├── http://localhost:3000    (dev)
└── https://datapulse.tech   (prod)
```

### 2.2 Auth0 API (for Android + audience validation)

```
Auth0 Dashboard → APIs → Create API:
├── Name: DataPulse API
├── Identifier: https://api.datapulse.tech (this becomes AUTH0_AUDIENCE)
├── Signing: RS256
└── Enable RBAC + Add Permissions in Access Token
```

### 2.3 Roles & Permissions

```
Auth0 Dashboard → User Management → Roles:
├── admin:
│   ├── read:analytics
│   ├── write:pipeline
│   └── manage:users
└── viewer:
    └── read:analytics
```

### 2.4 Auth0 Action (Custom Claims)

Create an Action (Login / Post Login) to inject custom claims:

```javascript
exports.onExecutePostLogin = async (event, api) => {
  const namespace = 'https://datapulse.tech';
  
  // Add tenant_id (default 1 for beta)
  api.accessToken.setCustomClaim(`${namespace}/tenant_id`, 1);
  
  // Add roles
  const roles = event.authorization?.roles || [];
  api.accessToken.setCustomClaim(`${namespace}/roles`, roles);
};
```

### 2.5 Create Beta Users

```
Auth0 Dashboard → User Management → Users:
├── Create 30 users manually, OR
├── Use Auth0 bulk import (JSON), OR
└── Enable self-signup (Social/Email) with invite-only:
    Auth0 → Authentication → Database:
    └── Disable Sign Ups = ON (invite only)
```

Recommended for beta: **Disable self-signup**, create accounts manually, send credentials via email.

### 2.6 Android Auth0 Setup

```
Auth0 Dashboard → Applications → Create Application:
├── Name: DataPulse Android
├── Type: Native
├── Allowed Callback URLs: com.datapulse.android:/oauth2callback
├── Allowed Logout URLs: com.datapulse.android:/oauth2callback
└── Copy Client ID → update build.gradle.kts
```

Note: Native apps use a separate Auth0 Application (no client_secret, uses PKCE only).

**Exit Criteria**:
- [ ] Production callback URLs configured
- [ ] API resource created (audience)
- [ ] Roles (admin/viewer) created
- [ ] Custom claims Action deployed
- [ ] Beta users created (or invite-only enabled)
- [ ] Android native app configured
- [ ] Login works on https://datapulse.tech
- [ ] Login works on Android with production API

---

## PHASE 3: Monitoring Setup (Day 7)

> **Goal**: Know when things break before users tell you

### 3.1 Sentry (Already Integrated)

```
User:
├── Sign up at sentry.io (free tier)
├── Create project: datapulse-api (Python / FastAPI)
├── Create project: datapulse-frontend (Next.js)
├── Copy DSN for each project
└── Add DSN to .env on Droplet

Claude (DONE):
├── sentry-sdk[fastapi] in backend
├── @sentry/nextjs in frontend
├── Auto-capture unhandled exceptions
├── Error boundary sends to Sentry
└── Environment tagging (dev/production)
```

Sentry alert rules (configure in dashboard):
- New issue → Email notification
- Issue frequency > 10/hour → Urgent email
- First seen in production → Slack (if configured)

### 3.2 UptimeRobot (After Deploy)

```
User (5 minutes):
├── Sign up at uptimerobot.com (free)
├── Add monitor:
│   ├── Type: HTTPS
│   ├── URL: https://datapulse.tech/health
│   ├── Interval: 5 minutes
│   └── Alert: email
├── Add second monitor (optional):
│   ├── URL: https://datapulse.tech
│   └── Keyword: DataPulse (checks page loads)
└── Done.
```

That's it. Free, instant, reliable.

### 3.3 Monitoring Architecture (Lean)

```
                    ┌─────────────────┐
                    │   datapulse.tech │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        ┌─────┴─────┐ ┌─────┴─────┐ ┌─────┴─────┐
        │  Sentry   │ │UptimeRobot│ │  Logs     │
        │           │ │           │ │           │
        │  Errors   │ │  "Is it   │ │  docker   │
        │  Stack    │ │   up?"    │ │  compose  │
        │  traces   │ │           │ │  logs -f  │
        │  Context  │ │  5 min    │ │           │
        └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────┴────────┐
                    │   Your Email    │
                    └─────────────────┘

  Sentry:      "TypeError at repository.py:47"
  UptimeRobot: "datapulse.tech is DOWN"
  Logs:        docker compose logs -f api  (SSH into Droplet)
```

**Exit Criteria**:
- [ ] Sentry DSN in production .env
- [ ] Sentry receives test error from production
- [ ] UptimeRobot monitoring https://datapulse.tech/health
- [ ] Email alerts working

---

## PHASE 4: Android Release (Days 8-11)

> **Goal**: APK in testers' hands

### 4.1 Production Config

```kotlin
// build.gradle.kts — release buildType
release {
    buildConfigField("String", "API_BASE_URL",
        "\"https://datapulse.tech\"")      // Traefik routes /api/* to FastAPI
    buildConfigField("String", "AUTH0_DOMAIN",
        "\"datapulse.eu.auth0.com\"")
    buildConfigField("String", "AUTH0_CLIENT_ID",
        "\"<native-app-client-id>\"")      // From Auth0 Native app
    isMinifyEnabled = true
    proguardFiles(...)
    signingConfig = signingConfigs.getByName("release")
}
```

### 4.2 Release Checklist

| # | Task | Owner | Time |
|---|------|-------|------|
| 4.1 | Update build.gradle.kts with production URLs | Claude | 10min |
| 4.2 | Create release keystore | User | 10min |
| 4.3 | Build signed APK | User | 15min |
| 4.4 | Test all 9 screens with production API | User | 30min |
| 4.5 | Fix any issues | Claude | varies |
| 4.6 | Upload to Firebase App Distribution | User | 10min |
| 4.7 | Invite 30 testers | User | 10min |

### 4.3 Firebase App Distribution (Free)

```
User:
├── Create Firebase project (free)
├── Add Android app (com.datapulse.android)
├── Upload signed APK to App Distribution
├── Add tester emails (same 30 as Auth0)
└── Testers get email → install APK
```

No Play Store needed for beta. Firebase handles distribution.

**Exit Criteria**:
- [ ] Signed APK built with production config
- [ ] All 9 screens work with production API
- [ ] Auth0 login works on Android
- [ ] APK uploaded to Firebase
- [ ] 30 testers invited

---

## PHASE 5: Beta Launch (Days 12-21)

> **Goal**: 30 users testing, feedback flowing, bugs squashed

### Launch Day Checklist

```
[ ] https://datapulse.tech loads with HTTPS
[ ] Auth0 login works (web)
[ ] Auth0 login works (Android)
[ ] All 6 dashboard pages render data
[ ] Pipeline trigger works
[ ] Sentry is capturing (test error)
[ ] UptimeRobot is monitoring
[ ] 30 Auth0 accounts created
[ ] Firebase APK distributed
[ ] Feedback form ready (Google Forms)
[ ] Backup verified (RDS automated)
```

### Daily Routine (10 min/day)

```
Morning:
├── Check UptimeRobot — any downtime?
├── Check Sentry — new errors?
├── Check feedback form — new responses?
└── Fix anything critical

Weekly:
├── SSH to Droplet: docker stats (check RAM/CPU)
├── Review Sentry error trends
├── Compile feedback summary
└── Deploy fixes: git pull && docker compose up -d --build
```

### Deploy Process (Simple)

```bash
# SSH into Droplet
ssh deploy@datapulse.tech

# Pull latest code
cd /opt/datapulse
git pull origin main

# Rebuild and restart
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Verify
docker compose ps       # all services healthy?
curl https://datapulse.tech/health   # API responds?
```

Future: GitHub Actions auto-deploy on push to main. Not needed for beta with 30 users.

### Success Metrics

| Metric | Target | How to Check |
|--------|--------|-------------|
| Uptime | > 99% | UptimeRobot dashboard |
| API p95 latency | < 500ms | Sentry performance tab |
| Error rate | < 1% | Sentry issues |
| Active users | 20+ of 30 | Auth0 dashboard → Users |
| Crash-free (Android) | > 99% | Firebase Crashlytics |
| Feedback responses | 15+ | Google Forms |
| Critical bugs | 0 open | Sentry |

### Feedback Form (Google Forms)

```
Questions:
1. How easy was it to log in? (1-5)
2. Which pages did you use? (checkboxes)
3. How useful is the dashboard? (1-5)
4. Did you encounter any errors? (text)
5. What feature would you add? (text)
6. Would you use this daily? (yes/no/maybe)
7. Overall rating (1-10)
```

---

## Budget (Lean)

### Monthly Cost

| Service | Cost | Source |
|---------|------|--------|
| Droplet (4GB) | $24.00 | DO credit |
| Backups | $4.80 | DO credit |
| RDS (db.t3.micro) | ~$15.00 | AWS credit |
| S3 | ~$0.50 | AWS credit |
| Auth0 | $0 | Free tier |
| Sentry | $0 | Free tier |
| UptimeRobot | $0 | Free tier |
| GitHub Actions | $0 | Free tier |
| Firebase | $0 | Free tier |
| **Total** | **~$44/mo** | **From credits = $0** |

### Runway

```
DigitalOcean: $200 / $29/mo = ~7 months
AWS:          $200 / $16/mo = ~12 months
───────────────────────────────────────
Effective: ~8 months at $0 out of pocket
After credits expire: ~$44/month
```

### v1 vs v2 Budget Comparison

```
v1 (Original):  14 tools, $47/mo, complex setup
v2 (Lean):       6 tools, $44/mo, minimal setup
                                   ^^^
              Same cost, half the complexity.
```

---

## Risk Matrix

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Auth0 flow breaks in prod | HIGH | LOW | Already tested on localhost |
| Droplet runs out of RAM | MEDIUM | LOW | 1.6GB free buffer, no Keycloak/Jupyter |
| RDS connection slow | MEDIUM | LOW | Same region (eu-central-1 / FRA1) |
| Data loss during migration | HIGH | LOW | pg_dump backup before migration |
| 30 users find critical bug | MEDIUM | MEDIUM | Sentry alerts → fix in < 24h |
| SSL certificate issues | MEDIUM | LOW | Traefik + Let's Encrypt = auto |
| Credits expire mid-beta | LOW | LOW | 8 month runway > 3 week beta |
| Android crashes on some devices | MEDIUM | MEDIUM | Firebase Crashlytics |

---

## Timeline

```
Week 1              Week 2              Week 3
────────────────    ────────────────    ────────────────
Day 1               Days 5-6            Days 12-21
PHASE 0             PHASE 2             PHASE 5
Pre-flight          Auth0 config        BETA LAUNCH
Tests + audit       Dashboard setup     30 users
                    Roles + users       Monitor
Days 2-5                                Feedback
PHASE 1             Day 7               Iterate
DigitalOcean        PHASE 3             Fix bugs
AWS RDS             Sentry setup
Domain + SSL        UptimeRobot
Data migration
                    Days 8-11
                    PHASE 4
                    Android APK
                    Firebase dist
```

---

## Go/No-Go Checklist

| # | Check | Required |
|---|-------|----------|
| 1 | pytest passes (95%+) | MUST |
| 2 | Playwright E2E passes | MUST |
| 3 | Auth0 login works (web) | MUST |
| 4 | Auth0 login works (Android) | MUST |
| 5 | https://datapulse.tech loads | MUST |
| 6 | API responds < 500ms | MUST |
| 7 | SSL certificate valid | MUST |
| 8 | Sentry receiving errors | MUST |
| 9 | UptimeRobot monitoring | MUST |
| 10 | RDS backups enabled | MUST |
| 11 | 30 user accounts created | MUST |
| 12 | Android APK on Firebase | MUST |
| 13 | Feedback form ready | MUST |
| 14 | GitHub Actions CI green | NICE |

---

## Tools We Can Add Later (When Needed)

| Tool | When to Add | Trigger |
|------|-------------|---------|
| Datadog | > 100 users | Need APM, not just error tracking |
| Doppler | Multi-env deploys | When staging environment is needed |
| Codecov | PR-heavy phase | When multiple contributors join |
| Stripe | Revenue phase | When billing is implemented |
| Cloudflare | High traffic | When CDN/DDoS protection needed |
| GitHub Actions CD | Frequent deploys | When manual SSH deploy is annoying |

---

*The lean wolf hunts smarter, not harder.*

*Plan updated: 2026-04-01*
*Revision: v2 (Lean)*
*Agent: Claude Opus 4.6*
