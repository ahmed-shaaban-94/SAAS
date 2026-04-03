# Phase 10 — Scale & Infrastructure

> **Status**: PLANNED
> **Priority**: WHEN NEEDED (triggered by growth)
> **Dependencies**: Phase 5 (Multi-tenancy)
> **Goal**: Prepare DataPulse for production scale — container orchestration, object storage, background jobs, CDN, and observability.

---

## When to Start This Phase

**Triggers** (any one of these):
- 50+ active tenants
- 10M+ total rows across all tenants
- API p95 latency > 2 seconds
- Single-server Docker Compose becomes a bottleneck
- First enterprise customer with SLA requirements

**Don't over-engineer early** — Docker Compose works fine for the first 10-50 tenants.

---

## Visual Overview

```
Phase 10 — Scale & Infrastructure
═══════════════════════════════════════════════════════════════

  10.1 Object Storage (MinIO/S3)     File storage off local disk
        │
        v
  10.2 Background Jobs (Celery)      Async task processing
        │
        v
  10.3 Caching (Redis expansion)     Query cache, session cache
        │
        v
  10.4 Kubernetes Deployment         Container orchestration
        │
        v
  10.5 CDN & Static Assets           Edge caching for frontend
        │
        v
  10.6 Monitoring & Observability    Prometheus, Grafana, alerting

═══════════════════════════════════════════════════════════════
```

---

## Sub-Phases

### 10.1 Object Storage (MinIO / S3)

**Goal**: Move file storage from local Docker volumes to S3-compatible object storage.

**What Moves to Object Storage**:
| Content | Current Location | New Location |
|---------|-----------------|-------------|
| Raw Excel/CSV uploads | `/app/data/raw/sales` volume | `s3://datapulse-{tenant}/raw/` |
| Parquet files | `/app/data/parquet` volume | `s3://datapulse-{tenant}/parquet/` |
| Generated PDFs | Generated on-the-fly | `s3://datapulse-{tenant}/reports/` |
| Export files | Generated on-the-fly | `s3://datapulse-{tenant}/exports/` (TTL: 24h) |

**Implementation**:
- `src/datapulse/storage/` module:
  - `client.py` — S3 client wrapper (`boto3` or `aiobotocore`)
  - `models.py` — `StorageFile`, `UploadResult`
  - Presigned URLs for secure client-side upload/download
- Docker: MinIO service for dev, S3 for production
- Migration path: script to move existing local files to S3

**Config**:
```python
# config.py additions
STORAGE_BACKEND: str = "local"  # "local" | "s3" | "minio"
S3_BUCKET: str = "datapulse"
S3_ENDPOINT: str | None = None  # For MinIO
S3_REGION: str = "eu-west-1"
```

---

### 10.2 Background Jobs (Celery + Redis)

**Goal**: Offload heavy tasks from API request/response cycle.

**Tasks to Backgroundize**:
| Task | Current | Backgrounded |
|------|---------|-------------|
| Bronze loading | Synchronous in executor | Celery task |
| dbt runs | Synchronous subprocess | Celery task |
| PDF report generation | N/A | Celery task |
| Data export (large) | N/A | Celery task + presigned download |
| Forecast computation | N/A | Celery task |
| AI query execution | N/A | Celery task (with timeout) |
| Baseline recalculation | N/A | Celery periodic task |

**Implementation**:
- `src/datapulse/tasks/` module:
  - `celery_app.py` — Celery app configuration
  - `pipeline_tasks.py` — Bronze, dbt, quality tasks
  - `export_tasks.py` — CSV, Excel, PDF generation
  - `ai_tasks.py` — Forecast, NL query, summary generation
- Redis: expand existing Redis service as Celery broker + result backend
- Flower: Celery monitoring dashboard (dev only)
- API pattern:
  ```
  POST /api/v1/exports → 202 Accepted, {task_id}
  GET  /api/v1/tasks/{task_id} → {status, result_url}
  ```

**Docker**:
```yaml
celery-worker:
  build: .
  command: celery -A datapulse.tasks.celery_app worker -l info
  depends_on: [redis, postgres]

celery-beat:
  build: .
  command: celery -A datapulse.tasks.celery_app beat -l info
  depends_on: [redis]
```

---

### 10.3 Caching Strategy (Redis Expansion)

**Goal**: Reduce database load and API latency with strategic caching.

**Cache Layers**:
| Layer | TTL | Key Pattern | Content |
|-------|-----|-------------|---------|
| API response | 5 min | `cache:{tenant}:{endpoint}:{params_hash}` | JSON response |
| Query result | 15 min | `query:{tenant}:{sql_hash}` | DataFrame serialized |
| Tenant config | 1 hour | `tenant:{id}:config` | Plan, limits, settings |
| Usage counters | Real-time | `usage:{tenant}:{metric}:{date}` | Counter values |
| Session | 30 min | `session:{user_id}` | JWT claims cache |

