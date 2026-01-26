# 001 - Initialize Infrastructure

## Metadata

```yaml
prompt_id: "001"
phase: 1
agent: "@infrastructure"
model: "sonnet 4.5"
priority: P0
estimated_effort: "2 days"
dependencies: []
```

## Objective

Set up the complete Docker Compose development environment for NovaSight with all required services.

## Task Description

Create a Docker Compose configuration that includes:

1. **PostgreSQL** - Metadata store (multi-tenant schemas)
2. **ClickHouse** - OLAP data warehouse
3. **Redis** - Caching and session management
4. **Apache Airflow** - Workflow orchestration (webserver, scheduler, worker)
5. **Ollama** - Local LLM runtime
6. **Backend** - Flask API container (dev mode with hot reload)
7. **Frontend** - React/Vite container (dev mode with HMR)

## Requirements

### Services Configuration

```yaml
services:
  postgres:
    image: postgres:15
    ports: ["5432:5432"]
    volumes: [postgres_data:/var/lib/postgresql/data]
    environment:
      POSTGRES_DB: novasight
      POSTGRES_USER: novasight
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    healthcheck: pg_isready
    
  clickhouse:
    image: clickhouse/clickhouse-server:23.8
    ports: ["8123:8123", "9000:9000"]
    volumes: [clickhouse_data:/var/lib/clickhouse]
    
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    
  airflow-webserver:
    image: apache/airflow:2.7.0
    depends_on: [postgres, redis]
    ports: ["8080:8080"]
    
  airflow-scheduler:
    image: apache/airflow:2.7.0
    depends_on: [airflow-webserver]
    
  airflow-worker:
    image: apache/airflow:2.7.0
    depends_on: [airflow-scheduler]
    
  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes: [ollama_models:/root/.ollama]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Network Configuration

- Create `novasight-network` bridge network
- All services on same network
- Only expose necessary ports to host

### Volume Mounts

- `postgres_data` - PostgreSQL persistent storage
- `clickhouse_data` - ClickHouse persistent storage
- `airflow_logs` - Airflow log files
- `ollama_models` - Downloaded LLM models
- `./backend:/app` - Backend code (hot reload)
- `./frontend:/app` - Frontend code (HMR)

### Environment Template

Create `.env.example` with all required variables.

## Expected Output

```
novasight/
├── docker-compose.yml
├── docker-compose.override.yml  # Dev overrides
├── .env.example
├── docker/
│   ├── backend/
│   │   └── Dockerfile
│   ├── frontend/
│   │   └── Dockerfile
│   └── airflow/
│       └── Dockerfile
└── scripts/
    ├── init-db.sh
    └── start-dev.sh
```

## Acceptance Criteria

- [ ] `docker-compose up` starts all services
- [ ] All services healthy within 60 seconds
- [ ] PostgreSQL accessible on localhost:5432
- [ ] ClickHouse accessible on localhost:8123
- [ ] Airflow UI accessible on localhost:8080
- [ ] Ollama API accessible on localhost:11434
- [ ] Hot reload works for backend changes
- [ ] HMR works for frontend changes

## Reference Documents

- [Infrastructure Agent](../agents/infrastructure-agent.agent.md)
- [Implementation Plan - Phase 1](../../docs/implementation/IMPLEMENTATION_PLAN.md)
