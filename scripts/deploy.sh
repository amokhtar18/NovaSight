#!/bin/bash
# ============================================
# NovaSight Deployment Script
# ============================================
# Unified deployment script for development, staging, and production
#
# Usage:
#   ./scripts/deploy.sh [environment] [options]
#
# Environments:
#   dev         Local development (default)
#   test        Testing with integration tests
#   staging     Kubernetes staging environment
#   production  Production deployment (requires confirmation)
#
# Options:
#   --build          Force rebuild containers
#   --clean          Wipe containers, volumes, project images, network and build cache
#   --skip-tests     Skip running tests before deployment
#   --no-ollama      Skip Ollama LLM service
#   --no-airflow     Skip Airflow (use Dagster only)
#   --monitoring     Include monitoring stack (Prometheus, Grafana, Loki)
#   --dry-run        Show what would be done without executing
#   --verbose        Enable verbose output
#   --rollback       Rollback to previous deployment (k8s only)
#   --version        Specify version tag (default: latest)
#   --help           Show this help message

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default values
ENVIRONMENT="dev"
BUILD=false
CLEAN=false
SKIP_TESTS=false
NO_OLLAMA=false
NO_AIRFLOW=false
MONITORING=false
DRY_RUN=false
VERBOSE=false
ROLLBACK=false
VERSION="latest"

# ============================================
# Helper Functions
# ============================================

print_banner() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}${MAGENTA}NovaSight Deployment${NC}                                      ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  Self-Service End-to-End BI Platform                        ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${MAGENTA}[DEBUG]${NC} $1"
    fi
}

show_help() {
    echo "NovaSight Deployment Script"
    echo ""
    echo "Usage: $0 [environment] [options]"
    echo ""
    echo "Environments:"
    echo "  dev         Local development with Docker Compose (default)"
    echo "  test        Run integration tests in containers"
    echo "  staging     Deploy to Kubernetes staging"
    echo "  production  Deploy to Kubernetes production"
    echo ""
    echo "Options:"
    echo "  --build          Force rebuild containers"
    echo "  --clean          Remove volumes and start fresh"
    echo "  --skip-tests     Skip running tests before deployment"
    echo "  --no-ollama      Skip Ollama LLM service"
    echo "  --no-airflow     Skip Airflow (use Dagster only)"
    echo "  --monitoring     Include monitoring stack (Prometheus, Grafana, Loki)"
    echo "  --dry-run        Show what would be done without executing"
    echo "  --verbose        Enable verbose output"
    echo "  --rollback       Rollback to previous deployment (k8s only)"
    echo "  --version=TAG    Specify version tag (default: latest)"
    echo "  --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 dev --build             # Development with rebuild"
    echo "  $0 dev --monitoring        # Development with monitoring stack"
    echo "  $0 test                    # Run integration tests"
    echo "  $0 staging --version=v1.2  # Deploy v1.2 to staging"
    echo "  $0 production              # Production deployment"
    exit 0
}

