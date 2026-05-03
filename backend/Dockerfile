# NovaSight Backend Dockerfile
# ============================
# Multi-stage build for production-ready Flask API.
#
# Build context: REPOSITORY ROOT (so we can reach both backend/ and dbt/).
# Build manually with:
#   docker build -f backend/Dockerfile -t novasight-backend:prod --target production .

FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /build

# Build dependencies including Oracle Instant Client requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libaio1t64 \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/lib/x86_64-linux-gnu/libaio.so.1t64 /usr/lib/x86_64-linux-gnu/libaio.so.1

# Oracle Instant Client (so dbt-oracle / cx_Oracle can resolve)
RUN mkdir -p /opt/oracle && \
    wget -q https://download.oracle.com/otn_software/linux/instantclient/2350000/instantclient-basiclite-linux.x64-23.5.0.24.07.zip -O /tmp/instantclient.zip && \
    unzip -q /tmp/instantclient.zip -d /opt/oracle && \
    rm /tmp/instantclient.zip && \
    echo /opt/oracle/instantclient_23_5 > /etc/ld.so.conf.d/oracle-instantclient.conf && \
    ldconfig

# Python wheels
COPY backend/requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt


# ============================================
# Development stage
# ============================================
FROM python:3.11-slim AS development

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app \
    FLASK_ENV=development \
    DEBIAN_FRONTEND=noninteractive \
    LD_LIBRARY_PATH=/opt/oracle/instantclient_23_5:$LD_LIBRARY_PATH \
    DAGSTER_HOME=/app/dagster_home \
    DAGSTER_COMPUTE_LOGS_DIR=/app/dagster_home/compute_logs \
    DBT_PACKAGES_INSTALL_PATH=/var/dbt_packages

WORKDIR /app

# Runtime + dev OS dependencies
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        git \
        libaio1t64 \
        wget \
        unzip \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/lib/x86_64-linux-gnu/libaio.so.1t64 /usr/lib/x86_64-linux-gnu/libaio.so.1

# Oracle Instant Client
RUN mkdir -p /opt/oracle && \
    wget -q https://download.oracle.com/otn_software/linux/instantclient/2350000/instantclient-basiclite-linux.x64-23.5.0.24.07.zip -O /tmp/instantclient.zip && \
    unzip -q /tmp/instantclient.zip -d /opt/oracle && \
    rm /tmp/instantclient.zip && \
    echo /opt/oracle/instantclient_23_5 > /etc/ld.so.conf.d/oracle-instantclient.conf && \
    ldconfig

# Python deps from wheels
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Dev-only deps (optional)
COPY backend/requirements-dev.txt* ./
RUN if [ -f requirements-dev.txt ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

# Pre-install dbt packages into the image (offline-friendly runtime)
COPY dbt/packages.yml dbt/dbt_project.yml /tmp/dbt-deps/
RUN mkdir -p "$DBT_PACKAGES_INSTALL_PATH" \
    && dbt deps \
        --project-dir /tmp/dbt-deps \
        --profiles-dir /tmp/dbt-deps \
    && rm -rf /tmp/dbt-deps

# App code
COPY backend/ /app/

# Dagster home + supervisor logs
RUN mkdir -p $DAGSTER_HOME $DAGSTER_COMPUTE_LOGS_DIR /var/log/supervisor && \
    cp orchestration/dagster.yaml $DAGSTER_HOME/dagster.yaml && \
    cp orchestration/workspace.yaml $DAGSTER_HOME/workspace.yaml

EXPOSE 5000 3000

CMD ["flask", "run", "--host=0.0.0.0", "--reload", "--debug"]


# ============================================
# Production stage
# ============================================
FROM python:3.11-slim AS production

# Non-root user
RUN groupadd -r novasight && useradd -r -g novasight novasight

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app \
    FLASK_ENV=production \
    LD_LIBRARY_PATH=/opt/oracle/instantclient_23_5:$LD_LIBRARY_PATH \
    DAGSTER_HOME=/app/dagster_home \
    DAGSTER_COMPUTE_LOGS_DIR=/app/dagster_home/compute_logs \
    DBT_PACKAGES_INSTALL_PATH=/var/dbt_packages

WORKDIR /app

# Runtime OS deps + Oracle Instant Client requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    libaio1t64 \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/lib/x86_64-linux-gnu/libaio.so.1t64 /usr/lib/x86_64-linux-gnu/libaio.so.1

# Oracle Instant Client
RUN mkdir -p /opt/oracle && \
    wget -q https://download.oracle.com/otn_software/linux/instantclient/2350000/instantclient-basiclite-linux.x64-23.5.0.24.07.zip -O /tmp/instantclient.zip && \
    unzip -q /tmp/instantclient.zip -d /opt/oracle && \
    rm /tmp/instantclient.zip && \
    echo /opt/oracle/instantclient_23_5 > /etc/ld.so.conf.d/oracle-instantclient.conf && \
    ldconfig

# Python deps from wheels (built in `builder`)
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Pre-install dbt packages into the image
COPY dbt/packages.yml dbt/dbt_project.yml /tmp/dbt-deps/
RUN mkdir -p "$DBT_PACKAGES_INSTALL_PATH" \
    && dbt deps \
        --project-dir /tmp/dbt-deps \
        --profiles-dir /tmp/dbt-deps \
    && rm -rf /tmp/dbt-deps \
    && chown -R novasight:novasight "$DBT_PACKAGES_INSTALL_PATH"

# App code
COPY --chown=novasight:novasight backend/ /app/

# Dagster + supervisor dirs
RUN mkdir -p $DAGSTER_HOME $DAGSTER_COMPUTE_LOGS_DIR /var/log/supervisor && \
    cp orchestration/dagster.yaml $DAGSTER_HOME/dagster.yaml && \
    cp orchestration/workspace.yaml $DAGSTER_HOME/workspace.yaml && \
    chown -R novasight:novasight $DAGSTER_HOME /var/log/supervisor

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

EXPOSE 5000 3000

CMD ["supervisord", "-c", "/app/supervisord.conf"]
