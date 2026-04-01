# 🐺 THE WILD WOLF — Beta Release Plan

> **Project**: DataPulse — Business/Sales Analytics SaaS
> **Codename**: The Wild Wolf
> **Target**: Beta release for 30 testers
> **Timeline**: 4 weeks
> **Budget**: $0 (Student Pack + Credits)

---

## 📋 Executive Summary

| Item | Detail |
|------|--------|
| **Goal** | Launch DataPulse beta (web + Android) for 30 users |
| **Budget** | $0 — DigitalOcean $200 + AWS $200 + Student Pack |
| **Timeline** | 4 weeks (5 phases) |
| **Platforms** | Web (Next.js) + Android (Kotlin/Compose) |
| **Auth** | Auth0 (replaces Keycloak, saves 512MB RAM) |
| **Hosting** | DigitalOcean Droplet + AWS RDS/S3 |
| **Monitoring** | Datadog + Sentry + Honeybadger |
| **CI/CD** | GitHub Actions (existing) + deploy-staging + deploy-prod |

---

## 🏗️ Current State Assessment

### Backend (FastAPI)

| Metric | Status | Notes |
|--------|--------|-------|
| API Endpoints | 14+ | Analytics (10) + Pipeline (4) |
| Test Coverage | 95%+ | pytest + pytest-cov |
| Security | ✅ | RLS, JWT, rate limiting, CORS |
| Authentication | ⚠️ | Keycloak (to migrate → Auth0) |
| Async Tasks | ✅ | Celery + Redis |
| Data Pipeline | ✅ | Bronze → Silver → Gold |
| dbt Models | ✅ | 6 dims + 1 fact + 8 aggs |

### Frontend (Next.js 14)

| Metric | Status | Notes |
|--------|--------|-------|
| Pages | 6 | Dashboard, Products, Customers, Staff, Sites, Returns |
| E2E Tests | 18+ specs | Playwright (Chromium) |
| Theme | ✅ | Dark/Light mode |
| Auth | ✅ | NextAuth (to swap provider) |
| Mobile | ✅ | Touch swipe, responsive |
| Print Report | ✅ | /dashboard/report |

### Android App (Kotlin + Compose)

| Metric | Status | Notes |
|--------|--------|-------|
| Screens | 9 | Login, Dashboard, Products, Customers, Staff, Sites, Returns, Pipeline, Settings |
| Architecture | ✅ | Clean Architecture + MVVM |
| Auth | ⚠️ | AppAuth + Keycloak (to migrate → Auth0) |
| Caching | ✅ | Room DB + cache-first strategy |
| State | ✅ | StateFlow + Resource pattern |
| Charts | ✅ | Vico Charts 2.0 |
| Completeness | ~80% | Core flows done, edge cases pending |

### Infrastructure

| Service | Container | RAM | Status |
|---------|-----------|-----|--------|
| FastAPI | datapulse-api | 512MB | ✅ |
| Next.js | datapulse-frontend | 512MB | ✅ |
| PostgreSQL 16 | datapulse-db | 2GB | ✅ (→ AWS RDS) |
| Keycloak | datapulse-keycloak | 512MB | ⚠️ (→ Auth0) |
| n8n | datapulse-n8n | 512MB | ✅ |
| Redis 7 | datapulse-redis | 64MB | ✅ |
| Celery | celery-worker | 512MB | ✅ |
| Traefik | traefik | 64MB | ✅ |
| pgAdmin | datapulse-pgadmin | 256MB | ✅ |
| Lightdash | lightdash | 1GB | ✅ |
| Jupyter | datapulse-app | 2GB | ❌ (not needed in prod) |
| **Total** | | **~7.4GB** | |

---

## 🆓 Free Tools Inventory

### Student Pack — API-Enabled (Claude can configure)

