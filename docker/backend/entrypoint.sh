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

# ── Logging Functions ──
log_info()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO  | $1"; }
log_warn()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARN  | $1"; }
log_error() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR | $1" >&2; }
log_debug() { [ "${DEBUG:-false}" = "true" ] && echo "[$(date '+%Y-%m-%d %H:%M:%S')] DEBUG | $1"; }

echo "╔═══════════════════════════════════════════════════════╗"
echo "║           NovaSight Backend Starting...               ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
log_info "Environment: FLASK_ENV=${FLASK_ENV:-development}"
log_info "Database URL: ${DATABASE_URL:-not set}"

# ── 1. Wait for PostgreSQL ──
log_info "Waiting for PostgreSQL..."
MAX_RETRIES=30
RETRY_COUNT=0
DB_ERROR=""

until python -c "
import psycopg2, os, sys
from urllib.parse import urlparse
try:
    url = os.environ.get('DATABASE_URL', 'postgresql://novasight:novasight@postgres:5432/novasight_platform')
    parsed = urlparse(url)
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        dbname=parsed.path.lstrip('/'),
        connect_timeout=5
    )
    conn.close()
except psycopg2.OperationalError as e:
    print(f'DB_ERROR:{e}', file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f'DB_ERROR:{type(e).__name__}: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    DB_ERROR=$(python -c "
import psycopg2, os, sys
from urllib.parse import urlparse
try:
    url = os.environ.get('DATABASE_URL', 'postgresql://novasight:novasight@postgres:5432/novasight_platform')
    parsed = urlparse(url)
    conn = psycopg2.connect(host=parsed.hostname, port=parsed.port or 5432, user=parsed.username, password=parsed.password, dbname=parsed.path.lstrip('/'), connect_timeout=2)
    conn.close()
except Exception as e:
    print(str(e))
" 2>&1 || true)
    
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        log_error "PostgreSQL not ready after ${MAX_RETRIES} attempts"
        log_error "Last error: ${DB_ERROR}"
        log_warn "Continuing anyway - application may fail to start"
        break
    fi
    log_warn "Database not ready (${RETRY_COUNT}/${MAX_RETRIES}): ${DB_ERROR}"
    sleep 2
done

if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
    log_info "Database connection established successfully"
fi

# ── 2. Initialize Database Schema ──
if [ "${SKIP_MIGRATIONS}" != "true" ]; then
    log_info "Initializing database schema..."
    set +e
    
    # Use SQLAlchemy create_all to create tables from models (more reliable than migrations)
    INIT_OUTPUT=$(python -c "
from app import create_app
from app.extensions import db

app = create_app()
with app.app_context():
    # Create all tables from models
    db.create_all()
    print('Tables created successfully')
" 2>&1)
    INIT_STATUS=$?
    
    if [ $INIT_STATUS -eq 0 ]; then
        log_info "Database schema initialized successfully"
        
        # Stamp the database to mark migrations as applied
        flask db stamp head 2>/dev/null || true
        log_info "Migration state synchronized"
    else
        if echo "$INIT_OUTPUT" | grep -q "already exists"; then
            log_info "Database schema already exists"
        else
            log_warn "Schema initialization returned: $INIT_STATUS"
            log_debug "Output: $INIT_OUTPUT"
        fi
    fi
    set -e
else
    log_info "Skipping database initialization (SKIP_MIGRATIONS=true)"
fi

# ── 3. Seed default data ──
if [ "${SEED_USERS:-true}" = "true" ] || [ "${SEED_USERS}" = "1" ] || [ "${SEED_USERS}" = "yes" ]; then
    log_info "Seeding default data..."
    set +e
    
    # Use Python directly to seed, which triggers auto-seed in app initialization
    SEED_OUTPUT=$(python -c "
from app import create_app
from app.extensions import db
from app.seed import seed_default_users

app = create_app()
with app.app_context():
    try:
        result = seed_default_users()
        if result:
            print(f'Seeded {len(result)} users')
        else:
            print('No users seeded (may already exist)')
    except Exception as e:
        print(f'Seed note: {e}')
" 2>&1)
    SEED_STATUS=$?
    
    if [ $SEED_STATUS -eq 0 ]; then
        log_info "Data seeding completed: $SEED_OUTPUT"
    else
        log_info "Seeding skipped (data may already exist)"
        log_debug "Seed output: $SEED_OUTPUT"
    fi
    set -e
else
    log_info "Skipping data seeding (SEED_USERS=${SEED_USERS})"
fi

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║           NovaSight Backend Ready! 🚀                 ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# ── dbt packages ──
# Packages are now baked into the image at build time. No runtime
# `dbt deps` is needed.

# ── 4. Start the application ──
exec "$@"
