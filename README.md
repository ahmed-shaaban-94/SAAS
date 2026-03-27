# DataPulse

> Sales Analytics Platform -- Import, Clean, Analyze, Visualize

DataPulse is a data analytics platform built on a **medallion architecture** (Bronze / Silver / Gold) for processing and analyzing sales data. It ingests raw Excel files, transforms them through a structured pipeline, and serves business-ready metrics.

## Architecture

```
                    +-----------------+
                    |   Excel Files   |
                    |  (12 quarterly) |
                    +--------+--------+
                             |
                    Polars + PyArrow
                             |
              +--------------+--------------+
              |                             |
     +--------v--------+          +--------v--------+
     |    Parquet       |          |   PostgreSQL    |
     |    (57 MB)       |          |  bronze.sales   |
     |    Archive       |          |  1.1M rows      |
     +------------------+          +--------+--------+
                                            |
                                      dbt transforms
                                            |
                               +------------+------------+
                               |                         |
                      +--------v--------+       +--------v--------+
                      |     Silver      |       |      Gold       |
                      |   (cleaned)     |       |  (aggregated)   |
                      +-----------------+       +--------+--------+
                                                         |
                                                   Next.js Dashboard
```

## Quick Start

### Prerequisites

- Docker Desktop
- Git

### Setup

```bash
git clone https://github.com/ahmed-shaaban-94/SAAS.git
cd SAAS

# Copy environment file
cp .env.example .env

# Start all services
docker compose up -d --build
```

### Services

| Service | URL | Credentials |
|---------|-----|-------------|
| PostgreSQL | `localhost:5432` | datapulse / datapulse_dev |
| pgAdmin | `localhost:5050` | admin@datapulse.dev / admin |
| JupyterLab | `localhost:8888` | -- |

### Load Sales Data

```bash
# Mount your Excel files directory in docker-compose.yml, then:
docker exec -it datapulse-app python -m datapulse.bronze.loader --source /app/data/raw/sales

# Or generate Parquet only (no DB load):
docker exec -it datapulse-app python -m datapulse.bronze.loader --source /app/data/raw/sales --skip-db
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Data Processing | Python 3.12, Polars, PyArrow |
| Database | PostgreSQL 16 |
| Data Transforms | dbt-core + dbt-postgres |
| Configuration | Pydantic Settings |
| Logging | structlog |
| Containers | Docker Compose |
| Testing | pytest + pytest-cov |
| Frontend (planned) | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |

## Project Structure

```
datapulse/
|-- src/datapulse/
|   |-- bronze/              # Raw data ingestion (Excel -> Parquet -> PostgreSQL)
|   |-- import_pipeline/     # Generic CSV/Excel reader + type detection
|   |-- utils/               # Logging utilities
|   +-- config.py            # Application settings
|-- dbt/
|   +-- models/
|       |-- bronze/          # Source definitions
|       |-- staging/         # Silver layer (stg_sales — cleaned, 35 cols, 7 tests)
|       +-- marts/           # Gold layer (planned)
|-- migrations/              # SQL schema migrations
|-- tests/                   # pytest test suite
|-- notebooks/               # Jupyter notebooks for analysis
|-- docker-compose.yml       # PostgreSQL + App + pgAdmin
+-- pyproject.toml           # Python dependencies
```

## Current Status

| Phase | Status | Description |
|-------|--------|-------------|
| 1.1 Foundation | Done | Docker, Python env, import pipeline |
| 1.2 Bronze Layer | Done | 1.1M rows loaded into PostgreSQL |
| 1.3 Silver Layer | Done | Cleaned data, normalized status, EN billing, flags, 7 dbt tests |
| 1.4 Gold Layer | Next | Aggregations, star schema |
| 1.5 Dashboard | Planned | Next.js interactive charts |
| 1.6 Testing | Planned | 80%+ coverage |

## Data

- **Source**: 12 quarterly Excel files (Q1.2023 -- Q4.2025)
- **Volume**: 1,134,799 sales transactions, 46 columns
- **Raw size**: 272 MB (Excel) -> 57 MB (Parquet)
- **Categories**: Product, Customer, Site, Personnel, Financial

## Development

```bash
# Run tests
docker exec -it datapulse-app pytest --cov=datapulse

# Run dbt
docker exec -it datapulse-app dbt build --project-dir /app/dbt

# Lint
docker exec -it datapulse-app ruff check src/
```

## Roadmap

- **Phase 2**: Workflow automation (n8n)
- **Phase 3**: AI-powered analysis (LangGraph)
- **Phase 4**: Public website expansion

## License

Private

---

See [CLAUDE.md](./CLAUDE.md) for full technical reference.
See [PLAN.md](./PLAN.md) for detailed phase breakdown.
