# Track 5 — Observability Stack

> **Status**: PLANNED
> **Priority**: HIGH
> **Current State**: structlog JSON logging, basic health checks, Sentry DSN configured but no metrics/dashboards/tracing

---

## Objective

Deploy a full **observability stack** (Prometheus + Grafana + Loki) via Docker Compose to collect **metrics**, **logs**, and **traces** from all services — with pre-built Grafana dashboards for API performance, pipeline health, database stats, and infrastructure monitoring.

---

## Why This Matters

- "How do you monitor your services?" is asked in every backend/DevOps interview
- Prometheus + Grafana is the industry standard (used by 80%+ of companies)
- Understanding metrics, logs, and traces (the three pillars) is essential for senior roles
- Self-hosted = $0 cost, runs alongside existing Docker stack
- Demonstrates SRE mindset — not just building, but operating production systems

---

## Scope

- Prometheus server + exporters (node, postgres, redis)
- Grafana with 5 pre-built dashboards
- Loki for centralized log aggregation
- FastAPI metrics middleware (request count, latency, error rate)
- Pipeline metrics (run duration, stage timing, quality scores)
- Alerting rules (Prometheus Alertmanager → Slack)
- All running in Docker Compose alongside existing services
- $0 additional cost

---

## Deliverables

| Deliverable | Description |
|-------------|-------------|
| Prometheus | Metrics collection server + scrape configs for all services |
| Grafana | 5 pre-built dashboards (API, Pipeline, Database, Infrastructure, Quality) |
| Loki + Promtail | Centralized log aggregation from all Docker containers |
| FastAPI middleware | `prometheus_fastapi_instrumentator` for automatic HTTP metrics |
| Custom metrics | Pipeline run counters, stage timings, quality scores, cache hit rates |
| PostgreSQL exporter | `postgres_exporter` for DB connection pool, query stats, table sizes |
| Redis exporter | `redis_exporter` for memory, connections, hit rates |
| Node exporter | System metrics (CPU, memory, disk, network) |
| Alert rules | 10 Prometheus alert rules + Alertmanager → Slack |
| Docker integration | All observability services in docker-compose.yml |

---

## Technical Details

### Architecture

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   FastAPI     │  │  PostgreSQL  │  │    Redis     │  │    n8n       │
│   /metrics    │  │  :9187       │  │  :9121       │  │  (logs)      │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │                 │
       └────────────┬────┴────────┬────────┘                 │
                    │             │                           │
              ┌─────▼─────────────▼──────┐            ┌──────▼──────┐
              │      Prometheus          │            │   Promtail   │
              │      :9090               │            │  (log ship)  │
              │  scrape_interval: 15s    │            └──────┬───────┘
              └──────────┬───────────────┘                   │
                         │                            ┌──────▼──────┐
                   ┌─────▼──────┐                     │    Loki      │
                   │  Grafana   │◄────────────────────│   :3100      │
                   │  :3001     │  (log queries)      └─────────────┘
                   └─────┬──────┘
                         │
                   ┌─────▼──────────┐
                   │ Alertmanager   │──► Slack webhook
                   │ :9093          │
                   └────────────────┘
```

### Docker Compose Additions

```yaml
# Observability services added to docker-compose.yml

  prometheus:
    image: prom/prometheus:v2.51.0
    container_name: datapulse-prometheus
    ports:
      - "127.0.0.1:9090:9090"
    volumes:
      - ./observability/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./observability/prometheus/rules/:/etc/prometheus/rules/
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'
    mem_limit: 512m
    networks:
      - backend

  grafana:
    image: grafana/grafana:10.4.0
    container_name: datapulse-grafana
    ports:
      - "127.0.0.1:3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-datapulse}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - ./observability/grafana/provisioning/:/etc/grafana/provisioning/
      - ./observability/grafana/dashboards/:/var/lib/grafana/dashboards/
      - grafana_data:/var/lib/grafana
    depends_on:
      - prometheus
      - loki
    mem_limit: 256m
    networks:
      - backend

  loki:
    image: grafana/loki:2.9.6
    container_name: datapulse-loki
    ports:
      - "127.0.0.1:3100:3100"
    volumes:
      - ./observability/loki/loki-config.yml:/etc/loki/local-config.yaml
      - loki_data:/loki
    mem_limit: 256m
    networks:
      - backend

  promtail:
    image: grafana/promtail:2.9.6
    container_name: datapulse-promtail
    volumes:
      - ./observability/promtail/promtail-config.yml:/etc/promtail/config.yml
      - /var/run/docker.sock:/var/run/docker.sock:ro
    depends_on:
      - loki
    mem_limit: 128m
    networks:
      - backend

  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:v0.15.0
    container_name: datapulse-postgres-exporter
    environment:
      DATA_SOURCE_NAME: "postgresql://${POSTGRES_USER:-datapulse}:${POSTGRES_PASSWORD}@postgres:5432/datapulse?sslmode=disable"
    depends_on:
      postgres:
        condition: service_healthy
    mem_limit: 128m
    networks:
      - backend

  redis-exporter:
    image: oliver006/redis_exporter:v1.58.0
    container_name: datapulse-redis-exporter
    environment:
      REDIS_ADDR: "redis:6379"
      REDIS_PASSWORD: "${REDIS_PASSWORD}"
    depends_on:
      redis:
        condition: service_healthy
    mem_limit: 64m
    networks:
      - backend

  node-exporter:
    image: prom/node-exporter:v1.7.0
    container_name: datapulse-node-exporter
    mem_limit: 64m
    networks:
      - backend

  alertmanager:
    image: prom/alertmanager:v0.27.0
    container_name: datapulse-alertmanager
    ports:
      - "127.0.0.1:9093:9093"
    volumes:
      - ./observability/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml
    mem_limit: 64m
    networks:
      - backend
