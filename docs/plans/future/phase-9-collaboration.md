# Phase 9 — Collaboration & Teams

> **Status**: PLANNED
> **Priority**: NICE-TO-HAVE
> **Dependencies**: Phase 5 (Multi-tenancy), Phase 7 (Self-Service Analytics — need dashboards to share)
> **Goal**: Enable team collaboration through comments, shared dashboards, team workspaces, and activity feeds.

---

## Why This Matters

Analytics is a team sport. A dashboard only becomes valuable when:
- The CEO can share a view with the sales director
- A sales manager can annotate a spike and explain it to the team
- Everyone sees what changed and who changed it

**Collaboration = Stickiness** — teams that collaborate inside your tool don't switch to competitors.

---

## Visual Overview

```
Phase 9 — Collaboration & Teams
═══════════════════════════════════════════════════════════════

  9.1 Comments & Annotations     Comment on charts, tag teammates
       │
       v
  9.2 Dashboard Sharing          Share links, embed, access control
       │
       v
  9.3 Team Workspaces            Groups within a tenant, shared views
       │
       v
  9.4 Activity Feed              Who did what, when, audit trail

═══════════════════════════════════════════════════════════════
```

---

## Sub-Phases

### 9.1 Comments & Annotations

**Goal**: Users can comment on specific data points, charts, or dashboards.

**Features**:
- Comment on any chart or KPI card
- @mention teammates (autocomplete from tenant members)
- Thread replies
- Pin important comments
- Attach comments to specific date ranges or data points

**Implementation**:
- `src/datapulse/collaboration/` module:
  - `models.py` — `Comment`, `CommentCreate`, `Mention`
  - `repository.py` — CRUD for `comments` table
  - `notifications.py` — Notify mentioned users (in-app + email)
- API:
  - `POST /api/v1/comments` — Create comment
  - `GET /api/v1/comments?target_type=dashboard&target_id=...` — List comments
  - `POST /api/v1/comments/{id}/reply` — Reply to thread
  - `DELETE /api/v1/comments/{id}` — Delete own comment

**Database**:
```sql
CREATE TABLE public.comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    user_name VARCHAR(200) NOT NULL,
    target_type VARCHAR(50) NOT NULL,    -- 'dashboard', 'widget', 'kpi', 'alert'
    target_id VARCHAR(200) NOT NULL,
    parent_id UUID REFERENCES public.comments(id),  -- Thread support
    body TEXT NOT NULL,
    mentions UUID[] DEFAULT '{}',
    is_pinned BOOLEAN DEFAULT false,
    context JSONB DEFAULT '{}',          -- {date_range, filters, data_point}
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.comments ENABLE ROW LEVEL SECURITY;
```

**Frontend**:
- Comment icon on each chart/widget (with unread badge)
- Slide-out comment panel
- @mention autocomplete
- Thread view

**Tests**: ~15 tests

---

### 9.2 Dashboard Sharing

**Goal**: Share dashboards with teammates, external stakeholders, or as public links.

**Sharing Modes**:
| Mode | Access | Use Case |
|------|--------|----------|
| Tenant member | Full (respects role) | Internal team |
| Public link | Read-only, no auth | Board presentations |
| Embed | iframe, read-only | External portals |
| Password-protected | Read-only + password | Client sharing |

**Implementation**:
- `src/datapulse/collaboration/sharing.py`:
  - `create_share_link(dashboard_id, mode, expires_at, password)` → `ShareLink`
  - Public links: unique token, optional expiry, optional password
  - Embed: generate `<iframe>` snippet with token-based auth
- API:
  - `POST /api/v1/dashboards/{id}/share` — Create share link
  - `GET /api/v1/dashboards/{id}/shares` — List active shares
  - `DELETE /api/v1/shares/{token}` — Revoke share
  - `GET /api/v1/shared/{token}` — Access shared dashboard (public route)
- Frontend:
  - Share button on dashboard header
  - Share modal: copy link, set expiry, toggle password
  - Shared dashboard viewer (minimal UI, no sidebar)

