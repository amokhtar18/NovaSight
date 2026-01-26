#!/bin/bash
# ============================================
# NovaSight Database Initialization Script
# ============================================
# This script initializes all databases for NovaSight
#
# Usage: ./scripts/init-db.sh

set -e

echo "============================================"
echo "NovaSight Database Initialization"
echo "============================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Default values
POSTGRES_HOST=${POSTGRES_HOST:-localhost}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_USER=${POSTGRES_USER:-novasight}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-novasight}
POSTGRES_DB=${POSTGRES_DB:-novasight_platform}

CLICKHOUSE_HOST=${CLICKHOUSE_HOST:-localhost}
CLICKHOUSE_PORT=${CLICKHOUSE_PORT:-8123}

echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
until docker-compose exec -T postgres pg_isready -U ${POSTGRES_USER} > /dev/null 2>&1; do
    echo "PostgreSQL not ready, waiting..."
    sleep 2
done
echo -e "${GREEN}PostgreSQL is ready!${NC}"

echo -e "${YELLOW}Waiting for ClickHouse to be ready...${NC}"
until curl -s "http://${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/ping" > /dev/null 2>&1; do
    echo "ClickHouse not ready, waiting..."
    sleep 2
done
echo -e "${GREEN}ClickHouse is ready!${NC}"

# Initialize PostgreSQL
echo -e "${YELLOW}Initializing PostgreSQL database...${NC}"
docker-compose exec -T postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -f /docker-entrypoint-initdb.d/01-init.sql || true
echo -e "${GREEN}PostgreSQL initialized!${NC}"

# Initialize ClickHouse
echo -e "${YELLOW}Initializing ClickHouse database...${NC}"
docker-compose exec -T clickhouse clickhouse-client --query "CREATE DATABASE IF NOT EXISTS novasight"
docker-compose exec -T clickhouse clickhouse-client --query "CREATE DATABASE IF NOT EXISTS novasight_staging"

# Create sample tables in ClickHouse
docker-compose exec -T clickhouse clickhouse-client --multiquery <<EOF
CREATE TABLE IF NOT EXISTS novasight.ingestion_logs (
    id UUID DEFAULT generateUUIDv4(),
    tenant_id UUID,
    job_id UUID,
    table_name String,
    rows_ingested UInt64,
    bytes_ingested UInt64,
    duration_ms UInt64,
    status String,
    error_message Nullable(String),
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (tenant_id, created_at)
PARTITION BY toYYYYMM(created_at);

CREATE TABLE IF NOT EXISTS novasight.query_logs (
    id UUID DEFAULT generateUUIDv4(),
    tenant_id UUID,
    user_id UUID,
    query_text String,
    query_hash String,
    duration_ms UInt64,
    rows_read UInt64,
    bytes_read UInt64,
    result_rows UInt64,
    status String,
    error_message Nullable(String),
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (tenant_id, created_at)
PARTITION BY toYYYYMM(created_at);
EOF

echo -e "${GREEN}ClickHouse initialized!${NC}"

# Run Flask migrations
echo -e "${YELLOW}Running Flask database migrations...${NC}"
docker-compose exec -T backend flask db upgrade || echo "Migrations may already be applied"
echo -e "${GREEN}Migrations complete!${NC}"

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Database initialization complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "You can now access:"
echo "  - PostgreSQL: localhost:5432"
echo "  - ClickHouse: localhost:8123 (HTTP) / localhost:9000 (Native)"
echo ""
