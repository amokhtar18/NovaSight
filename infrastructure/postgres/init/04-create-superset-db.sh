#!/bin/bash
# =========================================
# Create the Apache Superset metadata database
# =========================================
# Superset stores its own metadata (dashboards, charts, slices, …) in a
# dedicated logical database inside the same Postgres server NovaSight
# already uses. This script creates that database on first start.

set -e

create_database_if_not_exists() {
    local database="$1"
    local user="$2"

    echo "Checking if database '$database' exists..."

    if psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" -tAc "SELECT 1 FROM pg_database WHERE datname='$database'" | grep -q 1; then
        echo "Database '$database' already exists"
    else
        echo "Creating database '$database'..."
        psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
            CREATE DATABASE $database;
            GRANT ALL PRIVILEGES ON DATABASE $database TO $user;
EOSQL
        echo "Database '$database' created successfully"
    fi
}

create_database_if_not_exists "superset" "$POSTGRES_USER"

echo "Superset database ready"
