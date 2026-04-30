# Phase 6 — Data Sources & Connectors

> **Status**: PLANNED
> **Priority**: HIGH
> **Dependencies**: Phase 5 (Multi-tenancy — need tenant isolation for external data)
> **Goal**: Expand beyond CSV/Excel to support Google Sheets, databases, and third-party APIs as data sources.

---

## Why This Matters

DataPulse currently only accepts Excel/CSV file uploads. For a SaaS platform, customers need to:
- Connect their existing data where it lives
- Set up automated syncs (not manual uploads every time)
- Combine data from multiple sources

---

## Visual Overview

```
Phase 6 — Data Sources & Connectors
═══════════════════════════════════════════════════════════════

  6.1 Connector Framework    Abstract base, registry, auth store
       │
       v
  6.2 Google Sheets          OAuth2, sheet selection, auto-sync
       │
       v
  6.3 Database Connectors    MySQL, SQL Server, PostgreSQL (external)
       │
       v
  6.4 API Connectors         Shopify, WooCommerce, generic REST
       │
       v
  6.5 Schema Mapping UI      Map source columns → DataPulse schema
       │
       v
  6.6 Sync Scheduler         Cron-based auto-sync, change detection

═══════════════════════════════════════════════════════════════
```

---

## Sub-Phases

### 6.1 Connector Framework

**Goal**: Build an extensible connector architecture.

**Design**:
```python
# src/datapulse/connectors/base.py
class BaseConnector(ABC):
    """All connectors implement this interface."""

    @abstractmethod
    async def test_connection(self) -> bool: ...

    @abstractmethod
    async def list_tables(self) -> list[TableInfo]: ...

    @abstractmethod
    async def fetch_schema(self, table: str) -> list[ColumnInfo]: ...

    @abstractmethod
    async def extract(self, table: str, since: datetime | None) -> pl.DataFrame: ...

    @abstractmethod
    def connector_type(self) -> str: ...
```

**Components**:
- `src/datapulse/connectors/` module:
  - `base.py` — Abstract `BaseConnector` class
  - `registry.py` — Connector type registry (factory pattern)
  - `models.py` — `ConnectionCreate`, `ConnectionResponse`, `ConnectionTest`, `SyncConfig`
  - `repository.py` — CRUD for `connections` table
  - `service.py` — Connection lifecycle + sync orchestration
- Migration: `011_create_connections.sql`

```sql
CREATE TABLE public.connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES bronze.tenants(tenant_id),
    name VARCHAR(200) NOT NULL,
    connector_type VARCHAR(50) NOT NULL,  -- 'google_sheets', 'mysql', 'shopify', etc.
    config JSONB NOT NULL DEFAULT '{}',   -- Connection params (encrypted at rest)
    credentials JSONB,                     -- Encrypted credentials
    status VARCHAR(20) DEFAULT 'active',
    last_sync_at TIMESTAMPTZ,
    sync_schedule VARCHAR(50),            -- Cron expression
    created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.connections ENABLE ROW LEVEL SECURITY;
```

**Tests**: ~15 tests

---

### 6.2 Google Sheets Connector

**Goal**: Connect to Google Sheets with OAuth2.

**Flow**:
1. User clicks "Connect Google Sheets"
2. OAuth2 consent flow (Google API)
3. User picks spreadsheet + sheet tab
4. DataPulse reads data → Polars DataFrame → Bronze layer
5. Optional: auto-sync on schedule

**Implementation**:
- `src/datapulse/connectors/google_sheets.py`:
  - OAuth2 token management (refresh tokens stored encrypted)
  - `gspread` or Google Sheets API v4 direct
  - Sheet → Polars DataFrame conversion
  - Change detection (sheet `modifiedTime`)
- Frontend: OAuth popup, sheet picker, column preview

**Tests**: ~15 tests (mock Google API)

---

### 6.3 Database Connectors

**Goal**: Read data from external MySQL, SQL Server, PostgreSQL databases.

**Supported Databases**:
| Database | Driver | Notes |
|----------|--------|-------|
| MySQL | `asyncmy` / `pymysql` | Most common SMB database |
| SQL Server | `pyodbc` / `pymssql` | Enterprise customers |
| PostgreSQL | `asyncpg` | Dev/analytics teams |