| Tool | Value | Duration | API Key? | Role in Wild Wolf |
|------|-------|----------|----------|-------------------|
| **Datadog** | $15/host/mo | 2 years | ✅ API + App Key | Infrastructure + APM monitoring |
| **Sentry** | $26/mo | 1 year | ✅ DSN | Error tracking (FastAPI + Next.js) |
| **Doppler** | $10/mo | Student | ✅ Service Token | Secret management (replace .env) |
| **Codecov** | $15/mo | Forever | ✅ Upload Token | CI test coverage reports |
| **Auth0** | $23/mo | 7,500 users | ✅ Client ID/Secret | Authentication (replace Keycloak) |
| **Stripe** | 2.9% fees | Waived $1K | ✅ API Keys | Future: subscription billing |
| **Honeybadger** | $19/mo | Free tier | ✅ API Key | Uptime monitoring |

### Student Pack — Personal Use (No API needed)

| Tool | Value | Duration | Role |
|------|-------|----------|------|
| **GitHub Copilot** | $10/mo | Student | AI code assistant |
| **JetBrains** | $25/mo | 1 year | PyCharm Pro + WebStorm |
| **1Password** | $3/mo | 1 year | Store all API keys safely |
| **Domain (.tech/.app)** | $10-15/yr | 1 year | datapulse.tech |

### Cloud Credits

| Provider | Credit | Monthly Burn | Runway |
|----------|--------|-------------|--------|
| **DigitalOcean** | $200 | ~$24/mo | ~8 months |
| **AWS** | $200 | ~$20-30/mo | ~7 months |
| **Total** | **$400** | ~$50/mo | **~8 months** |

### Total Value

```
Student Pack tools:  ~$2,000/year
Cloud credits:       $400
IDE + Copilot:       ~$420/year
─────────────────────────────────
Total:               ~$2,820 FREE
```

---

## 📅 Phase Breakdown

### PHASE 0: Pre-Flight Check (Days 1-3)

> **Goal**: Verify everything works before touching infrastructure

| # | Task | Owner | Agent | Time |
|---|------|-------|-------|------|
| 0.1 | Run full pytest suite (95%+ pass) | Claude | tdd-guide | 30min |
| 0.2 | Run Playwright E2E (18 specs pass) | Claude | e2e-runner | 30min |
| 0.3 | Build Android debug APK | User | — | 30min |
| 0.4 | Security scan (OWASP Top 10) | Claude | security-reviewer | 1hr |
| 0.5 | Dependency audit (pip-audit + npm audit) | Claude | build-error-resolver | 30min |
| 0.6 | Docker build all targets | Claude | docker-specialist | 30min |

**Exit Criteria**:
- [ ] All tests pass
- [ ] No CRITICAL security issues
- [ ] All Docker images build
- [ ] Android APK builds successfully

---

### PHASE 1: Infrastructure Setup (Days 3-7)

> **Goal**: Production hosting ready

#### 1.1 DigitalOcean Droplet

| Setting | Value |
|---------|-------|
| Region | Frankfurt (EU) or NYC |
| Size | s-2vcpu-4gb ($24/mo) |
| OS | Ubuntu 24.04 LTS |
| Features | Monitoring, IPv6, backups ($4.80/mo) |

```
User activates:
├── DigitalOcean account (Student Pack)
├── Creates API Token
└── Gives token to Claude

Claude configures:
├── Creates Droplet via API
├── Sets up firewall (80, 443, 22 only)
├── Installs Docker + Docker Compose
├── Configures Traefik + Let's Encrypt SSL
└── Deploys docker-compose (without Keycloak & Jupyter)
```

#### 1.2 AWS RDS PostgreSQL

| Setting | Value |
|---------|-------|
| Engine | PostgreSQL 16 |
| Instance | db.t3.micro (Free Tier eligible) |
| Storage | 20GB gp3 |
| Backup | Automated daily, 7-day retention |
| Multi-AZ | No (beta phase) |

```
User activates:
├── AWS account (education credit)
├── Creates IAM user + Access Keys
└── Gives keys to Claude

Claude configures:
├── Creates RDS instance via CLI
├── Creates S3 bucket for file uploads
├── Migrates data from Docker PostgreSQL → RDS
├── Updates DATABASE_URL in Doppler
└── Tests connectivity from Droplet
```

