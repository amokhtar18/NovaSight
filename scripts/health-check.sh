#!/bin/bash
# ============================================
# NovaSight Health Check Script
# ============================================
# Comprehensive health check for all NovaSight services
#
# Usage: ./scripts/health-check.sh [options]
#
# Options:
#   --json       Output in JSON format
#   --quiet      Only output failures
#   --wait       Wait for services to be healthy (max 60s)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default options
JSON_OUTPUT=false
QUIET=false
WAIT_MODE=false
WAIT_TIMEOUT=60

# Colors (disabled in JSON mode)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
for arg in "$@"; do
    case $arg in
        --json)
            JSON_OUTPUT=true
            ;;
        --quiet|-q)
            QUIET=true
            ;;
        --wait)
            WAIT_MODE=true
            ;;
    esac
done

# Service definitions
declare -A SERVICES
SERVICES=(
    ["postgres"]="http://localhost:5432"
    ["redis"]="http://localhost:6379"
    ["clickhouse"]="http://localhost:8123/ping"
    ["backend"]="http://localhost:5000/health"
    ["frontend"]="http://localhost:5173"
    ["dagster"]="http://localhost:3000/server_info"
    ["airflow-api-server"]="http://localhost:8080/api/v2/version"
    ["minio"]="http://localhost:9001/minio/health/live"
    ["ollama"]="http://localhost:11434/api/tags"
)

# Results storage
declare -A RESULTS
HEALTHY_COUNT=0
UNHEALTHY_COUNT=0

check_http() {
    local url=$1
    local timeout=${2:-5}
    
    if curl -s -o /dev/null -w '' --connect-timeout "$timeout" "$url" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

check_tcp() {
    local host=$1
    local port=$2
    
    if timeout 2 bash -c "echo > /dev/tcp/$host/$port" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

check_service() {
    local name=$1
    local url=$2
    
    # Extract host and port for TCP check
    local proto=$(echo "$url" | grep :// | sed -e's,^\(.*://\).*,\1,g')
    local host_port=$(echo "${url#$proto}" | cut -d/ -f1)
    local host=$(echo "$host_port" | cut -d: -f1)
    local port=$(echo "$host_port" | cut -d: -f2)
    
    local status="unhealthy"
    local message=""
    
    case $name in
        postgres)
            if check_tcp "$host" "$port"; then
                status="healthy"
            else
                message="TCP connection failed"
            fi
            ;;
        redis)
            if check_tcp "$host" "$port"; then
                status="healthy"
            else
                message="TCP connection failed"
            fi
            ;;
        *)
            if check_http "$url"; then
                status="healthy"
            else
                message="HTTP health check failed"
            fi
            ;;
    esac
    
    RESULTS[$name]=$status
    
    if [ "$status" = "healthy" ]; then
        ((HEALTHY_COUNT++))
    else
        ((UNHEALTHY_COUNT++))
    fi
    
    # Output
    if [ "$JSON_OUTPUT" = false ]; then
        if [ "$status" = "healthy" ]; then
            if [ "$QUIET" = false ]; then
                echo -e "  ${GREEN}✓${NC} $name: healthy"
            fi
        else
            echo -e "  ${RED}✗${NC} $name: $status - $message"
        fi
    fi
}

wait_for_services() {
    local start_time=$(date +%s)
    local all_healthy=false
    
    while [ $(($(date +%s) - start_time)) -lt $WAIT_TIMEOUT ]; do
        HEALTHY_COUNT=0
        UNHEALTHY_COUNT=0
        
        for name in "${!SERVICES[@]}"; do
            check_service "$name" "${SERVICES[$name]}" 2>/dev/null
        done
        
        if [ $UNHEALTHY_COUNT -eq 0 ]; then
            all_healthy=true
            break
        fi
        
        echo -e "${YELLOW}Waiting for services... ($HEALTHY_COUNT/${#SERVICES[@]} healthy)${NC}"
        sleep 5
    done
    
    if [ "$all_healthy" = true ]; then
        echo -e "${GREEN}All services are healthy!${NC}"
    else
        echo -e "${RED}Timeout waiting for services${NC}"
        return 1
    fi
}

output_json() {
    echo "{"
    echo '  "timestamp": "'$(date -Iseconds)'",'
    echo '  "healthy_count": '$HEALTHY_COUNT','
    echo '  "unhealthy_count": '$UNHEALTHY_COUNT','
    echo '  "services": {'
    
    local first=true
    for name in "${!RESULTS[@]}"; do
        if [ "$first" = true ]; then
            first=false
        else
            echo ","
        fi
        echo -n "    \"$name\": \"${RESULTS[$name]}\""
    done
    echo ""
    echo "  }"
    echo "}"
}

main() {
    if [ "$JSON_OUTPUT" = false ] && [ "$QUIET" = false ]; then
        echo ""
        echo -e "${BLUE}NovaSight Health Check${NC}"
        echo -e "${BLUE}════════════════════════════════════════${NC}"
        echo ""
    fi
    
    if [ "$WAIT_MODE" = true ]; then
        wait_for_services
    else
        for name in "${!SERVICES[@]}"; do
            check_service "$name" "${SERVICES[$name]}"
        done
    fi
    
    if [ "$JSON_OUTPUT" = true ]; then
        output_json
    elif [ "$QUIET" = false ]; then
        echo ""
        echo -e "${BLUE}════════════════════════════════════════${NC}"
        echo -e "Summary: ${GREEN}$HEALTHY_COUNT healthy${NC}, ${RED}$UNHEALTHY_COUNT unhealthy${NC}"
        echo ""
    fi
    
    # Exit with error if any service is unhealthy
    if [ $UNHEALTHY_COUNT -gt 0 ]; then
        exit 1
    fi
}

main
