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
| Lint/Format | ESLint 8.57 + Prettier (Next.js defaults) — `.eslintrc.json` legacy config (#548) |

**ESLint version policy**: pinned to `^8.57` because the Next.js `eslint-config-next@15` preset still uses `.eslintrc.json`-style rules. Migrating to ESLint 9's flat config (`eslint.config.js`) is deferred until Next ships a flat-config compatible preset. CI runs `npm run lint` (= `next lint`) on every PR; `npm run lint:strict` (= `next lint --max-warnings=0`) is the local gate for zero-warning branches.

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
   - `make diff-cover` — your patch meets the 81% coverage target
     (same bar as CI's `codecov/patch` check; install once with
     `pip install -e '.[dev]'`). Use `SKIP_DIFF_COVER=1 git push`
     only in emergencies — the signal erodes fast when ignored.
4. Submit a PR with a clear description
5. Wait for CI checks and review

## Releases

Production deploys are tag-triggered. To cut a release:

1. Merge everything you want in the release to `main`. CI on `main` must be green.
2. Update `CHANGELOG.md` with a new heading `## [vX.Y.Z] — YYYY-MM-DD` and a
   bulleted summary of user-visible changes. Commit on `main`.
3. Tag locally and push:
   ```bash
   git checkout main && git pull --ff-only
   git tag -a vX.Y.Z -m "vX.Y.Z: <one-line summary>"
   git push origin vX.Y.Z
   ```
4. The `Deploy Production` workflow fires on the tag push. Follow it in the
   Actions tab; it will halt if the latest staging deploy is not green.
5. For hotfixes or re-deploys without cutting a new tag, use the Actions UI
   → **Deploy Production** → *Run workflow* (`workflow_dispatch`).

See [`docs/RUNBOOK.md §2`](./docs/RUNBOOK.md) for the full production-deploy runbook.

## Project Structure

See the [README.md](./README.md#project-structure) for the full directory layout
and [docs/plans/](./docs/plans/) for detailed phase documentation.
