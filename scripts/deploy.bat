@echo off
REM ============================================
REM NovaSight Deployment Script (Windows)
REM ============================================
REM Unified deployment script for development, staging, and production
REM
REM Usage:
REM   scripts\deploy.bat [environment] [options]
REM
REM Environments:
REM   dev         Local development (default)
REM   test        Testing with integration tests
REM   staging     Kubernetes staging environment
REM   production  Production deployment (requires confirmation)
REM
REM Options:
REM   --build          Force rebuild containers
REM   --clean          Wipe containers, volumes, project images, network and build cache (full fresh start)
REM   --skip-tests     Skip running tests before deployment
REM   --no-spark       Skip Spark cluster (dev/test only) [REMOVED — Spark no longer supported]
REM
REM   --no-ollama      Skip Ollama LLM service
REM   --no-airflow     Skip Airflow orchestration (use Dagster only)
REM   --monitoring     Include monitoring stack (Prometheus, Grafana, Loki)
REM   --dry-run        Show what would be done without executing
REM   --version=TAG    Specify version tag (default: latest)
REM   --help           Show this help message

setlocal enabledelayedexpansion

REM Script directory
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
cd /d "%PROJECT_ROOT%"

REM Default values
set "ENVIRONMENT=dev"
set "BUILD=false"
set "CLEAN=false"
set "SKIP_TESTS=false"
set "NO_SPARK=true"  REM Spark removed; flag retained for backward compat (no-op)
set "NO_OLLAMA=false"
set "NO_AIRFLOW=false"
set "MONITORING=false"
set "DRY_RUN=false"
set "ROLLBACK=false"
set "VERSION=latest"

REM ============================================
REM Parse Arguments
REM ============================================
:parse_args
if "%~1"=="" goto :end_parse
if /i "%~1"=="dev" set "ENVIRONMENT=dev"
if /i "%~1"=="test" set "ENVIRONMENT=test"
if /i "%~1"=="staging" set "ENVIRONMENT=staging"
if /i "%~1"=="production" set "ENVIRONMENT=production"
if /i "%~1"=="--build" set "BUILD=true"
if /i "%~1"=="--clean" set "CLEAN=true"
if /i "%~1"=="--skip-tests" set "SKIP_TESTS=true"
if /i "%~1"=="--no-spark" set "NO_SPARK=true"  REM no-op (Spark removed)
if /i "%~1"=="--no-ollama" set "NO_OLLAMA=true"
if /i "%~1"=="--no-airflow" set "NO_AIRFLOW=true"
if /i "%~1"=="--monitoring" set "MONITORING=true"
if /i "%~1"=="--dry-run" set "DRY_RUN=true"
if /i "%~1"=="--rollback" set "ROLLBACK=true"
if /i "%~1"=="--help" goto :show_help
if /i "%~1"=="-h" goto :show_help
REM Parse --version=TAG
echo %~1 | findstr /i "^--version=" >nul && (
    for /f "tokens=2 delims==" %%a in ("%~1") do set "VERSION=%%a"
)
shift
goto :parse_args
:end_parse

REM ============================================
REM Banner
REM ============================================
echo.
echo ================================================================
echo   NovaSight Deployment
echo   Self-Service End-to-End BI Platform
echo ================================================================
echo.
echo Environment: %ENVIRONMENT%
echo Version: %VERSION%
echo Build: %BUILD%
echo Clean: %CLEAN%
echo.

REM ============================================
REM Check Prerequisites
REM ============================================
echo [STEP] Checking prerequisites...

where docker >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Docker not found. Please install Docker Desktop.
    exit /b 1
)

docker compose version >nul 2>nul
if errorlevel 1 (
    where docker-compose >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] Docker Compose not found.
        exit /b 1
    )
    set "COMPOSE_CMD=docker-compose"
) else (
    set "COMPOSE_CMD=docker compose"
)

echo [SUCCESS] Prerequisites check passed

REM ============================================
REM Check .env File
REM ============================================
echo [STEP] Checking environment configuration...

if not exist ".env" (
    if exist ".env.example" (
        echo [WARNING] No .env file found. Creating from .env.example...
        copy ".env.example" ".env" >nul
        echo [INFO] Please review .env and update secrets before production deployment
    ) else (
        echo [ERROR] No .env or .env.example file found
        exit /b 1
    )
) else (
    echo [SUCCESS] Environment file exists
)

REM ============================================
REM Route to Environment
REM ============================================
if /i "%ENVIRONMENT%"=="dev" goto :deploy_dev
if /i "%ENVIRONMENT%"=="test" goto :deploy_test
if /i "%ENVIRONMENT%"=="staging" goto :deploy_staging
if /i "%ENVIRONMENT%"=="production" goto :deploy_production
echo [ERROR] Unknown environment: %ENVIRONMENT%
exit /b 1

REM ============================================
REM Development Deployment
REM ============================================
:deploy_dev
echo.
echo [STEP] Deploying development environment...

set "BUILD_FLAG="
if "%BUILD%"=="true" set "BUILD_FLAG=--build"