```

### FastAPI Metrics Middleware

```python
# src/datapulse/api/middleware/metrics.py

from prometheus_fastapi_instrumentator import Instrumentator, metrics

def setup_metrics(app: FastAPI) -> None:
    """Instrument FastAPI with Prometheus metrics."""
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=False,
        excluded_handlers=["/health", "/metrics"],
        env_var_name="ENABLE_METRICS",
    ).instrument(app).expose(app, endpoint="/metrics")
```

### Custom Pipeline Metrics

```python
# src/datapulse/pipeline/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# Counters
pipeline_runs_total = Counter(
    "datapulse_pipeline_runs_total",
    "Total pipeline runs",
    ["tenant_id", "status"],  # completed, failed, retrying
)

pipeline_stage_total = Counter(
    "datapulse_pipeline_stage_total",
    "Total stage executions",
    ["stage", "status"],
)

# Histograms
pipeline_duration_seconds = Histogram(
    "datapulse_pipeline_duration_seconds",
    "Pipeline total duration",
    ["tenant_id"],
    buckets=[30, 60, 120, 300, 600, 1200, 3600],
)

stage_duration_seconds = Histogram(
    "datapulse_stage_duration_seconds",
    "Individual stage duration",
    ["stage"],
    buckets=[5, 10, 30, 60, 120, 300],
)

# Gauges
quality_score_gauge = Gauge(
    "datapulse_quality_score",
    "Latest quality gate score (0-100)",
    ["tenant_id", "stage"],
)