**Implementation**:
- `src/datapulse/connectors/database.py`:
  - Connection via SQLAlchemy with dynamic `create_engine`
  - Table listing, schema introspection
  - Chunked extraction (batch reads for large tables)
  - SSH tunnel support (for databases behind firewalls)
- Security:
  - Credentials encrypted at rest (Fernet or AWS KMS)
  - Connection timeout limits
  - Read-only connections enforced (SET TRANSACTION READ ONLY)
  - SQL injection prevention (no user-provided queries, only table selection)

**Tests**: ~20 tests (mock database connections)

---

### 6.4 API Connectors

**Goal**: Pull data from e-commerce and CRM APIs.

**Initial Connectors**:
| Source | API | Data |
|--------|-----|------|
| Shopify | REST Admin API | Orders, products, customers |
| WooCommerce | REST API v3 | Orders, products, customers |
| Generic REST | User-configured | Any JSON API |

**Implementation**:
- `src/datapulse/connectors/shopify.py` — Shopify-specific connector
- `src/datapulse/connectors/woocommerce.py` — WooCommerce connector
- `src/datapulse/connectors/rest_api.py` — Generic configurable REST connector
- Pagination handling (cursor, offset, link-header)
- Rate limit respect (backoff + retry)
- Response → Polars DataFrame mapping

**Tests**: ~15 tests (mock HTTP responses)

---

### 6.5 Schema Mapping UI

**Goal**: Let users map source columns to the DataPulse schema.

**Frontend**:
- Column mapping interface:
  - Left: source columns with detected types
  - Right: DataPulse target columns
  - Auto-suggest mappings based on name similarity
  - Manual override with drag-and-drop
- Data preview: show first 10 rows with mapping applied
- Save mapping as template for reuse

**Backend**:
- `src/datapulse/connectors/mapper.py` — Column mapping logic
- `src/datapulse/connectors/auto_map.py` — Fuzzy matching for auto-suggestions
- Store mapping config in `connections.config` JSONB

**Tests**: ~10 tests

---

### 6.6 Sync Scheduler

**Goal**: Automated periodic data syncing.

**Implementation**:
- Cron-based scheduling via existing n8n infrastructure
- Sync modes:
  - **Full refresh**: Replace all data from source
  - **Incremental**: Only new/changed rows (using timestamp or ID cursor)
- `src/datapulse/connectors/scheduler.py`:
  - Create/update n8n workflow per connection
  - Track sync history (success/failure, rows synced, duration)
- API routes:
  - `POST /api/v1/connections/{id}/sync` — Manual sync trigger
  - `GET /api/v1/connections/{id}/sync-history` — Sync run history

**Frontend**:
- Sync status indicators on connections list
- Sync history table with row counts and durations
- Manual "Sync Now" button

**Tests**: ~10 tests

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/connections` | List tenant connections |
| POST | `/api/v1/connections` | Create new connection |
| GET | `/api/v1/connections/{id}` | Get connection details |
| PATCH | `/api/v1/connections/{id}` | Update connection config |
| DELETE | `/api/v1/connections/{id}` | Remove connection |
| POST | `/api/v1/connections/{id}/test` | Test connection |
| POST | `/api/v1/connections/{id}/sync` | Trigger manual sync |
| GET | `/api/v1/connections/{id}/schema` | Get source schema |
| GET | `/api/v1/connections/{id}/preview` | Preview source data |
| GET | `/api/v1/connections/{id}/sync-history` | Sync run history |

---

## Frontend Pages

```
frontend/src/app/(app)/connections/
├── page.tsx               # Connections list with status
├── new/
│   └── page.tsx           # New connection wizard (type → config → mapping → test)
└── [id]/
    ├── page.tsx           # Connection details + sync history
    └── mapping/
        └── page.tsx       # Column mapping editor
```

---

## Acceptance Criteria

- [ ] Google Sheets: OAuth flow, sheet selection, data import in < 3 minutes
- [ ] MySQL/SQL Server: connection test, table selection, schema preview
- [ ] Shopify: API key setup, orders import with pagination
- [ ] Column mapping: auto-suggest works for 80%+ of common column names
- [ ] Scheduled sync: runs on cron, handles failures with retry
- [ ] All credentials encrypted at rest
- [ ] Tenant isolation: connections visible only to owning tenant
- [ ] 80+ new tests, all passing