#### 1.3 Domain + DNS

```
User:
├── Registers datapulse.tech (FREE via Student Pack)
└── Points nameservers to DigitalOcean

Claude:
├── Creates DNS records:
│   ├── A     datapulse.tech      → Droplet IP
│   ├── CNAME www                 → datapulse.tech
│   ├── CNAME api                 → datapulse.tech
│   └── CNAME n8n                 → datapulse.tech
└── Configures Traefik routing:
    ├── datapulse.tech        → Next.js :3000
    ├── api.datapulse.tech    → FastAPI :8000
    └── n8n.datapulse.tech    → n8n :5678
```

#### 1.4 Doppler Secrets

```
User:
├── Activates Doppler (Student Pack)
└── Creates Service Token

Claude:
├── Creates project "datapulse"
├── Creates environments: dev / staging / prod
├── Migrates all .env variables to Doppler
├── Updates docker-compose to use Doppler
└── Removes .env from production
```

**Exit Criteria**:
- [ ] Droplet running with Docker
- [ ] RDS PostgreSQL accessible
- [ ] S3 bucket created
- [ ] Domain resolving to Droplet
- [ ] SSL certificate active
- [ ] All secrets in Doppler

---

### PHASE 2: Auth Migration — Keycloak → Auth0 (Days 7-10)

> **Goal**: Replace Keycloak with Auth0, save 512MB RAM

#### Files Changed

| File | Change | Risk |
|------|--------|------|
| `docker-compose.yml` | Remove keycloak service | 🟢 Low |
| `src/datapulse/api/jwt.py` | JWKS URL → Auth0 | 🟡 Medium |
| `frontend/.env` | Auth URLs → Auth0 | 🟢 Low |
| `frontend/src/lib/auth.ts` | KeycloakProvider → Auth0Provider | 🟡 Medium |
| `android/.../AuthManager.kt` | Keycloak endpoints → Auth0 | 🟡 Medium |
| `android/.../NetworkModule.kt` | Auth URL update | 🟢 Low |

#### Auth0 Setup

```
User:
├── Creates Auth0 account (Student Pack or free tier)
├── Creates Application (Regular Web App)
├── Creates API (datapulse-api)
├── Creates 2 roles: admin, viewer
├── Creates 30 test users
└── Gives Client ID + Secret to Claude

Claude:
├── Updates jwt.py (JWKS URL + audience)
├── Updates NextAuth provider
├── Updates Android AuthManager
├── Removes Keycloak from docker-compose
├── Tests full auth flow (web + Android)
└── Runs E2E auth tests
```

#### RAM Savings

```
Before (with Keycloak):          After (with Auth0):
──────────────────────           ─────────────────────
FastAPI:     512MB               FastAPI:     512MB
Next.js:     512MB               Next.js:     512MB
PostgreSQL:  2GB → RDS           n8n:         512MB
Keycloak:    512MB ← REMOVED     Redis:       64MB
n8n:         512MB               Celery:      512MB
Redis:       64MB                Traefik:     64MB
Celery:      512MB               Lightdash:   1GB
Traefik:     64MB                pgAdmin:     256MB
Lightdash:   1GB                 Datadog:     256MB
pgAdmin:     256MB               ──────────────────
Datadog:     256MB               Total: ~3.2GB
──────────────────
Total: ~5.7GB                    Saved: 2.5GB (PostgreSQL + Keycloak)
                                 Free RAM: ~800MB buffer ✅
```

**Exit Criteria**:
- [ ] Auth0 application configured
- [ ] Web login/logout works
- [ ] Android login/logout works
- [ ] JWT validation works
- [ ] Role-based access works
- [ ] Keycloak container removed
- [ ] All auth E2E tests pass

---

### PHASE 3: Monitoring Stack (Days 10-14)

> **Goal**: Full observability before users arrive

#### 3.1 Datadog (Pro, 2 years FREE)

