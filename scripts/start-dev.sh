#!/bin/bash
# ============================================
# NovaSight Development Startup Script
# ============================================
# This script starts all NovaSight services in development mode
#
# Usage: ./scripts/start-dev.sh [options]
#
# Options:
#   --no-spark    Skip Spark cluster
#   --no-ollama   Skip Ollama LLM
#   --build       Force rebuild containers
#   --clean       Remove volumes and start fresh

set -e

echo "============================================"
echo "NovaSight Development Environment"
echo "============================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
NO_SPARK=false
NO_OLLAMA=false
BUILD=false
CLEAN=false

for arg in "$@"; do
    case $arg in
        --no-spark)
            NO_SPARK=true
            shift
            ;;
        --no-ollama)
            NO_OLLAMA=true
            shift
            ;;
        --build)
            BUILD=true
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
    esac
done

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}No .env file found. Creating from .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}.env file created. Please review and update values.${NC}"
fi

# Clean start if requested
if [ "$CLEAN" = true ]; then
    echo -e "${YELLOW}Cleaning up existing containers and volumes...${NC}"
    docker compose down -v
    echo -e "${GREEN}Cleanup complete!${NC}"
fi

# Build services to exclude
EXCLUDE_SERVICES=""
if [ "$NO_SPARK" = true ]; then
    EXCLUDE_SERVICES="$EXCLUDE_SERVICES --scale spark-master=0 --scale spark-worker-1=0 --scale spark-worker-2=0"
    echo -e "${YELLOW}Skipping Spark cluster${NC}"
fi

if [ "$NO_OLLAMA" = true ]; then
    EXCLUDE_SERVICES="$EXCLUDE_SERVICES --scale ollama=0"
    echo -e "${YELLOW}Skipping Ollama LLM${NC}"
fi

# Build if requested
BUILD_FLAG=""
if [ "$BUILD" = true ]; then
    BUILD_FLAG="--build"
    echo -e "${YELLOW}Forcing container rebuild...${NC}"
fi

echo ""
echo -e "${BLUE}Starting infrastructure services...${NC}"
docker compose up -d postgres redis clickhouse $BUILD_FLAG

echo -e "${BLUE}Waiting for databases to be healthy...${NC}"
sleep 10

echo -e "${BLUE}Starting Airflow 3.x services...${NC}"
docker compose up -d airflow-postgres airflow-init
sleep 15
echo -e "${BLUE}Starting Airflow API Server, DAG Processor, Scheduler, and Triggerer...${NC}"
docker compose up -d airflow-api-server airflow-dag-processor airflow-scheduler airflow-triggerer $BUILD_FLAG

echo -e "${BLUE}Dagster is integrated into the backend service...${NC}"

if [ "$NO_SPARK" = false ]; then
    echo -e "${BLUE}Starting Spark cluster...${NC}"
    docker compose up -d spark-master spark-worker-1 spark-worker-2
fi

if [ "$NO_OLLAMA" = false ]; then
    echo -e "${BLUE}Starting Ollama LLM...${NC}"
    docker compose up -d ollama
fi

echo -e "${BLUE}Starting NovaSight backend (with integrated Dagster)...${NC}"
docker compose up -d backend $BUILD_FLAG

echo -e "${BLUE}Starting NovaSight frontend...${NC}"
docker compose up -d frontend $BUILD_FLAG

echo ""
echo -e "${BLUE}Waiting for all services to be healthy...${NC}"
sleep 10

# Check service health
echo ""
echo "============================================"
echo "Service Status"
echo "============================================"
docker compose ps

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}NovaSight is ready!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Access the following services:"
echo ""
echo -e "  ${BLUE}Frontend:${NC}        http://localhost:5173"
echo -e "  ${BLUE}Backend API:${NC}     http://localhost:5000"
echo -e "  ${BLUE}Airflow UI:${NC}      http://localhost:8080  (airflow/airflow)"
echo -e "  ${BLUE}Dagster UI:${NC}      http://localhost:3000"
echo -e "  ${BLUE}Spark Master:${NC}    http://localhost:8081"
echo -e "  ${BLUE}ClickHouse:${NC}      http://localhost:8123"
echo -e "  ${BLUE}PostgreSQL:${NC}      localhost:5432"
echo -e "  ${BLUE}Redis:${NC}           localhost:6379"
if [ "$NO_OLLAMA" = false ]; then
    echo -e "  ${BLUE}Ollama:${NC}          http://localhost:11434"
fi
echo ""
echo "Default credentials:"
echo "  - NovaSight: admin@novasight.io / Admin123!"
echo "  - Airflow:   airflow / airflow"
echo ""
echo "Useful commands:"
echo "  - View logs:     docker compose logs -f [service]"
echo "  - Stop all:      docker compose down"
echo "  - Restart:       docker compose restart [service]"
echo ""
