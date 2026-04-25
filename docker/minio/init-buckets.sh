#!/bin/bash
# ============================================
# MinIO Bucket Initialization Script
# ============================================
# Creates buckets for seeded tenants on first startup.
# This script is executed when MinIO starts.

set -e

# Wait for MinIO to be ready
echo "Waiting for MinIO to be ready..."
until mc alias set local http://localhost:9000 ${MINIO_ROOT_USER:-minioadmin} ${MINIO_ROOT_PASSWORD:-minioadmin} 2>/dev/null; do
    echo "MinIO not ready yet, waiting..."
    sleep 2
done

echo "MinIO is ready. Creating buckets..."

# Create buckets for demo/seeded tenants
# These match the tenant slugs created by backend/app/seed.py

# Demo tenant bucket
if ! mc ls local/novasight-novasight-demo 2>/dev/null; then
    mc mb local/novasight-novasight-demo
    echo "Created bucket: novasight-novasight-demo"
else
    echo "Bucket already exists: novasight-novasight-demo"
fi

# Acme Corp demo tenant bucket
if ! mc ls local/novasight-acme-corp 2>/dev/null; then
    mc mb local/novasight-acme-corp
    echo "Created bucket: novasight-acme-corp"
else
    echo "Bucket already exists: novasight-acme-corp"
fi

# Set bucket policies to allow authenticated access
mc anonymous set none local/novasight-novasight-demo
mc anonymous set none local/novasight-acme-corp

echo "MinIO bucket initialization complete."