**Database**:
```sql
CREATE TABLE public.share_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    dashboard_id UUID NOT NULL REFERENCES public.dashboards(id),
    token VARCHAR(64) UNIQUE NOT NULL,
    mode VARCHAR(20) NOT NULL DEFAULT 'public',
    password_hash VARCHAR(200),
    expires_at TIMESTAMPTZ,
    view_count INT DEFAULT 0,
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

**Tests**: ~15 tests

---

### 9.3 Team Workspaces

**Goal**: Organize users into teams within a tenant, with shared resources.

**Features**:
- Create teams (e.g., "Sales Cairo", "Management", "Operations")
- Assign dashboards, views, and alerts to teams
- Team-level permissions (view/edit)
- Default team for new members

**Implementation**:
- `src/datapulse/collaboration/teams.py`:
  - `TeamCreate`, `TeamResponse`, `TeamMember`
  - CRUD for teams + team membership
  - Resource assignment (dashboard → team)
- API:
  - `CRUD /api/v1/teams` — Manage teams
  - `POST /api/v1/teams/{id}/members` — Add member
  - `POST /api/v1/teams/{id}/dashboards` — Assign dashboard

**Database**:
```sql
CREATE TABLE public.teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE public.team_members (
    team_id UUID NOT NULL REFERENCES public.teams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    role VARCHAR(20) DEFAULT 'member',  -- lead, member
    PRIMARY KEY (team_id, user_id)
);

CREATE TABLE public.team_resources (
    team_id UUID NOT NULL REFERENCES public.teams(id) ON DELETE CASCADE,
    resource_type VARCHAR(50) NOT NULL,  -- 'dashboard', 'view', 'alert_rule'
    resource_id UUID NOT NULL,
    permission VARCHAR(20) DEFAULT 'view',
    PRIMARY KEY (team_id, resource_type, resource_id)
);
```

**Tests**: ~10 tests

---

### 9.4 Activity Feed

**Goal**: Full audit trail — who did what, when.

**Tracked Events**:
| Event | Example |
|-------|---------|
| Data import | "Ahmed imported 50K rows from sales_q1.xlsx" |
| Dashboard created | "Sara created dashboard 'Weekly Sales'" |
| Alert triggered | "Returns exceeded 5% threshold" |
| Share link created | "Mohamed shared 'Executive Dashboard' as public link" |
| Pipeline run | "Auto pipeline completed: 45K rows processed" |
| Settings changed | "Ahmed changed plan from Starter to Pro" |
| Member invited | "Sara invited omar@company.com as viewer" |

**Implementation**:
- `src/datapulse/collaboration/activity.py`:
  - `log_activity(tenant_id, user_id, event_type, details)` — Fire-and-forget logging
  - Event types enum with structured details
  - Async write (don't block the main request)
- API:
  - `GET /api/v1/activity` — Paginated activity feed
  - `GET /api/v1/activity?user_id=...` — Filter by user
  - `GET /api/v1/activity?type=...` — Filter by event type
- Frontend:
  - Activity feed page (`/activity`)
  - Activity widget for dashboard sidebar
  - User avatar + relative timestamp
  - Filter by event type and user

**Database**:
```sql
CREATE TABLE public.activity_log (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID,
    user_name VARCHAR(200),
    event_type VARCHAR(50) NOT NULL,
    target_type VARCHAR(50),
    target_id VARCHAR(200),
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_activity_tenant_time ON public.activity_log(tenant_id, created_at DESC);
ALTER TABLE public.activity_log ENABLE ROW LEVEL SECURITY;
```

**Tests**: ~10 tests

---

## API Endpoints Summary

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/comments` | Create comment |
| GET | `/api/v1/comments` | List comments for target |
| POST | `/api/v1/comments/{id}/reply` | Reply in thread |
| DELETE | `/api/v1/comments/{id}` | Delete comment |
| POST | `/api/v1/dashboards/{id}/share` | Create share link |
| GET | `/api/v1/shared/{token}` | Access shared dashboard |
| DELETE | `/api/v1/shares/{token}` | Revoke share |
| CRUD | `/api/v1/teams` | Team management |
| POST | `/api/v1/teams/{id}/members` | Add team member |
| GET | `/api/v1/activity` | Activity feed |

---

## Frontend Pages

```
frontend/src/app/(app)/
├── activity/
│   └── page.tsx           # Activity feed timeline
├── teams/
│   ├── page.tsx           # Teams list
│   └── [id]/
│       └── page.tsx       # Team details + members

frontend/src/app/(shared)/
└── [token]/
    └── page.tsx           # Shared dashboard viewer (no auth required)
```

---

## Acceptance Criteria

- [ ] Users can comment on any chart and @mention teammates
- [ ] Mentioned users receive in-app notification
- [ ] Public share links render dashboard without auth
- [ ] Share links can be set to expire and password-protected
- [ ] Teams can be created and dashboards assigned to them
- [ ] Activity feed shows all tracked events in chronological order
- [ ] All features respect tenant isolation
- [ ] 50+ new tests, all passing
