---
name: add-docker-service
description: "Add a new Docker service to all compose files with healthcheck, resource limits, and networking. Usage: /add-docker-service <name> <image-or-build> <port>"
---

You are adding a new Docker service to DataPulse. This modifies 3 compose files.

## Input
Parse the user's request for:
- **Service name** (e.g., `minio`, `grafana`, `prometheus`)
- **Image or build context** (e.g., `minio/minio:latest` or build from Dockerfile)
- **Port** (if any)
- **Purpose** (storage, monitoring, etc.)

## Steps

### 1. Add to docker-compose.yml (base)
Edit `docker-compose.yml` — add service in appropriate position:

```yaml
  <name>:
    image: <image>:<tag>
    container_name: datapulse-<name>
    restart: unless-stopped
    ports:
      - "<port>:<port>"
    environment:
      # Use env vars from .env with required/default pattern:
      SOME_VAR: ${SOME_VAR:-default}
      SECRET_VAR: ${SECRET_VAR:?SECRET_VAR must be set}
    volumes:
      - <name>_data:/data  # Named volume for persistence
    healthcheck:
      test: ["CMD-SHELL", "<health-command>"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
    deploy:
      resources:
        limits:
          memory: <appropriate>M  # 256M-512M typical
    networks:
      - backend  # or frontend-net if needs frontend access
```

Add volume to `volumes:` section:
```yaml
volumes:
  <name>_data:
```

Add `depends_on` to services that need it.

### 2. Add to docker-compose.override.yml (dev)
Edit `docker-compose.override.yml` — add dev overrides if needed:
- Volume mounts for config files
- Debug ports
- Dev-specific env vars

### 3. Add to docker-compose.prod.yml (production)
Edit `docker-compose.prod.yml`:
- Remove exposed ports (internal only)
- Adjust resource limits
- Add to appropriate profile if optional

### 4. Update .env.example
Add any new env vars with comments:
```bash
# <Service Name>
SOME_VAR=default-value
SECRET_VAR=  # Required: description
```

### 5. Update Makefile (if needed)
Add convenience commands if the service needs management:
```makefile
<name>-logs:
	docker compose logs -f <name>
```

### 6. Validate
```bash
cd /home/user/SAAS && docker compose config --quiet && echo "Config valid"
```

### 7. Report
Show:
- Service added to all 3 compose files
- Network: backend / frontend-net
- Port: host:container
- Volume: named volume
- Health check configured
- Env vars added to .env.example
- Memory limit set

## Conventions
- Container names: `datapulse-<name>`
- Networks: `backend` for internal, `frontend-net` if frontend needs access
- Always set `restart: unless-stopped`
- Always set `deploy.resources.limits.memory`
- Always add healthcheck
- Secrets via `${VAR:?must be set}`, defaults via `${VAR:-default}`
