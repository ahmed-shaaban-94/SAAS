.PHONY: up down build test lint fmt dbt logs clean dev status pipeline demo help setup backup restore

## Docker
up:
	docker compose up -d --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

## Development
dev:
	docker compose up -d --build
	@echo ""
	@echo "DataPulse is running:"
	@echo "  Dashboard: http://localhost:3000"
	@echo "  API:       http://localhost:8000/docs"
	@echo "  Health:    http://localhost:8000/health"
	@echo "  pgAdmin:   http://localhost:5050"
	@echo "  n8n:       http://localhost:5678"
	@echo ""

setup:
	@echo "=== DataPulse Setup ==="
	@test -f .env || (cp .env.example .env && echo "[setup] Created .env from .env.example — edit with your passwords")
	docker compose up -d --build
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
	@curl -s -X POST http://localhost:80/api/v1/pipeline/trigger \
		-H "Content-Type: application/json" \
		-H "X-Pipeline-Token: $${PIPELINE_WEBHOOK_SECRET}" \
		-d '{}' | python -m json.tool 2>/dev/null || echo "(requires running services + valid token)"

demo:
	@echo "=== DataPulse Demo Setup ==="
	docker compose up -d --build
	@echo "Waiting for services to be healthy..."
	@sleep 10
	@echo "Running bronze loader..."
	docker exec datapulse-app python -m datapulse.bronze.loader --source /app/data/raw/sales || true
	@echo "Running dbt build..."
	docker exec datapulse-app dbt build --project-dir /app/dbt || true
	@echo ""
	@echo "Demo ready at http://localhost:80"

help:
	@echo "DataPulse — Business/Sales Analytics SaaS"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Docker:"
	@echo "  setup     Zero-to-working: copy .env + build + start"
	@echo "  up        Build and start all services"
	@echo "  down      Stop all services"
	@echo "  build     Build Docker images"
	@echo "  logs      Follow service logs"
	@echo "  dev       Start services and print access URLs"
	@echo "  status    Show service health status"
	@echo "  demo      Full demo: build + load data + dbt + serve"
	@echo ""
	@echo "Testing:"
	@echo "  test      Run Python unit tests with coverage"
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
	@echo "Cleanup:"
	@echo "  clean     Stop services, remove volumes and caches"

## Testing
test:
	docker exec -it datapulse-app pytest --cov=datapulse --cov-report=term-missing

test-e2e:
	docker compose exec frontend npx playwright test

## Linting
lint:
	docker exec -it datapulse-app ruff check src/ tests/

fmt:
	docker exec -it datapulse-app ruff format src/ tests/

## dbt
dbt:
	docker exec -it datapulse-app dbt build --project-dir /app/dbt

dbt-test:
	docker exec -it datapulse-app dbt test --project-dir /app/dbt

## Data
load:
	docker exec -it datapulse-app python -m datapulse.bronze.loader --source /app/data/raw/sales

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
