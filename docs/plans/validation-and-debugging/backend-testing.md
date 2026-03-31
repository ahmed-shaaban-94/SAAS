# Backend Testing Strategy

Python testing for the DataPulse backend: FastAPI API, data pipeline, analytics, and infrastructure.

## Current State (DONE)

- **Framework**: pytest + pytest-cov
- **Coverage**: 95%+ on `src/datapulse/`
- **Test files**: `tests/conftest.py`, `test_reader.py`, `test_type_detector.py`, `test_config.py`, `test_validator.py`, `test_loader.py`, `test_coverage_gaps.py`
- **Total tests**: 100+ across all modules

## Running Tests

```bash
# Full test suite with coverage
docker exec -it datapulse-app pytest --cov=src/datapulse --cov-report=term-missing

# Specific module
docker exec -it datapulse-app pytest tests/test_reader.py -v

# Single test
docker exec -it datapulse-app pytest tests/test_reader.py::test_read_csv_basic -v

# With output visible
docker exec -it datapulse-app pytest -s --tb=short

# Coverage report as HTML
docker exec -it datapulse-app pytest --cov=src/datapulse --cov-report=html
# Output in htmlcov/ directory
```

## Test Categories

### 1. Unit Tests

Tests for isolated functions and classes with no external dependencies.

| Module | File | What It Tests |
|--------|------|---------------|
| `import_pipeline.reader` | `test_reader.py` | `read_csv()`, `read_excel()`, `read_file()` -- file parsing with Polars |
| `import_pipeline.type_detector` | `test_type_detector.py` | Auto-detection of column types from DataFrames |
| `import_pipeline.validator` | `test_validator.py` | File size, format, and column validation |
| `config` | `test_config.py` | Pydantic settings loading, defaults, env overrides |
| `bronze.column_map` | `test_coverage_gaps.py` | Excel header to DB column mapping |
| `pipeline.quality` | `test_coverage_gaps.py` | 7 quality check functions |

### 2. Integration Tests

Tests that interact with the database or external services.

| Module | What It Tests |
|--------|---------------|
| `bronze.loader` | Full Excel -> Polars -> Parquet -> PostgreSQL pipeline |
| `analytics.repository` | SQLAlchemy queries against marts schema |
| `analytics.service` | Business logic with default filters |
| `pipeline.repository` | CRUD for pipeline_runs table |
| `pipeline.service` | Pipeline lifecycle (start/complete/fail) |
| `pipeline.executor` | Bronze loader and dbt subprocess execution |
| `pipeline.quality_repository` | Quality check persistence |
| `pipeline.quality_service` | Quality gate orchestration |

### 3. API Tests

Tests for FastAPI endpoints using `TestClient`.

| Endpoint Group | Routes Tested |
|---------------|---------------|
| Health | `GET /health` (200 OK, 503 DB down) |
| Analytics | 10 endpoints under `/api/v1/analytics/` |
| Pipeline | 11 endpoints under `/api/v1/pipeline/` |

## Fixtures (`tests/conftest.py`)

Key fixtures to understand and reuse:

```python
# Database session (uses test database or mocked)
@pytest.fixture
def db_session():
    """Provides a SQLAlchemy session scoped to a single test."""

# FastAPI test client
@pytest.fixture
def client(db_session):
    """TestClient with dependency overrides for DB session."""

# Sample DataFrames
@pytest.fixture
def sample_sales_df():
    """Polars DataFrame matching bronze.sales schema."""

# Temporary files for import tests
@pytest.fixture
def sample_csv(tmp_path):
    """Creates a temporary CSV file for import testing."""

@pytest.fixture
def sample_excel(tmp_path):
    """Creates a temporary Excel file for import testing."""
```

## Mocking Patterns

### Database Mocking

```python
from unittest.mock import MagicMock, patch

# Mock the session
mock_session = MagicMock()
mock_session.execute.return_value.scalars.return_value.all.return_value = [...]

# Patch at the dependency injection level
with patch("datapulse.api.deps.get_db_session", return_value=mock_session):
    response = client.get("/api/v1/analytics/summary")
```

### Subprocess Mocking (for dbt)

```python
@patch("subprocess.run")
def test_dbt_execution(mock_run):
    mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="OK")
    result = executor.run_dbt_stage("staging")
    assert result.success is True
```

### External Service Mocking

```python
# Mock Polars file reading
@patch("polars.read_excel")
def test_read_excel(mock_read):
    mock_read.return_value = pl.DataFrame({"col1": [1, 2, 3]})
    result = read_file("test.xlsx")
    assert result.row_count == 3
```

## Coverage Targets

| Module | Current | Target | Notes |
|--------|---------|--------|-------|
| `config.py` | 95%+ | 90% | Env var edge cases |
| `bronze/` | 95%+ | 90% | Loader + column_map |
| `import_pipeline/` | 95%+ | 90% | Reader + validator + type detector |
| `analytics/` | 95%+ | 85% | Repository queries need live DB |
| `pipeline/` | 95%+ | 85% | Executor subprocess mocking |
| `api/` | 95%+ | 85% | All routes via TestClient |
| **Overall** | **95%+** | **80%** | Minimum acceptable |

## Recommended Additions (TODO)

### Property-Based Testing

```bash
pip install hypothesis
```

Use Hypothesis for data-heavy modules:

- [ ] `type_detector.py` -- random DataFrames with mixed types
- [ ] `validator.py` -- boundary values for file sizes and row counts
- [ ] `column_map.py` -- fuzzy header matching edge cases

### Load Testing for API

```bash
pip install locust
```

- [ ] Locustfile for analytics endpoints under concurrent load
- [ ] Measure response times at 10, 50, 100 concurrent users

### Contract Testing

- [ ] Validate API responses against Pydantic models programmatically
- [ ] Ensure frontend TypeScript types stay in sync with backend models

### Test Organization

- [ ] Split `test_coverage_gaps.py` into module-specific files
- [ ] Add `tests/api/` directory for endpoint tests
- [ ] Add `tests/integration/` directory for DB-dependent tests
- [ ] Add pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`

```ini
# pyproject.toml addition
[tool.pytest.ini_options]
markers = [
    "unit: fast tests with no external deps",
    "integration: tests requiring database",
    "slow: tests taking > 5 seconds",
]
```

## Checklist for Adding New Tests

1. Identify the module and function under test
2. Check if a fixture already exists in `conftest.py`
3. Write the test following existing patterns (arrange/act/assert)
4. Mock external dependencies (DB, filesystem, subprocess)
5. Run with coverage to verify the new code is covered
6. Ensure the test is deterministic (no random failures, no time dependencies)