```
User:
├── Activates Datadog (Student Pack)
└── Copies API Key + App Key

Claude:
├── Adds datadog-agent container to docker-compose
├── Adds dd-trace SDK to FastAPI
├── Configures APM tracing (request → DB query)
├── Creates dashboards:
│   ├── API Performance (latency, error rate, throughput)
│   ├── PostgreSQL Metrics (connections, query time)
│   ├── Container Resources (CPU, RAM per service)
│   └── Business Metrics (active users, pipeline runs)
├── Creates alerts:
│   ├── API error rate > 5%
│   ├── Response time > 2s
│   ├── Container restart
│   └── Disk usage > 80%
└── Tests all monitors
```

#### 3.2 Sentry (1 year FREE)

```
User:
├── Activates Sentry (Student Pack)
└── Copies DSN

Claude:
├── Adds sentry-sdk[fastapi] to Python deps
├── Adds @sentry/nextjs to frontend
├── Configures:
│   ├── Environment tags (staging/production)
│   ├── Release tracking (git SHA)
│   ├── User context (from JWT claims)
│   ├── Performance monitoring (10% sample)
│   └── Session replay (for debugging)
├── Creates alert rules:
│   ├── New error → Slack notification
│   ├── Error spike → Email
│   └── Unhandled exception → Urgent
└── Tests with intentional error
```

#### 3.3 Codecov + Honeybadger

```
Claude:
├── Codecov:
│   ├── Adds upload step to ci.yml
│   ├── Adds codecov.yml config (80% target)
│   └── PR comments with coverage diff
│
└── Honeybadger:
    ├── Creates uptime check: https://datapulse.tech/health
    ├── Check interval: 1 minute
    ├── Alert: email + Slack
    └── SSL expiry monitoring
```

#### Monitoring Architecture

```
┌──────────────────────────────────────────────────────────┐
│                 Monitoring Stack                          │
│                                                          │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐       │
│  │ Datadog  │    │  Sentry  │    │ Honeybadger  │       │
│  │          │    │          │    │              │       │
│  │ Metrics  │    │  Errors  │    │   Uptime     │       │
│  │ APM      │    │  Stack   │    │   SSL        │       │
│  │ Logs     │    │  traces  │    │   Alerts     │       │
│  │ Infra    │    │  Context │    │              │       │
│  └────┬─────┘    └────┬─────┘    └──────┬───────┘       │
│       │               │                 │               │
│       └───────────────┼─────────────────┘               │
│                       │                                  │
│              ┌────────┴────────┐                        │
│              │  Slack Channel  │                        │
│              │  #datapulse-ops │                        │
│              └─────────────────┘                        │
│                                                          │
│  Datadog:     "API latency 2.3s on /analytics/summary"  │
│  Sentry:      "DatabaseError at repository.py:47"       │
│  Honeybadger: "datapulse.tech is DOWN"                  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Exit Criteria**:
- [ ] Datadog dashboard live
- [ ] Sentry catching errors
- [ ] Codecov reporting on PRs
- [ ] Honeybadger uptime check active
- [ ] Slack notifications working

---

### PHASE 4: Android Release (Days 14-18)

> **Goal**: Release APK to 30 beta testers

| # | Task | Agent | Details |
|---|------|-------|---------|
| 4.1 | Update `build.gradle.kts` | code-reviewer | Release API URL → `api.datapulse.tech` |
| 4.2 | Update AuthManager | security-reviewer | Auth0 endpoints + client ID |
| 4.3 | Update NetworkModule | code-reviewer | Production Ktor client config |
| 4.4 | Test all 9 screens | e2e-runner | Login → Dashboard → All pages → Pipeline |
| 4.5 | Fix edge cases | tdd-guide | Error states, offline, timeout |
| 4.6 | Generate signed APK | build-error-resolver | Release keystore + ProGuard |
| 4.7 | Firebase App Distribution | — | Upload APK, invite 30 testers |
| 4.8 | Add Firebase Crashlytics | code-reviewer | Runtime crash reporting |

#### Android Production Config

```kotlin
// build.gradle.kts - release buildType
release {
    buildConfigField("String", "API_BASE_URL",
        "\"https://api.datapulse.tech\"")
    buildConfigField("String", "AUTH_DISCOVERY_URL",
        "\"https://YOUR_DOMAIN.auth0.com/.well-known/openid-configuration\"")
    buildConfigField("String", "AUTH_CLIENT_ID",
        "\"YOUR_AUTH0_CLIENT_ID\"")
    isMinifyEnabled = true
    proguardFiles(...)
    signingConfig = signingConfigs.getByName("release")
}
```

**Exit Criteria**:
- [ ] Signed APK builds
- [ ] All 9 screens work with production API
- [ ] Auth0 login works on Android
- [ ] Crashlytics sending reports
- [ ] 30 testers invited via Firebase

---

### PHASE 5: Beta Launch (Days 18-28)

> **Goal**: 30 users testing, feedback collected, issues fixed

#### Launch Checklist

```
Day 18 — Launch Day:
├── ✅ Web: datapulse.tech live
├── ✅ Android: APK distributed
├── ✅ 30 users have accounts (Auth0)
├── ✅ Monitoring active (Datadog + Sentry)
├── ✅ Uptime monitoring (Honeybadger)
└── ✅ Feedback form ready (Google Forms / Notion)