check_prerequisites() {
    print_step "Checking prerequisites..."
    
    local missing=()
    
    if ! command -v docker &> /dev/null; then
        missing+=("docker")
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        missing+=("docker-compose")
    fi
    
    if [[ "$ENVIRONMENT" == "staging" || "$ENVIRONMENT" == "production" ]]; then
        if ! command -v kubectl &> /dev/null; then
            missing+=("kubectl")
        fi
        if ! command -v helm &> /dev/null; then
            missing+=("helm")
        fi
    fi
    
    if [ ${#missing[@]} -ne 0 ]; then
        print_error "Missing required tools: ${missing[*]}"
        print_info "Please install the missing tools and try again."
        exit 1
    fi
    
    print_success "All prerequisites met"
}

check_env_file() {
    print_step "Checking environment configuration..."
    
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        if [ -f "$PROJECT_ROOT/.env.example" ]; then
            print_warning "No .env file found. Creating from .env.example..."
            cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
            print_info "Please review .env and update secrets before production deployment"
        else
            print_error "No .env or .env.example file found"
            exit 1
        fi
    else
        print_success "Environment file exists"
    fi
}

run_tests() {
    if [ "$SKIP_TESTS" = true ]; then
        print_warning "Skipping tests (--skip-tests flag)"
        return 0
    fi
    
    print_step "Running pre-deployment tests..."
    
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would run: $PROJECT_ROOT/scripts/run-all-tests.sh"
        return 0
    fi
    
    if [ -x "$PROJECT_ROOT/scripts/run-all-tests.sh" ]; then
        "$PROJECT_ROOT/scripts/run-all-tests.sh" || {
            print_error "Tests failed. Aborting deployment."
            print_info "Use --skip-tests to bypass (not recommended)"
            exit 1
        }
    else
        print_warning "Test script not found or not executable"
    fi
}

# ============================================
# Development Deployment
# ============================================
deploy_development() {
    print_step "Deploying development environment..."
    
    cd "$PROJECT_ROOT"
    
    local compose_cmd="docker compose"
    if ! docker compose version &> /dev/null 2>&1; then
        compose_cmd="docker-compose"
    fi
    
    local build_flag=""
    [ "$BUILD" = true ] && build_flag="--build"
    
    if [ "$CLEAN" = true ]; then
        print_info "Wiping containers, volumes, project images, network and build cache..."
        if [ "$DRY_RUN" = true ]; then
            print_info "[DRY-RUN] Would run: $compose_cmd down -v --remove-orphans --rmi local"
            print_info "[DRY-RUN] Would run: docker network rm novasight-network"
            print_info "[DRY-RUN] Would run: docker builder prune -af"
        else
            $compose_cmd down -v --remove-orphans --rmi local
            docker network rm novasight-network 2>/dev/null || true
            docker builder prune -af >/dev/null 2>&1 || true
        fi
    fi
    
    # Build excluded services list
    local scale_opts=""
    if [ "$NO_OLLAMA" = true ]; then
        scale_opts="$scale_opts --scale ollama=0"
    fi
    
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would run: $compose_cmd up -d $build_flag $scale_opts"
    else
        # Start infrastructure first
        print_info "Starting infrastructure services..."
        $compose_cmd up -d postgres redis clickhouse $build_flag
        
        print_info "Waiting for databases to be healthy..."
        sleep 10
        
        # Start Airflow 3.x (unless disabled)
        if [ "$NO_AIRFLOW" = false ]; then
            print_info "Starting Airflow 3.x services..."
            $compose_cmd up -d airflow-postgres airflow-init
            sleep 15
            print_info "Starting Airflow API Server, DAG Processor, Scheduler, and Triggerer..."
            $compose_cmd up -d airflow-api-server airflow-dag-processor airflow-scheduler airflow-triggerer
        else
            print_info "Skipping Airflow (--no-airflow flag set, using Dagster only)"
        fi
        
        # Start optional services
        if [ "$NO_OLLAMA" = false ]; then
            print_info "Starting Ollama..."
            $compose_cmd up -d ollama
        fi
        
        # Start application services (with integrated Dagster)
        print_info "Starting application services (with integrated Dagster)..."
        $compose_cmd up -d backend frontend $build_flag
        
        # Start monitoring stack if requested
        if [ "$MONITORING" = true ]; then
            print_info "Starting monitoring stack (Prometheus, Grafana, Loki)..."
            $compose_cmd -f docker-compose.yml -f docker-compose.logging.yml up -d prometheus grafana loki promtail 2>/dev/null || {
                print_warning "Monitoring services not found in compose files. Skipping..."
            }
        fi
    fi
    
    print_success "Development environment deployed!"
    print_info ""
    print_info "Services available at:"
    print_info "  Frontend:     http://localhost:5173"
    print_info "  Backend API:  http://localhost:5000"
    print_info "  API Docs:     http://localhost:5000/api/v1/docs"
    print_info "  Dagster UI:   http://localhost:3000"
    if [ "$NO_AIRFLOW" = false ]; then
        print_info "  Airflow UI:   http://localhost:8080 (airflow/airflow)"
    fi
    print_info "  ClickHouse:   http://localhost:8123"
    if [ "$NO_OLLAMA" = false ]; then
        print_info "  Ollama:       http://localhost:11434"
    fi
    if [ "$MONITORING" = true ]; then
        print_info "  Grafana:      http://localhost:3001 (admin/admin)"
        print_info "  Prometheus:   http://localhost:9090"
    fi
    print_info ""
    print_info "Default credentials:"
    print_info "  NovaSight:   admin@novasight.io / Admin123!"
    print_info "  Airflow:     airflow / airflow"
}

# ============================================
# Test Deployment
# ============================================
deploy_test() {
    print_step "Setting up test environment..."
    
    cd "$PROJECT_ROOT"
    
    local compose_cmd="docker compose"
    if ! docker compose version &> /dev/null 2>&1; then
        compose_cmd="docker-compose"
    fi
    
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would run test containers"
    else
        # Start test infrastructure
        print_info "Starting test infrastructure..."
        $compose_cmd -f docker-compose.test.yml up -d
        
        print_info "Waiting for services to be healthy..."
        sleep 15
        
        # Run tests
        print_info "Running integration tests..."
        
        # Backend tests
        print_info "Running backend tests..."
        $compose_cmd -f docker-compose.test.yml exec -T backend pytest -v --tb=short || {
            print_error "Backend tests failed"
            $compose_cmd -f docker-compose.test.yml down -v
            exit 1
        }
        
        # Frontend tests
        print_info "Running frontend tests..."
        $compose_cmd -f docker-compose.test.yml exec -T frontend npm test -- --run || {
            print_warning "Frontend tests failed or skipped"
        }
        
        # E2E tests
        print_info "Running E2E tests..."
        $compose_cmd -f docker-compose.test.yml exec -T frontend npm run e2e || {
            print_warning "E2E tests failed or skipped"
        }
        
        # Cleanup
        print_info "Cleaning up test environment..."
        $compose_cmd -f docker-compose.test.yml down -v
    fi
    
    print_success "Test deployment completed!"
}

# ============================================
# Kubernetes Staging Deployment
# ============================================
deploy_staging() {
    print_step "Deploying to Kubernetes staging..."
    
    # Check kubectl context
    local current_context=$(kubectl config current-context 2>/dev/null)
    print_info "Current kubectl context: $current_context"
    
    if [[ ! "$current_context" =~ staging ]]; then
        print_warning "Current context doesn't appear to be staging. Continue anyway? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            print_info "Deployment cancelled"
            exit 0
        fi
    fi
    
    if [ "$ROLLBACK" = true ]; then
        print_info "Rolling back staging deployment..."
        if [ "$DRY_RUN" = true ]; then
            print_info "[DRY-RUN] Would run: helm rollback novasight -n novasight-staging"
        else
            helm rollback novasight -n novasight-staging
        fi
        print_success "Rollback completed"
        exit 0
    fi
    
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would run Helm deployment to staging"
        helm upgrade --install novasight "$PROJECT_ROOT/helm/novasight" \
            -n novasight-staging \
            -f "$PROJECT_ROOT/helm/novasight/values-staging.yaml" \
            --set backend.image.tag="$VERSION" \
            --set frontend.image.tag="$VERSION" \
            --dry-run
    else
        # Create namespace if not exists
        kubectl create namespace novasight-staging --dry-run=client -o yaml | kubectl apply -f -
        
        # Deploy with Helm
        helm upgrade --install novasight "$PROJECT_ROOT/helm/novasight" \
            -n novasight-staging \
            -f "$PROJECT_ROOT/helm/novasight/values-staging.yaml" \
            --set backend.image.tag="$VERSION" \
            --set frontend.image.tag="$VERSION" \
            --wait --timeout=10m
    fi
    
    print_success "Staging deployment completed!"
    
    print_info ""
    print_info "Verifying deployment..."
    kubectl get pods -n novasight-staging
}

# ============================================
# Production Deployment
# ============================================
deploy_production() {
    print_step "Deploying to Production..."
    
    # Safety check
    echo ""
    print_warning "⚠️  PRODUCTION DEPLOYMENT ⚠️"
    print_warning "You are about to deploy to PRODUCTION"
    echo ""
    print_info "Version: $VERSION"
    print_info "Kubectl context: $(kubectl config current-context 2>/dev/null)"
    echo ""
    
    if [ "$DRY_RUN" = false ]; then
        print_warning "Type 'DEPLOY' to confirm: "
        read -r confirmation
        if [ "$confirmation" != "DEPLOY" ]; then
            print_info "Deployment cancelled"
            exit 0
        fi
    fi
    
    if [ "$ROLLBACK" = true ]; then
        print_info "Rolling back production deployment..."
        if [ "$DRY_RUN" = true ]; then
            print_info "[DRY-RUN] Would run: helm rollback novasight -n novasight-prod"
        else
            helm rollback novasight -n novasight-prod
        fi
        print_success "Rollback completed"
        exit 0
    fi
    
    # Run pre-deployment tests
    run_tests
    
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would run Helm deployment to production"
        helm upgrade --install novasight "$PROJECT_ROOT/helm/novasight" \
            -n novasight-prod \
            -f "$PROJECT_ROOT/helm/novasight/values-production.yaml" \
            --set backend.image.tag="$VERSION" \
            --set frontend.image.tag="$VERSION" \
            --dry-run
    else
        # Create namespace if not exists
        kubectl create namespace novasight-prod --dry-run=client -o yaml | kubectl apply -f -
        
        # Deploy with Helm - blue-green strategy
        print_info "Performing blue-green deployment..."
        
        helm upgrade --install novasight "$PROJECT_ROOT/helm/novasight" \
            -n novasight-prod \
            -f "$PROJECT_ROOT/helm/novasight/values-production.yaml" \
            --set backend.image.tag="$VERSION" \
            --set frontend.image.tag="$VERSION" \
            --wait --timeout=15m
    fi
    
    print_success "🎉 Production deployment completed!"
    
    print_info ""
    print_info "Verifying deployment..."
    kubectl get pods -n novasight-prod
    
    print_info ""
    print_info "Post-deployment checklist:"
    print_info "  [ ] Verify application health at https://novasight.io/health"
    print_info "  [ ] Check error rates in Grafana"
    print_info "  [ ] Verify key user flows"
    print_info "  [ ] Monitor for 15 minutes before closing deployment"
}

# ============================================
# Parse Arguments
# ============================================
parse_args() {
    for arg in "$@"; do
        case $arg in
            dev|test|staging|production)
                ENVIRONMENT="$arg"
                ;;
            --build)
                BUILD=true
                ;;
            --clean)
                CLEAN=true
                ;;
            --skip-tests)
                SKIP_TESTS=true
                ;;
            --no-ollama)
                NO_OLLAMA=true
                ;;
            --no-airflow)
                NO_AIRFLOW=true
                ;;
            --monitoring)
                MONITORING=true
                ;;
            --dry-run)
                DRY_RUN=true
                ;;
            --verbose)
                VERBOSE=true
                ;;
            --rollback)
                ROLLBACK=true
                ;;
            --version=*)
                VERSION="${arg#*=}"
                ;;
            --help|-h)
                show_help
                ;;
            *)
                print_warning "Unknown option: $arg"
                ;;
        esac
    done
}

# ============================================
# Main Entry Point
# ============================================
main() {
    print_banner
    parse_args "$@"
    
    verbose "Environment: $ENVIRONMENT"
    verbose "Build: $BUILD"
    verbose "Clean: $CLEAN"
    verbose "Version: $VERSION"
    verbose "Dry Run: $DRY_RUN"
    
    check_prerequisites
    check_env_file
    
    case $ENVIRONMENT in
        dev)
            deploy_development
            ;;
        test)
            deploy_test
            ;;
        staging)
            deploy_staging
            ;;
        production)
            deploy_production
            ;;
        *)
            print_error "Unknown environment: $ENVIRONMENT"
            exit 1
            ;;
    esac
    
    echo ""
    print_success "Deployment process completed!"
}

# Run main
main "$@"
