.PHONY: up down build test coverage coverage-pos diff-cover lint fmt dbt logs clean dev status pipeline demo help setup backup restore openapi openapi-check loadtest-dashboard loadtest-checkout loadtest-analytics-mixed loadtest-all

## Compose file shortcuts
DEV_COMPOSE  = docker compose -f docker-compose.yml -f docker-compose.dev.yml
PROD_COMPOSE = docker compose -f docker-compose.yml -f docker-compose.prod.yml

## Docker
up:
	$(DEV_COMPOSE) up -d --build

down:
	docker compose down

build:
	$(DEV_COMPOSE) build

logs:
	docker compose logs -f

## Development
dev:
	$(DEV_COMPOSE) up -d --build
	@echo ""
	@echo "DataPulse is running (DEV mode):"
	@echo "  Dashboard: http://localhost:3000"
	@echo "  API:       http://localhost:8000/docs"
	@echo "  Health:    http://localhost:8000/health"
	@echo ""

## Production (server only — requires IMAGE_TAG env var)
prod:
	$(PROD_COMPOSE) up -d
	@echo ""
	@echo "DataPulse is running (PROD mode):"
	@echo "  https://smartdatapulse.tech"
	@echo ""

setup:
	@echo "=== DataPulse Setup ==="
	@test -f .env || (cp .env.example .env && echo "[setup] Created .env from .env.example — edit with your passwords")
	$(DEV_COMPOSE) up -d --build
	@echo "Waiting for services..."
	@sleep 10
	@echo ""
	@echo "Setup complete. Services:"
	@docker compose ps --format "table {{.Name}}\t{{.Status}}"
	@echo ""
	@echo "Next steps:"
	@echo "  make load    # Import raw data"
	@echo "  make dbt     # Build silver/gold layers"
	@echo "  make demo    # Or do both at once"

status:
	@echo "=== DataPulse Service Status ==="
	@docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

pipeline:
	@echo "Triggering full pipeline run..."
	@curl -s -X POST http://localhost:8000/api/v1/pipeline/trigger \
		-H "Content-Type: application/json" \
		-H "X-Pipeline-Token: $${PIPELINE_WEBHOOK_SECRET}" \
		-d '{}' | python -m json.tool 2>/dev/null || echo "(requires running services + valid token)"

demo:
	@echo "=== DataPulse Demo Setup ==="
	$(DEV_COMPOSE) up -d --build
	@echo "Waiting for services to be healthy..."
	@sleep 10
	@echo "Running bronze loader..."
	docker exec datapulse-api python -m datapulse.bronze.loader --source /app/data/raw/sales || true
	@echo "Running dbt build..."
	docker exec datapulse-api dbt build --project-dir /app/dbt || true
	@echo ""
	@echo "Demo ready at http://localhost:80"

help:
	@echo "DataPulse — Business/Sales Analytics SaaS"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Docker:"
	@echo "  setup     Zero-to-working: copy .env + build + start (dev)"
	@echo "  up        Build and start all services (dev)"
	@echo "  dev       Start dev services and print access URLs"
	@echo "  prod      Start production services (requires IMAGE_TAG)"
	@echo "  down      Stop all services"
	@echo "  build     Build Docker images (dev)"
	@echo "  logs      Follow service logs"
	@echo "  status    Show service health status"
	@echo "  demo      Full demo: build + load data + dbt + serve (dev)"
	@echo ""
	@echo "Testing:"
	@echo "  test      Run Python unit tests (in container) with coverage"
	@echo "  coverage  Run unit tests locally with the same coverage gate CI enforces"
	@echo "  test-e2e  Run Playwright E2E tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint      Run ruff linter"
	@echo "  fmt       Run ruff formatter"
	@echo ""
	@echo "Data:"
	@echo "  load      Run bronze loader (import raw Excel/CSV)"
	@echo "  dbt       Run dbt build (staging + marts)"
	@echo "  dbt-test  Run dbt tests"
	@echo "  pipeline  Trigger full pipeline via API"
	@echo ""
	@echo "Backup:"
	@echo "  backup    Create compressed PostgreSQL backup"
	@echo "  restore   Restore from backup (BACKUP_FILE=path)"
	@echo ""
	@echo "API contract (issue #658):"
	@echo "  openapi         Dump FastAPI schema → contracts/openapi.json"
	@echo "  openapi-check   Fail if contracts/openapi.json is stale"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean     Stop services, remove volumes and caches"