active_pipeline_runs = Gauge(
    "datapulse_active_pipeline_runs",
    "Currently running pipelines",
)
```

### 5 Grafana Dashboards

#### Dashboard 1: API Performance
| Panel | Metric | Visualization |
|-------|--------|---------------|
| Request Rate | `rate(http_requests_total[5m])` | Time series |
| Latency P50/P95/P99 | `histogram_quantile(0.99, http_request_duration_seconds)` | Time series |
| Error Rate | `rate(http_requests_total{status=~"5.."}[5m])` | Stat + threshold |
| Top Slow Endpoints | `topk(10, avg by (handler)(http_request_duration_seconds))` | Table |
| Requests by Status | `sum by (status)(rate(http_requests_total[5m]))` | Pie chart |

#### Dashboard 2: Pipeline Health
| Panel | Metric | Visualization |
|-------|--------|---------------|
| Runs Today | `datapulse_pipeline_runs_total` | Stat |
| Success Rate | `runs{status="completed"} / runs_total` | Gauge (green/red) |
| Run Duration Trend | `datapulse_pipeline_duration_seconds` | Time series |
| Stage Breakdown | `datapulse_stage_duration_seconds` | Stacked bar |
| Active Runs | `datapulse_active_pipeline_runs` | Stat |
| Quality Score Trend | `datapulse_quality_score` | Time series per stage |

#### Dashboard 3: Database
| Panel | Metric | Visualization |
|-------|--------|---------------|
| Active Connections | `pg_stat_activity_count` | Gauge |
| Connection Pool | `pg_stat_activity_count / pg_settings_max_connections` | Gauge |
| Cache Hit Ratio | `pg_stat_database_blks_hit / (blks_hit + blks_read)` | Stat (target: >99%) |
| Table Sizes | `pg_total_relation_size_bytes` | Bar chart |
| Slow Queries | `pg_stat_statements_mean_time_seconds` | Table |
| Transactions/s | `rate(pg_stat_database_xact_commit[5m])` | Time series |

#### Dashboard 4: Infrastructure
| Panel | Metric | Visualization |
|-------|--------|---------------|
| CPU Usage | `node_cpu_seconds_total` | Time series per container |
| Memory Usage | `container_memory_usage_bytes` | Stacked area |
| Disk I/O | `node_disk_io_time_seconds_total` | Time series |
| Network I/O | `node_network_transmit_bytes_total` | Time series |
| Redis Memory | `redis_memory_used_bytes` | Gauge |
| Redis Hit Rate | `redis_keyspace_hits / (hits + misses)` | Stat |

#### Dashboard 5: Quality Gates
| Panel | Metric | Visualization |
|-------|--------|---------------|
| Quality Score Trend | Daily quality score over 30 days | Line chart |
| Check Pass Rate | Per check-type pass rate | Horizontal bar |
| Failed Checks Log | Recent failures with details | Table |
| Quality by Stage | Bronze vs Silver vs Gold scores | Grouped bar |

### Prometheus Alert Rules (10 rules)

```yaml
# observability/prometheus/rules/datapulse.yml
groups:
  - name: datapulse
    rules:
      # API alerts
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels: { severity: critical }
        annotations: { summary: "API error rate above 5%" }

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels: { severity: warning }
        annotations: { summary: "API P95 latency above 2 seconds" }

      # Pipeline alerts
      - alert: PipelineFailure
        expr: increase(datapulse_pipeline_runs_total{status="failed"}[1h]) > 0
        labels: { severity: critical }
        annotations: { summary: "Pipeline run failed in the last hour" }

      - alert: PipelineSlow
        expr: datapulse_pipeline_duration_seconds > 3600
        labels: { severity: warning }
        annotations: { summary: "Pipeline run exceeding 1 hour" }

      # Database alerts
      - alert: HighConnectionCount
        expr: pg_stat_activity_count > 80
        for: 5m
        labels: { severity: warning }
        annotations: { summary: "PostgreSQL connections above 80" }

      - alert: LowCacheHitRatio
        expr: pg_stat_database_blks_hit / (pg_stat_database_blks_hit + pg_stat_database_blks_read) < 0.95
        for: 10m
        labels: { severity: warning }
        annotations: { summary: "PostgreSQL cache hit ratio below 95%" }

      # Redis alerts
      - alert: RedisHighMemory
        expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.8
        for: 5m
        labels: { severity: warning }
        annotations: { summary: "Redis memory usage above 80%" }

      # Infrastructure alerts
      - alert: HighCPU
        expr: 100 - (avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 10m
        labels: { severity: warning }
        annotations: { summary: "CPU usage above 80% for 10 minutes" }

      - alert: HighMemory
        expr: node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes < 0.1
        for: 5m
        labels: { severity: critical }
        annotations: { summary: "Available memory below 10%" }

      - alert: DiskSpaceLow
        expr: node_filesystem_avail_bytes / node_filesystem_size_bytes < 0.15
        for: 5m
        labels: { severity: warning }
        annotations: { summary: "Disk space below 15%" }
```

---

## File Structure

```
observability/
├── prometheus/
│   ├── prometheus.yml               # Scrape config (all targets)
│   └── rules/
│       └── datapulse.yml            # 10 alert rules
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── datasources.yml      # Prometheus + Loki data sources
│   │   └── dashboards/
│   │       └── dashboards.yml       # Dashboard provisioning config
│   └── dashboards/
│       ├── api-performance.json     # Dashboard 1
│       ├── pipeline-health.json     # Dashboard 2
│       ├── database.json            # Dashboard 3
│       ├── infrastructure.json      # Dashboard 4
│       └── quality-gates.json       # Dashboard 5
├── loki/
│   └── loki-config.yml              # Loki storage + retention config
├── promtail/
│   └── promtail-config.yml          # Docker log scraping config
└── alertmanager/
    └── alertmanager.yml             # Slack webhook + routing

src/datapulse/
├── api/middleware/metrics.py        # NEW: Prometheus FastAPI middleware
└── pipeline/metrics.py              # NEW: Custom pipeline metrics
```

---

## Resource Requirements

| Service | Memory | Disk | CPU |
|---------|--------|------|-----|
| Prometheus | 512MB | ~2GB/month (30d retention) | Low |
| Grafana | 256MB | Minimal | Low |
| Loki | 256MB | ~1GB/month | Low |
| Promtail | 128MB | Minimal | Minimal |
| Exporters (3) | 256MB total | Minimal | Minimal |
| Alertmanager | 64MB | Minimal | Minimal |
| **Total** | **~1.5GB** | **~3GB/month** | **Low** |

---

## Dependencies

- Docker Compose (existing)
- Slack webhook URL (existing from Phase 2.6)
- No external services needed — everything self-hosted
