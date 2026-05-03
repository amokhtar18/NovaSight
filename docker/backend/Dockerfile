# NovaSight Backend Dockerfile
# ============================
# Multi-stage build for Flask API
#
# Build context: REPOSITORY ROOT (so backend/ and dbt/ are both available).
#   docker build -f docker/backend/Dockerfile -t novasight-backend --target production .

# ============================================
# Base Stage
# ============================================
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV DBT_PACKAGES_INSTALL_PATH=/var/dbt_packages

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# Development Stage
# ============================================
FROM base AS development

# Install Python deps (dbt CLI + adapters live here)
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

# Pre-install dbt packages so runtime doesn't need to call the registry
COPY dbt/packages.yml dbt/dbt_project.yml /tmp/dbt-deps/
RUN mkdir -p "$DBT_PACKAGES_INSTALL_PATH" \
    && dbt deps \
        --project-dir /tmp/dbt-deps \
        --profiles-dir /tmp/dbt-deps \
    && rm -rf /tmp/dbt-deps

ENV FLASK_ENV=development
ENV FLASK_DEBUG=1

EXPOSE 5000

CMD ["flask", "run", "--host=0.0.0.0", "--reload", "--debug"]

# ============================================
# Builder Stage (for production)
# ============================================
FROM base AS builder

COPY backend/requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ============================================
# Production Stage
# ============================================
FROM python:3.11-slim AS production

# Create non-root user
RUN groupadd -r novasight && useradd -r -g novasight novasight

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    DBT_PACKAGES_INSTALL_PATH=/var/dbt_packages

WORKDIR /app

# Runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder and install
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Pre-install dbt packages
COPY dbt/packages.yml dbt/dbt_project.yml /tmp/dbt-deps/
RUN mkdir -p "$DBT_PACKAGES_INSTALL_PATH" \
    && dbt deps \
        --project-dir /tmp/dbt-deps \
        --profiles-dir /tmp/dbt-deps \
    && rm -rf /tmp/dbt-deps \
    && chown -R novasight:novasight "$DBT_PACKAGES_INSTALL_PATH"

# Copy application code
COPY --chown=novasight:novasight backend/ /app/

# Copy entrypoint script
COPY --chown=novasight:novasight docker/backend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh 2>/dev/null || true

# Switch to non-root user
USER novasight

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

EXPOSE 5000

# Entrypoint runs migrations + seed, then exec's CMD
ENTRYPOINT ["/entrypoint.sh"]

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:create_app()"]
