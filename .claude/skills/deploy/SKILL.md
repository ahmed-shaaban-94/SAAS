# Deploy to Production

Deploy the latest code to the production droplet (164.92.243.3).

## Pre-Deploy Checks

1. Ensure all tests pass locally (`make test`)
2. Ensure TypeScript compiles (`cd frontend && npx tsc --noEmit`)
3. Ensure Python lint passes (`ruff check src/ tests/`)
4. Check for `docker-compose.override.yml` on the droplet — remove or rename it before production builds

## Deploy Steps

1. Build Docker images with `docker compose build --no-cache` (no cache to avoid stale layers)
2. Push images to GHCR with proper tagging
3. SSH into the droplet and pull the new images
4. Run any pending database migrations
5. Run dbt transformations if models changed
6. Restart containers: `docker compose up -d`

## Post-Deploy Validation

1. Verify all containers are healthy with `docker ps` — check STATUS column for "healthy"
2. Hit the health endpoint: `curl http://localhost:8000/api/v1/health`
3. Confirm the frontend loads and is NOT in dev mode (no "Development Mode" banner, page loads fast)
4. Check container logs for errors: `docker compose logs --tail=20`
5. Verify disk usage is healthy: `df -h`

## Rollback

If any health check fails:
1. Identify the previous working image tag
2. Roll back: `docker compose pull` with previous tag
3. Restart: `docker compose up -d`
4. Report the failure reason to the user
