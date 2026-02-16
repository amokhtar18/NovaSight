# NovaSight Airflow Dockerfile
# =============================
# Custom Airflow image with NovaSight dependencies and Spark binaries
# Updated: February 2026 - Airflow 3.1.7 (latest stable)
# Uses pre-downloaded Spark binaries from ./infrastructure/spark for faster builds
#
# IMPORTANT: Build context must be project root, not docker/airflow
# Run: ./infrastructure/spark/download-spark.ps1 before building

FROM apache/airflow:3.1.7-python3.12

USER root

# Install system dependencies including Docker CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    default-jdk \
    curl \
    procps \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME for Spark operations
ENV JAVA_HOME=/usr/lib/jvm/default-java
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# ============================================
# Install Apache Spark 3.5.4 (from project dir)
# ============================================
ENV SPARK_VERSION=3.5.4
ENV SPARK_HOME=/opt/spark
ENV PATH="${SPARK_HOME}/bin:${SPARK_HOME}/sbin:${PATH}"

# Create Spark directories
RUN mkdir -p ${SPARK_HOME}/bin \
    ${SPARK_HOME}/sbin \
    ${SPARK_HOME}/jars \
    ${SPARK_HOME}/conf \
    ${SPARK_HOME}/python \
    /opt/spark/jobs && \
    chown -R airflow:root ${SPARK_HOME} /opt/spark/jobs

# Copy pre-downloaded Spark binaries from project directory
# These are downloaded via ./infrastructure/spark/download-spark.ps1
COPY --chown=airflow:root infrastructure/spark/bin/ ${SPARK_HOME}/bin/
COPY --chown=airflow:root infrastructure/spark/sbin/ ${SPARK_HOME}/sbin/
COPY --chown=airflow:root infrastructure/spark/conf/ ${SPARK_HOME}/conf/
COPY --chown=airflow:root infrastructure/spark/jars/ ${SPARK_HOME}/jars/
COPY --chown=airflow:root infrastructure/spark/python/ ${SPARK_HOME}/python/

# Add airflow user to docker group for docker exec fallback
RUN usermod -aG docker airflow || true

USER airflow

# Upgrade pip first
RUN pip install --no-cache-dir --upgrade pip

# Install Python dependencies for DAGs including Spark provider
RUN pip install --no-cache-dir \
    apache-airflow-providers-apache-spark \
    apache-airflow-providers-postgres \
    apache-airflow-providers-http \
    apache-airflow-providers-smtp \
    apache-airflow-providers-slack \
    apache-airflow-providers-common-sql \
    pyspark==3.5.4 \
    clickhouse-connect \
    pandas \
    numpy \
    httpx \
    structlog \
    pendulum

# Install dbt packages separately
RUN pip install --no-cache-dir \
    dbt-core \
    dbt-postgres \
    dbt-clickhouse

# Copy custom plugins and DAGs
COPY --chown=airflow:root docker/airflow/plugins/ /opt/airflow/plugins/
COPY --chown=airflow:root docker/airflow/dags/ /opt/airflow/dags/

# Copy init script for creating connections
COPY --chown=airflow:root docker/airflow/scripts/init-connections.sh /opt/airflow/scripts/init-connections.sh

# Set Airflow home
ENV AIRFLOW_HOME=/opt/airflow
