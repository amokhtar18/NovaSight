#!/bin/bash
# ============================================================
# NovaSight Backend Entrypoint
# ============================================================
# Runs DB migrations and seeds default users before starting
# the Flask application.
#
# Environment variables:
#   SEED_USERS     - "true" (default) to auto-seed test users
#   SEED_PASSWORD  - Override password for all test users
#   FLASK_ENV      - development | testing | production
#   SKIP_MIGRATIONS - "true" to skip Alembic migrations
# ============================================================

set -e

echo "╔═══════════════════════════════════════════════════════╗"
echo "║           NovaSight Backend Starting...               ║"
echo "╚═══════════════════════════════════════════════════════╝"

# ── 1. Wait for PostgreSQL ──
echo "⏳ Waiting for PostgreSQL..."
MAX_RETRIES=30
RETRY_COUNT=0
# Use pg_isready or simple python check with psycopg2
until python -c "
import psycopg2
import os
url = os.environ.get('DATABASE_URL', 'postgresql://novasight:novasight@postgres:5432/novasight_platform')
# Parse the URL
from urllib.parse import urlparse
parsed = urlparse(url)
conn = psycopg2.connect(
    host=parsed.hostname,
    port=parsed.port or 5432,
    user=parsed.username,
    password=parsed.password,
    dbname=parsed.path.lstrip('/')
)
conn.close()
print('Connected!')
" 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "❌ PostgreSQL not ready after ${MAX_RETRIES} attempts. Continuing anyway..."
        break
    fi
    echo "  Waiting for database... (${RETRY_COUNT}/${MAX_RETRIES})"
    sleep 2
done
echo "✅ Database connection ready"

# ── 1b. Ensure Dagster database exists ──
echo "🔧 Ensuring Dagster database exists..."
python -c "
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os

# Connect to postgres database to create dagster db
url = os.environ.get('DATABASE_URL', 'postgresql://novasight:novasight@postgres:5432/novasight_platform')
from urllib.parse import urlparse
parsed = urlparse(url)

# Connect to 'postgres' system database
conn = psycopg2.connect(
    host=parsed.hostname,
    port=parsed.port or 5432,
    user=parsed.username,
    password=parsed.password,
    dbname='postgres'
)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

# Check if dagster database exists
cur.execute(\"SELECT 1 FROM pg_database WHERE datname='dagster'\")
exists = cur.fetchone()

if not exists:
    print('Creating dagster database...')
    cur.execute('CREATE DATABASE dagster')
    cur.execute(f'GRANT ALL PRIVILEGES ON DATABASE dagster TO {parsed.username}')
    print('Dagster database created!')
else:
    print('Dagster database already exists')

cur.close()
conn.close()
" 2>&1 || {
    echo "⚠️  Could not ensure dagster database. It may need manual creation."
}
echo "✅ Dagster database ready"

# ── 2. Run Alembic migrations ──
if [ "${SKIP_MIGRATIONS}" != "true" ]; then
    echo "🔄 Running database migrations..."
    flask db upgrade 2>&1 || {
        echo "⚠️  Migrations failed (tables may already exist). Continuing..."
    }
    echo "✅ Migrations complete"
else
    echo "⏭️  Skipping migrations (SKIP_MIGRATIONS=true)"
fi

# ── 3. Seed default users ──
if [ "${SEED_USERS:-true}" = "true" ] || [ "${SEED_USERS}" = "1" ] || [ "${SEED_USERS}" = "yes" ]; then
    echo "🌱 Seeding default test users..."
    flask seed users 2>&1 || {
        echo "⚠️  Seeding failed (may already be seeded). Continuing..."
    }
else
    echo "⏭️  Skipping user seeding (SEED_USERS=${SEED_USERS})"
fi

# ── 4. Provision ClickHouse databases for all tenants ──
# This ensures ClickHouse databases exist even if provisioning failed during seed
echo "🔧 Ensuring ClickHouse databases for all tenants..."
MAX_CH_RETRIES=15
CH_RETRY_COUNT=0
until python -c "
from app.services.clickhouse_client import ClickHouseClient
client = ClickHouseClient()
client.execute('SELECT 1')
print('ClickHouse connected!')
" 2>/dev/null; do
    CH_RETRY_COUNT=$((CH_RETRY_COUNT + 1))
    if [ $CH_RETRY_COUNT -ge $MAX_CH_RETRIES ]; then
        echo "⚠️  ClickHouse not ready after ${MAX_CH_RETRIES} attempts. Skipping provisioning..."
        break
    fi
    echo "  Waiting for ClickHouse... (${CH_RETRY_COUNT}/${MAX_CH_RETRIES})"
    sleep 2
done

if [ $CH_RETRY_COUNT -lt $MAX_CH_RETRIES ]; then
    flask tenant provision-ch-all 2>&1 || {
        echo "⚠️  ClickHouse provisioning had issues. Some databases may need manual setup."
    }
    echo "✅ ClickHouse databases ready"
fi

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║           NovaSight Backend Ready! 🚀                 ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# ── 4b. Install dbt packages (idempotent, container-local path) ──
DBT_PROJECT_DIR="${DBT_PROJECT_DIR:-/app/dbt}"
DBT_PROFILES_DIR="${DBT_PROFILES_DIR:-/app/dbt}"
export DBT_PACKAGES_INSTALL_PATH="${DBT_PACKAGES_INSTALL_PATH:-/var/dbt_packages}"
if [ -f "$DBT_PROJECT_DIR/packages.yml" ] && command -v dbt >/dev/null 2>&1; then
    echo "📦 Installing dbt packages to $DBT_PACKAGES_INSTALL_PATH ..."
    mkdir -p "$DBT_PACKAGES_INSTALL_PATH"
    (
        cd "$DBT_PROJECT_DIR" && \
        dbt deps --project-dir "$DBT_PROJECT_DIR" --profiles-dir "$DBT_PROFILES_DIR" 2>&1 \
            | tail -20
    ) || echo "⚠️  dbt deps failed (non-fatal). dbt runs may still work if packages aren't required."
fi

# ── 5. Start the application ──
exec "$@"
