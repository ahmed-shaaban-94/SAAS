FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files and install
COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir -e ".[dev]" jupyterlab

EXPOSE 8888

# Default command: keep container running for interactive use
CMD ["tail", "-f", "/dev/null"]
