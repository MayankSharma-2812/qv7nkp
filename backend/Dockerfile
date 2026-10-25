# Multi-stage or optimized lean build for Gridbricks Backend
FROM python:3.11-slim AS runtime

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GRIDBRICKS_DB_PATH=/app/data/gridbricks.db \
    PORT=8000

# Install minimal OS dependencies for network operations & security updates
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged application user
RUN useradd -m -u 1000 -s /bin/bash appuser

WORKDIR /app

# Install Python production dependencies first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source and packaged verified historical dataset
COPY app/ ./app/
COPY data/ ./data/

# Set ownership to unprivileged user
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Health check using FastAPI /api/v1/health endpoint respecting dynamic PORT
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT:-8000}/api/v1/health || exit 1

# Start Uvicorn respecting dynamic PORT (for Render / Docker Compose) with graceful signal handling
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