if "%CLEAN%"=="true" (
    echo [INFO] Wiping containers, volumes, images, and networks for a fresh start...
    if "%DRY_RUN%"=="true" (
        echo [DRY-RUN] Would run: %COMPOSE_CMD% down -v --remove-orphans --rmi local
        echo [DRY-RUN] Would run: docker network rm novasight-network
        echo [DRY-RUN] Would run: docker builder prune -af
    ) else (
        %COMPOSE_CMD% down -v --remove-orphans --rmi local
        docker network rm novasight-network 2>nul
        docker builder prune -af >nul 2>nul
    )
)

if "%DRY_RUN%"=="true" (
    echo [DRY-RUN] Would start all services
    goto :deploy_success
)

echo [INFO] Starting infrastructure services...
%COMPOSE_CMD% up -d postgres redis clickhouse %BUILD_FLAG%

echo [INFO] Waiting for databases to be healthy...
timeout /t 10 /nobreak >nul

if "%NO_AIRFLOW%"=="false" (
    %COMPOSE_CMD% config --services | findstr /i /x "airflow-postgres" >nul
    if errorlevel 1 (
        echo [INFO] Airflow services not defined in compose config. Skipping Airflow startup.
    ) else (
        echo [INFO] Starting Airflow 3.x services...
        %COMPOSE_CMD% up -d airflow-postgres airflow-init
        timeout /t 15 /nobreak >nul
        echo [INFO] Starting Airflow API Server, DAG Processor, Scheduler, and Triggerer...
        %COMPOSE_CMD% up -d airflow-api-server airflow-dag-processor airflow-scheduler airflow-triggerer
    )
) else (
    echo [INFO] Skipping Airflow (--no-airflow flag set)
)

if "%NO_OLLAMA%"=="false" (
    echo [INFO] Starting Ollama...
    %COMPOSE_CMD% up -d ollama
)

echo [INFO] Starting application services (with integrated Dagster)...
%COMPOSE_CMD% up -d backend frontend %BUILD_FLAG%

if "%MONITORING%"=="true" (
    echo [INFO] Starting monitoring stack ^(Prometheus, Grafana, Loki^)...
    %COMPOSE_CMD% -f docker-compose.yml -f docker-compose.logging.yml up -d prometheus grafana loki promtail 2>nul
    if errorlevel 1 echo [WARN] Monitoring services not found in compose files. Skipping...
)

echo.
echo [SUCCESS] Development environment deployed!
echo.
echo Services available at:
echo   Frontend:     http://localhost:5173
echo   Backend API:  http://localhost:5000
echo   API Docs:     http://localhost:5000/api/v1/docs
echo   Dagster UI:   http://localhost:3000
echo   Airflow UI:   http://localhost:8080 ^(airflow/airflow^)
echo   ClickHouse:   http://localhost:8123
echo   Ollama:       http://localhost:11434
echo.
echo Default credentials:
echo   NovaSight:   admin@novasight.io / Admin123!
echo   Airflow:     airflow / airflow
goto :deploy_success

REM ============================================
REM Test Deployment
REM ============================================
:deploy_test
echo.
echo [STEP] Setting up test environment...

if "%DRY_RUN%"=="true" (
    echo [DRY-RUN] Would run test containers
    goto :deploy_success
)

echo [INFO] Starting test infrastructure...
%COMPOSE_CMD% -f docker-compose.test.yml up -d

echo [INFO] Waiting for services to be healthy...
timeout /t 15 /nobreak >nul

echo [INFO] Running backend tests...
%COMPOSE_CMD% -f docker-compose.test.yml exec -T backend pytest -v --tb=short
if errorlevel 1 (
    echo [ERROR] Backend tests failed
    %COMPOSE_CMD% -f docker-compose.test.yml down -v
    exit /b 1
)

echo [INFO] Running frontend tests...
%COMPOSE_CMD% -f docker-compose.test.yml exec -T frontend npm test -- --run
if errorlevel 1 echo [WARNING] Frontend tests failed or skipped

echo [INFO] Cleaning up test environment...
%COMPOSE_CMD% -f docker-compose.test.yml down -v

echo [SUCCESS] Test deployment completed!
goto :deploy_success

REM ============================================
REM Staging Deployment
REM ============================================
:deploy_staging
echo.
echo [STEP] Deploying to Kubernetes staging...

where kubectl >nul 2>nul
if errorlevel 1 (
    echo [ERROR] kubectl not found. Please install kubectl.
    exit /b 1
)

where helm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Helm not found. Please install Helm.
    exit /b 1
)

if "%ROLLBACK%"=="true" (
    echo [INFO] Rolling back staging deployment...
    if "%DRY_RUN%"=="true" (
        echo [DRY-RUN] Would run: helm rollback novasight -n novasight-staging
    ) else (
        helm rollback novasight -n novasight-staging
    )
    echo [SUCCESS] Rollback completed
    goto :deploy_success
)

