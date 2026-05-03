# NovaSight Dagster Dockerfile
# =============================
# Custom Dagster image with NovaSight dependencies

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Dagster packages (ensure latest versions)
RUN pip install --no-cache-dir \
    dagster>=1.9.0 \
    dagster-webserver>=1.9.0 \
    dagster-graphql>=1.9.0 \
    dagster-postgres>=0.25.0 \
    dagster-dbt>=0.25.0 \
    gql>=3.5.0

# Pre-install dbt packages into the image so containers don't need
# network access at first run and the bind-mounted /app/dbt is not
# corrupted by `dbt deps` (Windows bind-mount semantics).
ENV DBT_PACKAGES_INSTALL_PATH=/var/dbt_packages
COPY dbt/packages.yml dbt/dbt_project.yml /tmp/dbt-deps/
RUN mkdir -p "$DBT_PACKAGES_INSTALL_PATH" \
    && dbt deps \
        --project-dir /tmp/dbt-deps \
        --profiles-dir /tmp/dbt-deps \
    && rm -rf /tmp/dbt-deps

# Copy application code
COPY backend/ /app/backend/
COPY dbt/ /app/dbt/

# Set environment
ENV DAGSTER_HOME=/app/dagster_home
ENV PYTHONPATH=/app/backend

# Create dagster home
RUN mkdir -p $DAGSTER_HOME

# Copy Dagster configuration
COPY backend/orchestration/dagster.yaml $DAGSTER_HOME/dagster.yaml
COPY backend/orchestration/workspace.yaml $DAGSTER_HOME/workspace.yaml

EXPOSE 3000

# Default command runs webserver
CMD ["dagster-webserver", "-h", "0.0.0.0", "-p", "3000"]