**Implementation**:
- `src/datapulse/cache/` module:
  - `client.py` — Redis cache wrapper with serialization
  - `decorators.py` — `@cached(ttl=300)` decorator for service methods
  - `invalidation.py` — Cache invalidation on data changes
- Cache-aside pattern: check cache → miss → query DB → store in cache
- Automatic invalidation on pipeline run completion

---

### 10.4 Kubernetes Deployment

**Goal**: Move from Docker Compose to Kubernetes for horizontal scaling.

**Architecture**:
```
                    ┌─────────────────────┐
                    │   Ingress (nginx)   │
                    └──────┬──────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼──┐   ┌────▼───┐   ┌───▼────┐
        │Frontend│   │  API   │   │  n8n   │
        │ (2-4)  │   │ (2-8)  │   │  (1)   │
        └────────┘   └────┬───┘   └────────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
        ┌─────▼──┐  ┌────▼───┐  ┌───▼────┐
        │Postgres│  │ Redis  │  │ MinIO  │
        │  (HA)  │  │ (HA)   │  │  (HA)  │
        └────────┘  └────────┘  └────────┘
```

**Deliverables**:
- `k8s/` directory with Helm chart or Kustomize manifests
- Deployments: frontend, API, celery-worker, celery-beat, n8n
- StatefulSets: PostgreSQL (or managed RDS), Redis (or ElastiCache)
- HPA (Horizontal Pod Autoscaler) on API and frontend
- ConfigMaps and Secrets for environment config
- Health checks: liveness + readiness probes (existing `/health` endpoint)
- PersistentVolumeClaims for stateful services

**Migration Path**:
1. Start with managed K8s (EKS, GKE, or DigitalOcean K8s)
2. Use managed database (RDS/Cloud SQL) instead of self-hosted PG
3. Use managed Redis (ElastiCache/Memorystore)
4. GitOps with ArgoCD or Flux

---

### 10.5 CDN & Static Assets

**Goal**: Serve frontend assets from edge locations for global performance.

**Implementation**:
- CloudFront / Cloudflare in front of Next.js
- Static asset caching headers (`Cache-Control: public, max-age=31536000, immutable`)
- Next.js `output: 'standalone'` for container deployment
- Image optimization via Next.js Image component (if images are added later)

---

### 10.6 Monitoring & Observability

**Goal**: Full visibility into system health, performance, and errors.

**Stack**:
| Tool | Purpose |
|------|---------|
| Prometheus | Metrics collection |
| Grafana | Dashboards + alerting |
| Loki | Log aggregation |
| Jaeger / Tempo | Distributed tracing |
| Sentry | Error tracking (frontend + backend) |

**Key Metrics to Monitor**:
| Metric | Alert Threshold |
|--------|----------------|
| API p95 latency | > 2s |
| API error rate | > 1% |
| Database connection pool | > 80% utilized |
| Redis memory | > 80% |
| Celery queue depth | > 100 pending tasks |
| Pipeline failure rate | > 10% |
| Disk usage | > 85% |

**Implementation**:
- `src/datapulse/monitoring/` module:
  - `metrics.py` — Prometheus metrics (counters, histograms, gauges)
  - `middleware.py` — Request duration, status code metrics
- Grafana dashboards:
  1. System Overview (API latency, error rate, throughput)
  2. Database Performance (query duration, connections, locks)
  3. Pipeline Health (runs, failures, quality scores)
  4. Tenant Usage (rows, API calls, storage per tenant)
  5. Business Metrics (active tenants, MRR, churn)

**Docker (dev)**:
```yaml
prometheus:
  image: prom/prometheus
  ports: ["9090:9090"]
  volumes:
    - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

grafana:
  image: grafana/grafana
  ports: ["3001:3000"]
  volumes:
    - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
```

---

## Infrastructure Comparison

| Aspect | Current (Docker Compose) | Phase 10 (Kubernetes) |
|--------|------------------------|----------------------|
| Scaling | Vertical only | Horizontal auto-scale |
| Storage | Local volumes | S3/MinIO (unlimited) |
| Jobs | Synchronous + n8n | Celery (distributed) |
| Caching | Basic Redis | Multi-layer Redis |
| Monitoring | structlog only | Prometheus + Grafana |
| Deploy | `docker compose up` | GitOps (ArgoCD) |
| Cost | $20-50/mo (single VPS) | $200-500/mo (managed K8s) |
| SLA | Best effort | 99.5-99.9% |

---

## Acceptance Criteria

- [ ] File uploads go to S3/MinIO instead of local volume
- [ ] Heavy operations (export, forecast) run as background tasks
- [ ] API p95 latency < 500ms with caching enabled
- [ ] K8s manifests deploy successfully on managed cluster
- [ ] HPA scales API from 2 to 8 pods based on CPU/memory
- [ ] Grafana dashboards show all key metrics
- [ ] Alerts fire when thresholds are breached
- [ ] Zero downtime deployment via rolling updates
- [ ] All existing tests pass in K8s environment