Day 19-25 — Observation:
├── 📊 Monitor Datadog dashboards daily
├── 🚨 Fix Sentry errors within 24 hours
├── 📝 Collect user feedback
├── 🔄 Deploy fixes via CI/CD
└── 📱 Push Android updates via Firebase

Day 25-28 — Review:
├── 📊 Analyze usage patterns
├── 📝 Compile feedback report
├── 🎯 Prioritize improvements
├── 📋 Plan next release
└── 🐺 Wild Wolf Beta: COMPLETE ✅
```

#### Success Metrics

| Metric | Target | Measured By |
|--------|--------|-------------|
| Uptime | > 99% | Honeybadger |
| API Response Time | < 500ms (p95) | Datadog APM |
| Error Rate | < 1% | Sentry |
| Crash-Free Sessions | > 99% (Android) | Firebase Crashlytics |
| Active Users | 20+ of 30 | Datadog / Auth0 |
| Feedback Responses | 15+ | Google Forms |
| Critical Bugs | 0 unresolved | Sentry |

---

## 💰 Complete Budget

### Monthly Cost Breakdown

| Service | Provider | Cost | Notes |
|---------|----------|------|-------|
| Droplet (4GB) | DigitalOcean | $24/mo | From $200 credit |
| Backups | DigitalOcean | $4.80/mo | Optional but recommended |
| RDS PostgreSQL | AWS | ~$15/mo | db.t3.micro |
| S3 Storage | AWS | ~$1/mo | Minimal for beta |
| Data Transfer | AWS | ~$2/mo | Estimated |
| SES Email | AWS | ~$0.10/mo | Minimal |
| Datadog | Student Pack | $0 | 2 years FREE |
| Sentry | Student Pack | $0 | 1 year FREE |
| Auth0 | Free Tier | $0 | 7,500 users |
| Doppler | Student Pack | $0 | Student duration |
| Codecov | Free | $0 | Forever |
| Honeybadger | Free Tier | $0 | Free tier |
| Domain | Student Pack | $0 | 1 year FREE |
| **TOTAL** | | **~$47/mo** | **From credits = $0** |

### Runway

```
DigitalOcean: $200 ÷ $29/mo ≈ 7 months
AWS:          $200 ÷ $18/mo ≈ 11 months
─────────────────────────────────────────
Effective runway: ~8 months at $0 cost
After credits: ~$47/month
```

---

## 🔧 Agent Dispatch Plan

### Phase 0 Agents

| Agent | Model | Task | Run Mode |
|-------|-------|------|----------|
| tdd-guide | sonnet | Run full test suite | Foreground |
| e2e-runner | sonnet | Run Playwright tests | Foreground |
| security-reviewer | opus | Full security scan | Foreground |
| build-error-resolver | sonnet | Fix any build issues | Foreground |

### Phase 1 Agents

| Agent | Model | Task | Run Mode |
|-------|-------|------|----------|
| docker-specialist | sonnet | Production docker-compose | Foreground |
| migration-specialist | sonnet | Data migration to RDS | Foreground |
| security-reviewer | sonnet | Verify secrets management | Background |

### Phase 2 Agents

| Agent | Model | Task | Run Mode |
|-------|-------|------|----------|
| architect | opus | Auth migration design | Foreground |
| security-reviewer | opus | Auth security verification | Foreground |
| code-reviewer | sonnet | Review auth changes | Background |
| e2e-runner | sonnet | Auth flow E2E tests | Foreground |

### Phase 3 Agents

| Agent | Model | Task | Run Mode |
|-------|-------|------|----------|
| docker-specialist | sonnet | Datadog container setup | Foreground |
| code-reviewer | sonnet | SDK integration review | Background |
| python-reviewer | sonnet | Sentry SDK review | Background |
| typescript-reviewer | sonnet | Next.js Sentry review | Background |

### Phase 4 Agents

| Agent | Model | Task | Run Mode |
|-------|-------|------|----------|
| code-reviewer | sonnet | Android config review | Foreground |
| security-reviewer | sonnet | Android security check | Background |
| build-error-resolver | sonnet | APK build issues | Foreground |

---

## 📊 Risk Matrix

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Auth0 migration breaks auth flow | 🔴 High | 🟡 Medium | Full E2E tests before/after |
| Droplet RAM insufficient | 🟡 Medium | 🟢 Low | Removed Keycloak + Jupyter = 2.5GB saved |
| RDS connection from Droplet slow | 🟡 Medium | 🟢 Low | Same region deployment |
| Android API compatibility | 🟡 Medium | 🟡 Medium | Test all 9 screens manually |
| Student Pack tools expire | 🟢 Low | 🟢 Low | 1-2 year runway |
| 30 users find critical bug | 🟡 Medium | 🟡 Medium | Sentry + quick fix cycle |
| Data loss during migration | 🔴 High | 🟢 Low | Full backup before migration |
| SSL certificate issues | 🟡 Medium | 🟢 Low | Traefik + Let's Encrypt auto |

---

## 🗓️ Timeline

```
Week 1          Week 2          Week 3          Week 4
─────────────   ─────────────   ─────────────   ─────────────
Phase 0         Phase 1 (cont)  Phase 3         Phase 5
Pre-flight      Infra setup     Monitoring      Beta Launch
Tests + Audit   DigitalOcean    Datadog         30 Users
                AWS RDS/S3      Sentry          Monitor
