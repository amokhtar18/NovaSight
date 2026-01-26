@echo off
REM ============================================
REM NovaSight Development Startup Script (Windows)
REM ============================================
REM This script starts all NovaSight services in development mode
REM
REM Usage: scripts\start-dev.bat [options]
REM
REM Options:
REM   --no-spark    Skip Spark cluster
REM   --no-ollama   Skip Ollama LLM
REM   --build       Force rebuild containers
REM   --clean       Remove volumes and start fresh

setlocal enabledelayedexpansion

echo ============================================
echo NovaSight Development Environment
echo ============================================

REM Parse arguments
set NO_SPARK=false
set NO_OLLAMA=false
set BUILD=false
set CLEAN=false

:parse_args
if "%~1"=="" goto :end_parse
if "%~1"=="--no-spark" set NO_SPARK=true
if "%~1"=="--no-ollama" set NO_OLLAMA=true
if "%~1"=="--build" set BUILD=true
if "%~1"=="--clean" set CLEAN=true
shift
goto :parse_args
:end_parse

REM Check for .env file
if not exist .env (
    echo No .env file found. Creating from .env.example...
    copy .env.example .env
    echo .env file created. Please review and update values.
)

REM Clean start if requested
if "%CLEAN%"=="true" (
    echo Cleaning up existing containers and volumes...
    docker-compose down -v
    echo Cleanup complete!
)

REM Set build flag
set BUILD_FLAG=
if "%BUILD%"=="true" (
    set BUILD_FLAG=--build
    echo Forcing container rebuild...
)

echo.
echo Starting infrastructure services...
docker-compose up -d postgres redis clickhouse %BUILD_FLAG%

echo Waiting for databases to be healthy...
timeout /t 5 /nobreak > nul

echo Starting Airflow services...
docker-compose up -d airflow-postgres airflow-init
timeout /t 10 /nobreak > nul
docker-compose up -d airflow-webserver airflow-scheduler %BUILD_FLAG%

if "%NO_SPARK%"=="false" (
    echo Starting Spark cluster...
    docker-compose up -d spark-master spark-worker-1 spark-worker-2
)

if "%NO_OLLAMA%"=="false" (
    echo Starting Ollama LLM...
    docker-compose up -d ollama
)

echo Starting NovaSight backend...
docker-compose up -d backend %BUILD_FLAG%

echo Starting NovaSight frontend...
docker-compose up -d frontend %BUILD_FLAG%

echo.
echo Waiting for all services to be healthy...
timeout /t 10 /nobreak > nul

REM Check service health
echo.
echo ============================================
echo Service Status
echo ============================================
docker-compose ps

echo.
echo ============================================
echo NovaSight is ready!
echo ============================================
echo.
echo Access the following services:
echo.
echo   Frontend:        http://localhost:5173
echo   Backend API:     http://localhost:5000
echo   Airflow UI:      http://localhost:8080  (airflow/airflow)
echo   Spark Master:    http://localhost:8081
echo   ClickHouse:      http://localhost:8123
echo   PostgreSQL:      localhost:5432
echo   Redis:           localhost:6379
if "%NO_OLLAMA%"=="false" echo   Ollama:          http://localhost:11434
echo.
echo Default credentials:
echo   - NovaSight: admin@novasight.dev / admin123
echo   - Airflow:   airflow / airflow
echo.
echo Useful commands:
echo   - View logs:     docker-compose logs -f [service]
echo   - Stop all:      docker-compose down
echo   - Restart:       docker-compose restart [service]
echo.

endlocal
