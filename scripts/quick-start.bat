@echo off
REM ============================================
REM NovaSight Quick Start Script (Windows)
REM ============================================
REM Minimal startup for quick testing - just the essentials
REM
REM Usage: scripts\quick-start.bat [options]
REM
REM Options:
REM   --rebuild    Force rebuild containers

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
cd /d "%PROJECT_ROOT%"

echo.
echo ================================================================
echo   NovaSight Quick Start
echo   Minimal services for rapid testing
echo ================================================================
echo.

REM Parse arguments
set "REBUILD=false"
:parse_args
if "%~1"=="" goto :end_parse
if /i "%~1"=="--rebuild" set "REBUILD=true"
shift
goto :parse_args
:end_parse

REM Check for Docker
where docker >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Docker not found. Please install Docker Desktop.
    exit /b 1
)

REM Determine compose command
docker compose version >nul 2>nul
if errorlevel 1 (
    set "COMPOSE_CMD=docker-compose"
) else (
    set "COMPOSE_CMD=docker compose"
)

REM Check/create .env
if not exist ".env" (
    if exist ".env.example" (
        echo Creating .env from .env.example...
        copy ".env.example" ".env" >nul
    )
)

set "BUILD_FLAG="
if "%REBUILD%"=="true" (
    set "BUILD_FLAG=--build"
    echo Forcing rebuild...
)

REM Start core infrastructure
echo Starting core infrastructure...
%COMPOSE_CMD% up -d postgres redis clickhouse %BUILD_FLAG%

echo Waiting for databases (10 seconds)...
timeout /t 10 /nobreak >nul

REM Start application
echo Starting application services...
%COMPOSE_CMD% up -d backend frontend %BUILD_FLAG%

echo Waiting for services to initialize (5 seconds)...
timeout /t 5 /nobreak >nul

echo.
echo ================================================================
echo   Quick Start Complete!
echo ================================================================
echo.
echo   Frontend:    http://localhost:5173
echo   Backend:     http://localhost:5000
echo   API Docs:    http://localhost:5000/api/v1/docs
echo   Dagster UI:  http://localhost:3000 (integrated with backend)
echo.
echo Default credentials:
echo   Email: admin@novasight.io
echo   Pass:  Admin123!
echo.
echo Commands:
echo   View logs:   docker compose logs -f backend frontend
echo   Stop:        docker compose down
echo   Full start:  scripts\start-dev.bat
echo.