## Testing
test:
	docker exec -it datapulse-api pytest --cov=datapulse --cov-report=term-missing

# Unit-test coverage with the same floor CI enforces. Reproducing CI's exact
# command locally avoids push-fail-fix-push round-trips (issue #540).
coverage:
	DATABASE_URL="sqlite:///:memory:" REDIS_URL="" SENTRY_ENVIRONMENT=test \
	    pytest -m unit --cov=datapulse --cov-report=term-missing --cov-fail-under=77 -q

# POS-specific coverage gate (audit §8 item 4). POS is the largest
# single module and gets its own higher floor — 85% — because the
# transaction + checkout + shift close critical paths must have tight
# unit coverage before v1.0 tag. Raise this floor incrementally; never
# lower it without a documented reason.
coverage-pos:
	DATABASE_URL="sqlite:///:memory:" REDIS_URL="" SENTRY_ENVIRONMENT=test \
	    pytest tests/test_pos_*.py -m unit \
	        --cov=datapulse.pos --cov=datapulse.api.routes.pos \
	        --cov-report=term-missing --cov-fail-under=85 -q

# Patch coverage — fails if the lines YOU CHANGED aren't tested to
# threshold (defaults to 81, matching codecov/patch). Catches the
# "CI fails on patch coverage after push" loop. Env overrides:
#   DIFF_COVER_THRESHOLD=90    bump the bar for a hardening change
#   DIFF_COVER_BASE=origin/X   compare against a non-main base
#   SKIP_DIFF_COVER=1          emergency bypass (use sparingly)
diff-cover:
	DATABASE_URL="sqlite:///:memory:" REDIS_URL="" SENTRY_ENVIRONMENT=test \
	    bash scripts/check_diff_coverage.sh

test-e2e:
	docker compose exec frontend npx playwright test

## Linting
lint:
	docker exec -it datapulse-api ruff check src/ tests/

fmt:
	docker exec -it datapulse-api ruff format src/ tests/

## dbt
dbt:
	docker exec -it datapulse-api dbt build --project-dir /app/dbt

dbt-test:
	docker exec -it datapulse-api dbt test --project-dir /app/dbt

dbt-lock:
	docker exec -it datapulse-api dbt deps --lock --project-dir /app/dbt
	@echo "package-lock.yml updated. Commit dbt/package-lock.yml alongside dbt/packages.yml."

## Data
load:
	docker exec -it datapulse-api python -m datapulse.bronze.loader --source /app/data/raw/sales

## API contract (issue #658)
# Dump the FastAPI OpenAPI schema to contracts/openapi.json. Re-run after
# changing any route or Pydantic response model, then run
# `cd frontend && npm run codegen` to refresh the TypeScript client.
openapi:
	python scripts/dump_openapi.py

# Verify contracts/openapi.json matches what the current FastAPI app emits.
# CI runs this in the typecheck job; a non-zero exit means the committed
# schema is stale and a PR must regenerate it.
openapi-check:
	python scripts/dump_openapi.py --check

## Load testing — k6 scenarios (#607). Requires k6 on $PATH, and
## BASE_URL + AUTH_TOKEN (+ TENANT_ID + POS_PIN for checkout) in env.
## See scripts/loadtest/README.md for provisioning.
loadtest-dashboard:
	k6 run scripts/loadtest/scenarios/dashboard.js

loadtest-checkout:
	k6 run scripts/loadtest/scenarios/pos_checkout.js

loadtest-analytics-mixed:
	k6 run scripts/loadtest/scenarios/analytics_mixed.js

loadtest-all: loadtest-dashboard loadtest-checkout loadtest-analytics-mixed

## Backup / Restore
backup:
	@bash scripts/backup.sh

restore:
	@bash scripts/restore.sh $(BACKUP_FILE)

## Cleanup
clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