if "%DRY_RUN%"=="true" (
    echo [DRY-RUN] Would run Helm deployment to staging
    helm upgrade --install novasight "%PROJECT_ROOT%\helm\novasight" ^
        -n novasight-staging ^
        -f "%PROJECT_ROOT%\helm\novasight\values-staging.yaml" ^
        --set backend.image.tag=%VERSION% ^
        --set frontend.image.tag=%VERSION% ^
        --dry-run
) else (
    kubectl create namespace novasight-staging --dry-run=client -o yaml | kubectl apply -f -
    
    helm upgrade --install novasight "%PROJECT_ROOT%\helm\novasight" ^
        -n novasight-staging ^
        -f "%PROJECT_ROOT%\helm\novasight\values-staging.yaml" ^
        --set backend.image.tag=%VERSION% ^
        --set frontend.image.tag=%VERSION% ^
        --wait --timeout=10m
)

echo [SUCCESS] Staging deployment completed!
kubectl get pods -n novasight-staging
goto :deploy_success

REM ============================================
REM Production Deployment
REM ============================================
:deploy_production
echo.
echo ================================================================
echo   WARNING: PRODUCTION DEPLOYMENT
echo ================================================================
echo.
echo You are about to deploy to PRODUCTION
echo Version: %VERSION%
echo.

where kubectl >nul 2>nul
if errorlevel 1 (
    echo [ERROR] kubectl not found. Please install kubectl.
    exit /b 1
)

where helm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Helm not found. Please install Helm.
    exit /b 1
)

if "%DRY_RUN%"=="false" (
    set /p "CONFIRM=Type 'DEPLOY' to confirm: "
    if /i not "!CONFIRM!"=="DEPLOY" (
        echo [INFO] Deployment cancelled
        exit /b 0
    )
)

if "%ROLLBACK%"=="true" (
    echo [INFO] Rolling back production deployment...
    if "%DRY_RUN%"=="true" (
        echo [DRY-RUN] Would run: helm rollback novasight -n novasight-prod
    ) else (
        helm rollback novasight -n novasight-prod
    )
    echo [SUCCESS] Rollback completed
    goto :deploy_success
)

if "%SKIP_TESTS%"=="false" (
    echo [STEP] Running pre-deployment tests...
    call "%SCRIPT_DIR%run-all-tests.bat"
    if errorlevel 1 (
        echo [ERROR] Tests failed. Aborting deployment.
        exit /b 1
    )
)

if "%DRY_RUN%"=="true" (
    echo [DRY-RUN] Would run Helm deployment to production
    helm upgrade --install novasight "%PROJECT_ROOT%\helm\novasight" ^
        -n novasight-prod ^
        -f "%PROJECT_ROOT%\helm\novasight\values-production.yaml" ^
        --set backend.image.tag=%VERSION% ^
        --set frontend.image.tag=%VERSION% ^
        --dry-run
) else (
    kubectl create namespace novasight-prod --dry-run=client -o yaml | kubectl apply -f -
    
    helm upgrade --install novasight "%PROJECT_ROOT%\helm\novasight" ^
        -n novasight-prod ^
        -f "%PROJECT_ROOT%\helm\novasight\values-production.yaml" ^
        --set backend.image.tag=%VERSION% ^
        --set frontend.image.tag=%VERSION% ^
        --wait --timeout=15m
)

echo.
echo [SUCCESS] Production deployment completed!
kubectl get pods -n novasight-prod
echo.
echo Post-deployment checklist:
echo   [ ] Verify application health at https://novasight.io/health
echo   [ ] Check error rates in Grafana
echo   [ ] Verify key user flows
echo   [ ] Monitor for 15 minutes before closing deployment
goto :deploy_success

REM ============================================
REM Show Help
REM ============================================
:show_help
echo NovaSight Deployment Script
echo.
echo Usage: %~nx0 [environment] [options]
echo.
echo Environments:
echo   dev         Local development with Docker Compose (default)
echo   test        Run integration tests in containers
echo   staging     Deploy to Kubernetes staging
echo   production  Deploy to Kubernetes production
echo.
echo Options:
echo   --build          Force rebuild containers
echo   --clean          Remove volumes and start fresh
echo   --skip-tests     Skip running tests before deployment
echo   --no-spark       (deprecated, no-op) Spark cluster has been removed
echo   --no-ollama      Skip Ollama LLM service
echo   --no-airflow     Skip Airflow (use Dagster only)
echo   --monitoring     Include monitoring stack (Prometheus, Grafana, Loki)
echo   --dry-run        Show what would be done without executing
echo   --rollback       Rollback to previous deployment (k8s only)
echo   --version=TAG    Specify version tag (default: latest)
echo   --help           Show this help message
echo.
echo Examples:
echo   %~nx0 dev --build             # Development with rebuild
echo   %~nx0 dev --monitoring        # Development with monitoring stack
echo   %~nx0 test                    # Run integration tests
echo   %~nx0 staging --version=v1.2  # Deploy v1.2 to staging
echo   %~nx0 production              # Production deployment
exit /b 0

REM ============================================
REM Success Exit
REM ============================================
:deploy_success
echo.
echo [SUCCESS] Deployment process completed!
exit /b 0
