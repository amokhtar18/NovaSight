# NovaSight Spark Image
# ======================
# Extends the official Spark image with Python dependencies
# required by NovaSight PySpark extraction jobs.

ARG SPARK_IMAGE=apache/spark:3.5.4
FROM ${SPARK_IMAGE}

USER root

# Install Python dependencies required by generated PySpark jobs
# Note: Spark 3.5.4 ships with Python 3.8, so we pin compatible versions
RUN pip3 install --no-cache-dir \
    clickhouse-connect==0.6.23

USER spark
