@echo off
REM ============================================
REM NovaSight Health Check Script (Windows)
REM ============================================
REM Comprehensive health check for all NovaSight services
REM
REM Usage: scripts\health-check.bat

setlocal enabledelayedexpansion

echo.
echo NovaSight Health Check
echo ========================================
echo.

set "HEALTHY=0"
set "UNHEALTHY=0"

REM Check PostgreSQL (using Docker)
docker exec novasight-postgres pg_isready -U novasight -d novasight_platform >nul 2>nul
if %errorlevel%==0 (
    echo   [OK] PostgreSQL is healthy
    set /a HEALTHY+=1
) else (
    echo   [FAIL] PostgreSQL is not responding
    set /a UNHEALTHY+=1
)

REM Check Redis (using Docker)
docker exec novasight-redis redis-cli ping >nul 2>nul
if %errorlevel%==0 (
    echo   [OK] Redis is healthy
    set /a HEALTHY+=1
) else (
    echo   [FAIL] Redis is not responding
    set /a UNHEALTHY+=1
)

REM Check Backend
curl -s -o nul -w "" --connect-timeout 2 http://localhost:5000/health 2>nul
if %errorlevel%==0 (
    echo   [OK] Backend API is healthy
    set /a HEALTHY+=1
) else (
    echo   [FAIL] Backend API is not responding
    set /a UNHEALTHY+=1
)

REM Check Frontend
curl -s -o nul -w "" --connect-timeout 2 http://localhost:5173 2>nul
if %errorlevel%==0 (
    echo   [OK] Frontend is healthy
    set /a HEALTHY+=1
) else (
    echo   [FAIL] Frontend is not responding
    set /a UNHEALTHY+=1
)

REM Check ClickHouse
curl -s -o nul -w "" --connect-timeout 2 http://localhost:8123/ping 2>nul
if %errorlevel%==0 (
    echo   [OK] ClickHouse is healthy
    set /a HEALTHY+=1
) else (
    echo   [FAIL] ClickHouse is not responding
    set /a UNHEALTHY+=1
)

REM Check Airflow 3.x API Server
curl -s -o nul -w "" --connect-timeout 2 http://localhost:8080/api/v2/version 2>nul
if %errorlevel%==0 (
    echo   [OK] Airflow API Server is healthy
    set /a HEALTHY+=1
) else (
    echo   [WARN] Airflow API Server is not responding (may be disabled)
    set /a UNHEALTHY+=1
)

REM Check Dagster
curl -s -o nul -w "" --connect-timeout 2 http://localhost:3000/server_info 2>nul
if %errorlevel%==0 (
    echo   [OK] Dagster is healthy
    set /a HEALTHY+=1
) else (
    echo   [WARN] Dagster is not responding (may be disabled)
    set /a UNHEALTHY+=1
)

REM Check MinIO (S3 / Iceberg lake)
curl -s -o nul -w "" --connect-timeout 2 http://localhost:9001/minio/health/live 2>nul
if %errorlevel%==0 (
    echo   [OK] MinIO (S3 / Iceberg lake) is healthy
    set /a HEALTHY+=1
) else (
    echo   [WARN] MinIO is not responding (may be disabled)
    set /a UNHEALTHY+=1
)

REM Check Ollama
curl -s -o nul -w "" --connect-timeout 2 http://localhost:11434/api/tags 2>nul
if %errorlevel%==0 (
    echo   [OK] Ollama is healthy
    set /a HEALTHY+=1
) else (
    echo   [WARN] Ollama is not responding (may be disabled)
    set /a UNHEALTHY+=1
)

echo.
echo ========================================
echo Summary: !HEALTHY! healthy, !UNHEALTHY! unhealthy
echo.

if !UNHEALTHY! GTR 0 exit /b 1
exit /b 0
