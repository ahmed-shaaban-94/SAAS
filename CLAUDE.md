# DataPulse — Business/Sales Analytics SaaS

## Project Overview

A data analytics platform for sales data: import raw Excel/CSV files, clean and transform through a medallion architecture (bronze/silver/gold), analyze with SQL, and visualize on interactive dashboards.

**Pipeline**: Import (Bronze) -> Clean (Silver) -> Analyze (Gold) -> Dashboard

## Architecture

### Medallion Data Architecture

```
Excel/CSV files
     |
     v
[Bronze Layer]  -- Raw data, as-is from source
     |              Polars + PyArrow -> Parquet -> PostgreSQL typed tables
     v
[Silver Layer]  -- Cleaned, deduplicated, type-cast
     |              dbt models (views/tables in silver schema)
     v
[Gold Layer]    -- Aggregated, business-ready metrics
                    dbt models (tables in marts schema)
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Data Processing | Polars + PyArrow |
| Excel Engine | fastexcel (calamine) |
| Database | PostgreSQL 16 (Docker) |
| Data Transform | dbt-core + dbt-postgres |
| Config | Pydantic Settings |
| Logging | structlog |
| ORM | SQLAlchemy 2.0 |
| Containers | Docker Compose |
| DB Admin | pgAdmin 4 |
| Notebooks | JupyterLab |
| Frontend (planned) | Next.js 14 + TypeScript + Tailwind + shadcn/ui |
| Charts (planned) | Recharts |
| Dashboard (planned) | react-grid-layout |

## Project Structure

```
src/datapulse/
├── __init__.py
├── config.py                    # Pydantic settings (DB URL, limits, paths)
├── bronze/                      # Bronze layer — raw data ingestion
│   ├── __init__.py
│   ├── __main__.py              # CLI: python -m datapulse.bronze.loader
│   ├── column_map.py            # Excel header -> DB column mapping
│   └── loader.py                # Excel -> Polars -> Parquet -> PostgreSQL
├── import_pipeline/             # Generic file reader (CSV/Excel)
│   ├── __init__.py
│   ├── models.py                # Pydantic models (ImportConfig, ImportResult, ColumnInfo)
│   ├── reader.py                # read_csv(), read_excel(), read_file()
│   ├── type_detector.py         # Auto-detect column types from DataFrame
│   └── validator.py             # File validation (size, format)
└── utils/
    ├── __init__.py
    └── logging.py               # structlog configuration

dbt/
├── dbt_project.yml
├── profiles.yml
└── models/
    ├── bronze/                  # Source definitions + base models
    │   ├── _bronze__sources.yml
    │   └── bronze_sales.sql
    ├── staging/                 # Silver layer (cleaning + renaming)
    │   ├── _staging__sources.yml
    │   └── stg_sales.sql        # Cleaned: 30 cols, dedup, billing EN, derived fields
    └── marts/                   # Gold layer (planned)

migrations/                      # SQL migrations (run by bronze loader)
├── 001_create_bronze_schema.sql

tests/
├── test_reader.py
└── test_type_detector.py
```

## Docker Services

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| `app` | datapulse-app | 8888 | Python app + JupyterLab |
| `postgres` | datapulse-db | 5432 | PostgreSQL 16 |
| `pgadmin` | datapulse-pgadmin | 5050 | Database admin UI |

```bash
docker compose up -d --build
```

## Database

### Schemas (Medallion)

| Schema | Purpose | Populated by |
|--------|---------|-------------|
| `bronze` | Raw data, as-is from source | Python bronze loader |
| `public_staging` / `silver` | Cleaned, transformed | dbt staging models |
| `marts` / `gold` | Aggregated, business-ready | dbt models (planned) |

### Current Tables/Views

| Table/View | Schema | Rows | Purpose |
|-------|--------|------|---------|
| `bronze.sales` | bronze | 1,134,799 | Raw sales data (Q1.2023–Q4.2025, 46 columns) |
| `public_staging.stg_sales` | staging | ~1.1M (deduped) | Cleaned sales (35 cols, EN billing, normalized status, flags, 7 dbt tests) |

### Bronze Sales Columns (Key)

- **Transaction**: reference_no, date, billing_document, billing_type
- **Product**: material, material_desc, brand, category, subcategory, division, segment
- **Customer/Site**: customer, customer_name, site, site_name, buyer
- **Personnel**: personel_number, person_name, position, area_mg
- **Financials**: quantity, net_sales, gross_sales, sales_not_tax, tax, paid, kzwi1

## Configuration

All settings via environment variables or `.env` file (Pydantic Settings):

| Setting | Default | Description |
|---------|---------|-------------|
| `DATABASE_URL` | `postgresql://datapulse:datapulse_dev@localhost:5432/datapulse` | PostgreSQL connection |
| `MAX_FILE_SIZE_MB` | 500 | Max upload file size |
| `MAX_ROWS` | 10,000,000 | Max rows per dataset |
| `MAX_COLUMNS` | 200 | Max columns per dataset |
| `BRONZE_BATCH_SIZE` | 50,000 | Rows per insert batch |

## Running the Bronze Pipeline

```bash
# Inside Docker container
docker exec -it datapulse-app python -m datapulse.bronze.loader --source /app/data/raw/sales

# Parquet only (no DB)
docker exec -it datapulse-app python -m datapulse.bronze.loader --source /app/data/raw/sales --skip-db
```

## Conventions

### Code Style (Python)
- Python 3.11+, Ruff for linting (line-length=100)
- Pydantic models for all config and data contracts
- structlog for structured JSON logging
- Type hints on all public functions
- Small files (200-400 lines), extract when approaching 800
- Functions < 50 lines, no nesting > 4 levels
- Immutable patterns — always create new objects, never mutate

### Documentation Language
- Code and docs: English
- Inline comments: Arabic where helpful for clarity (mixed)

### Testing
- pytest + pytest-cov
- Target: 80%+ coverage on `src/datapulse/`

## Future Phases

- **Phase 1.3**: Data Cleaning (silver layer via dbt) [DONE]
- **Phase 1.4**: Data Analysis (gold layer, aggregations, statistics)
- **Phase 1.5**: Dashboard & Visualization (Next.js frontend)
- **Phase 2**: Automation via n8n workflows
- **Phase 3**: AI-powered analysis via LangGraph
- **Phase 4**: Public website / landing page
