# NovaSight Airflow Dockerfile
# =============================
# Custom Airflow image with NovaSight dependencies

FROM apache/airflow:latest-python3.11

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    default-jdk \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME for Spark
ENV JAVA_HOME=/usr/lib/jvm/default-java
ENV PATH="${JAVA_HOME}/bin:${PATH}"

USER airflow

# Install Python dependencies for DAGs
RUN pip install --no-cache-dir \
    apache-airflow-providers-apache-spark \
    apache-airflow-providers-postgres \
    apache-airflow-providers-http \
    apache-airflow-providers-slack \
    pyspark==3.5.0 \
    clickhouse-connect \
    dbt-core \
    dbt-postgres \
    dbt-clickhouse \
    pandas \
    numpy \
    httpx \
    structlog

# Copy custom plugins and DAGs
COPY --chown=airflow:root plugins/ /opt/airflow/plugins/
COPY --chown=airflow:root dags/ /opt/airflow/dags/

# Set Airflow home
ENV AIRFLOW_HOME=/opt/airflow
