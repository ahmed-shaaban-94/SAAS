# Contributing to DataPulse

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

### Prerequisites

- Docker Desktop
- Git
- Node.js 18+ (for frontend development outside Docker)

### Quick Start

```bash
git clone https://github.com/ahmed-shaaban-94/Data-Pulse.git
cd SAAS
cp .env.example .env
make up
```

### Verify Setup

```bash
make status          # Check service health
make test            # Run Python tests
make test-e2e        # Run Playwright E2E tests
```

## Code Standards

### Python

| Rule | Detail |
|------|--------|
| Version | 3.11+ |
| Linter | `ruff check src/ tests/` |
| Formatter | `ruff format src/ tests/` |
| Line length | 100 characters |
| Type hints | Required on all public functions |
| Config | Pydantic Settings |
| Logging | structlog (structured JSON) |

### Frontend (TypeScript)

| Rule | Detail |
|------|--------|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript strict mode |
| Styling | Tailwind CSS |
| Lint/Format | ESLint + Prettier (Next.js defaults) |

### dbt

| Rule | Detail |
|------|--------|
| Naming | `stg_*` for staging, `dim_*`/`fct_*`/`agg_*` for marts |
| Tests | Schema tests in YAML, minimum per model |
| Docs | Column descriptions in schema YAML files |

### SQL Migrations

- Sequential numbering: `NNN_description.sql`
- Tracked via `schema_migrations` table
- Always include `IF NOT EXISTS` guards

## Testing

| Layer | Command | Target |
|-------|---------|--------|
| Python | `make test` | 80%+ coverage (current: 95%+) |
| E2E | `make test-e2e` | All specs passing |
| dbt | `make dbt-test` | All schema + data tests passing |

## Branch Naming

| Type | Format | Example |
|------|--------|---------|
| Feature | `feat/<description>` | `feat/add-export-csv` |
| Bug fix | `fix/<description>` | `fix/chart-tooltip-overlap` |
| Refactor | `refactor/<description>` | `refactor/split-loader` |
| Docs | `docs/<description>` | `docs/update-readme` |

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add CSV export to dashboard
fix: correct date filter timezone offset
refactor: split bronze loader into smaller modules
docs: update API endpoint documentation
test: add missing repository edge cases
chore: update Docker base images
```

## Pull Request Process

1. Create a branch from `main`
2. Make your changes
3. Ensure all checks pass:
   - `make lint` — no linting errors
   - `make test` — all tests pass
   - `make test-e2e` — E2E specs pass
4. Submit a PR with a clear description
5. Wait for CI checks and review

## Project Structure

See the [README.md](./README.md#project-structure) for the full directory layout
and [docs/plans/](./docs/plans/) for detailed phase documentation.