Phase 1         Phase 2         Codecov         Feedback
Infra start     Auth Migration  Honeybadger     Iterate
Domain          Keycloak→Auth0
Doppler         Phase 4
                Android Release
                Firebase Dist.
```

---

## ✅ Go/No-Go Checklist (Before Launch)

| # | Check | Required? |
|---|-------|-----------|
| 1 | All pytest tests pass | ✅ Must |
| 2 | All E2E tests pass | ✅ Must |
| 3 | Android APK builds and works | ✅ Must |
| 4 | Auth0 login works (web + Android) | ✅ Must |
| 5 | Production API responds < 500ms | ✅ Must |
| 6 | SSL certificate valid | ✅ Must |
| 7 | Datadog dashboard showing metrics | ✅ Must |
| 8 | Sentry catching test errors | ✅ Must |
| 9 | Honeybadger uptime active | ✅ Must |
| 10 | 30 user accounts created in Auth0 | ✅ Must |
| 11 | Feedback form ready | ✅ Must |
| 12 | Slack alerts configured | 🟡 Nice |
| 13 | Codecov on PRs | 🟡 Nice |
| 14 | Firebase Crashlytics active | 🟡 Nice |
| 15 | Backup strategy documented | ✅ Must |

---

*🐺 The Wild Wolf doesn't wait. It hunts.*

*Plan generated: 2026-04-01*
*Agent: Claude Opus 4.6*
