# NovaSight Backend Dockerfile
# ============================
# Multi-stage build for production-ready Flask API

FROM python:3.11-slim as builder

# Set build environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /build

# Install build dependencies including Oracle Instant Client
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libaio1t64 \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/lib/x86_64-linux-gnu/libaio.so.1t64 /usr/lib/x86_64-linux-gnu/libaio.so.1

# Install Oracle Instant Client for thick mode support
RUN mkdir -p /opt/oracle && \
    wget -q https://download.oracle.com/otn_software/linux/instantclient/2350000/instantclient-basiclite-linux.x64-23.5.0.24.07.zip -O /tmp/instantclient.zip && \
    unzip -q /tmp/instantclient.zip -d /opt/oracle && \
    rm /tmp/instantclient.zip && \
    echo /opt/oracle/instantclient_23_5 > /etc/ld.so.conf.d/oracle-instantclient.conf && \
    ldconfig

# Install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt


# Development stage
FROM python:3.11-slim as development

# Set environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app
ENV FLASK_ENV=development
ENV DEBIAN_FRONTEND=noninteractive
ENV LD_LIBRARY_PATH=/opt/oracle/instantclient_23_5:$LD_LIBRARY_PATH

WORKDIR /app

# Install runtime and dev dependencies with retry logic
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

# Install Oracle Instant Client for thick mode support
RUN mkdir -p /opt/oracle && \
    wget -q https://download.oracle.com/otn_software/linux/instantclient/2350000/instantclient-basiclite-linux.x64-23.5.0.24.07.zip -O /tmp/instantclient.zip && \
    unzip -q /tmp/instantclient.zip -d /opt/oracle && \
    rm /tmp/instantclient.zip && \
    echo /opt/oracle/instantclient_23_5 > /etc/ld.so.conf.d/oracle-instantclient.conf && \
    ldconfig

# Copy wheels from builder
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Install dev dependencies
COPY requirements-dev.txt* ./
RUN if [ -f requirements-dev.txt ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

# Copy application code
COPY . .

# Expose port
EXPOSE 5000

# Run with hot reload
CMD ["flask", "run", "--host=0.0.0.0", "--reload", "--debug"]


# Production stage
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r novasight && useradd -r -g novasight novasight

# Set environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app
ENV FLASK_ENV=production
ENV LD_LIBRARY_PATH=/opt/oracle/instantclient_23_5:$LD_LIBRARY_PATH

WORKDIR /app

# Install runtime dependencies including Oracle Instant Client requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    libaio1t64 \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/lib/x86_64-linux-gnu/libaio.so.1t64 /usr/lib/x86_64-linux-gnu/libaio.so.1

# Install Oracle Instant Client for thick mode support
RUN mkdir -p /opt/oracle && \
    wget -q https://download.oracle.com/otn_software/linux/instantclient/2350000/instantclient-basiclite-linux.x64-23.5.0.24.07.zip -O /tmp/instantclient.zip && \
    unzip -q /tmp/instantclient.zip -d /opt/oracle && \
    rm /tmp/instantclient.zip && \
    echo /opt/oracle/instantclient_23_5 > /etc/ld.so.conf.d/oracle-instantclient.conf && \
    ldconfig

# Copy wheels from builder
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application code
COPY --chown=novasight:novasight . .

# Switch to non-root user
USER novasight

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Expose port
EXPOSE 5000

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:create_app()"]
