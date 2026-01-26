# 048 - Developer Documentation

## Metadata

```yaml
prompt_id: "048"
phase: 6
agent: "@orchestrator"
model: "opus 4.5"
priority: P1
estimated_effort: "2 days"
dependencies: ["all previous"]
```

## Objective

Create comprehensive developer documentation for contributing to and extending NovaSight.

## Task Description

Write developer-focused documentation covering architecture, setup, and contribution guidelines.

## Requirements

### Architecture Overview

```markdown
<!-- docs/developer/architecture.md -->
# Architecture Overview

NovaSight is a multi-tenant SaaS platform for self-service business intelligence.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend                                 │
│                    React + TypeScript                           │
│                    (Vite, Shadcn/UI)                           │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTPS
┌─────────────────────────┴───────────────────────────────────────┐
│                    API Gateway / Load Balancer                   │
│                        (NGINX / K8s Ingress)                    │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                      Backend Services                            │
│                    Flask + Python 3.11                          │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│  │   Auth     │ │ DataSource │ │  Semantic  │ │  Dashboard │   │
│  │  Service   │ │  Service   │ │   Layer    │ │  Service   │   │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘   │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐                   │
│  │   Query    │ │  Template  │ │   Admin    │                   │
│  │  Service   │ │   Engine   │ │  Service   │                   │
│  └────────────┘ └────────────┘ └────────────┘                   │
└─────────┬─────────────┬─────────────┬───────────────────────────┘
          │             │             │
┌─────────┴───┐ ┌───────┴───┐ ┌───────┴───────┐
│  PostgreSQL │ │ ClickHouse│ │     Redis     │
│  (Metadata) │ │  (OLAP)   │ │   (Cache)     │
└─────────────┘ └───────────┘ └───────────────┘
          │             
┌─────────┴─────────────────────┐ ┌────────────────────┐
│         Apache Airflow        │ │       Ollama       │
│      (Workflow Orchestration) │ │    (NL-to-SQL)     │
└───────────────────────────────┘ └────────────────────┘
```

## Key Components

### Frontend (React + TypeScript)

- **Framework**: Vite for fast development
- **UI Library**: Shadcn/UI (Tailwind-based)
- **State Management**: Zustand
- **Data Fetching**: TanStack Query
- **Routing**: TanStack Router

### Backend (Flask + Python)

- **Web Framework**: Flask with Blueprints
- **ORM**: SQLAlchemy
- **Validation**: Pydantic
- **Authentication**: Flask-JWT-Extended
- **API Documentation**: Flask-RESTX

### Data Layer

- **PostgreSQL**: Tenant metadata, users, configurations
- **ClickHouse**: OLAP queries, analytics data
- **Redis**: Session cache, rate limiting

### Data Processing

- **Apache Airflow**: Workflow orchestration
- **PySpark**: Large-scale data ingestion
- **dbt**: SQL transformations

### AI/ML

- **Ollama**: Local LLM for NL-to-SQL
- **Model**: CodeLlama 13B

## Multi-Tenancy Model

NovaSight uses a hybrid multi-tenancy approach:

| Layer | Isolation Strategy |
|-------|-------------------|
| PostgreSQL | Schema-per-tenant |
| ClickHouse | Database-per-tenant |
| Redis | Key prefix per tenant |
| Airflow | Namespace per tenant |

## Template Engine (ADR-002)

**Critical**: NovaSight does NOT generate arbitrary code. All code generation uses pre-approved Jinja2 templates.

```
User Request → LLM → Parameters → Template Engine → Validated Code
                ↑                         ↓
            Parameters Only        Pre-approved Templates
```

See [Architecture Decision Records](./adr/) for detailed rationale.
```

### Local Development Setup

```markdown
<!-- docs/developer/setup.md -->
# Local Development Setup

This guide will help you set up NovaSight for local development.

## Prerequisites

- **Python 3.11+**
- **Node.js 20+**
- **Docker & Docker Compose**
- **Git**

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/novasight/novasight.git
cd novasight
```

### 2. Start Infrastructure

```bash
docker compose -f docker-compose.dev.yml up -d
```

This starts:
- PostgreSQL (port 5432)
- ClickHouse (port 8123)
- Redis (port 6379)
- Ollama (port 11434)

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set up environment
cp .env.example .env
# Edit .env with your settings

# Run migrations
flask db upgrade

# Seed development data
flask seed dev

# Start the server
flask run --reload
```

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 5. Verify Setup

- Frontend: http://localhost:5173
- Backend API: http://localhost:5000/api/v1
- API Docs: http://localhost:5000/api/v1/docs

Login with:
- Email: `admin@dev.novasight.io`
- Password: `DevPassword123!`

## Development Workflow

### Running Tests

```bash
# Backend tests
cd backend
pytest                          # All tests
pytest tests/unit              # Unit tests only
pytest -k "test_auth"          # Pattern matching
pytest --cov=app               # With coverage

# Frontend tests
cd frontend
npm run test                   # All tests
npm run test:watch            # Watch mode
```

### Code Quality

```bash
# Backend
ruff check backend/           # Linting
black backend/                # Formatting
mypy backend/app              # Type checking

# Frontend
npm run lint                  # ESLint
npm run type-check           # TypeScript
npm run format               # Prettier
```

### Database Migrations

```bash
cd backend

# Create migration
flask db migrate -m "Add new table"

# Apply migrations
flask db upgrade

# Rollback
flask db downgrade
```

## Project Structure

```
novasight/
├── backend/
│   ├── app/
│   │   ├── api/              # API endpoints
│   │   ├── models/           # SQLAlchemy models
│   │   ├── services/         # Business logic
│   │   ├── connectors/       # Data source connectors
│   │   ├── templates/        # Jinja2 code templates
│   │   └── utils/            # Utilities
│   ├── migrations/           # Alembic migrations
│   └── tests/                # Test suite
│
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/           # Page components
│   │   ├── hooks/           # Custom hooks
│   │   ├── stores/          # Zustand stores
│   │   └── api/             # API client
│   └── e2e/                 # Playwright tests
│
├── airflow/
│   └── dags/                # Airflow DAGs
│
├── dbt/
│   └── models/              # dbt models
│
├── k8s/                     # Kubernetes manifests
├── helm/                    # Helm charts
└── docs/                    # Documentation
```

## Troubleshooting

### Port Already in Use

```bash
# Find process
lsof -i :5000

# Kill process
kill -9 <PID>
```

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker compose ps

# Restart PostgreSQL
docker compose restart postgres
```

### Ollama Model Not Found

```bash
# Pull the model
docker compose exec ollama ollama pull codellama:13b
```
```

### Contributing Guide

```markdown
<!-- docs/developer/contributing.md -->
# Contributing to NovaSight

Thank you for your interest in contributing to NovaSight! 

## Code of Conduct

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

## Getting Started

1. Fork the repository
2. Clone your fork
3. Set up local development (see [Setup Guide](./setup.md))
4. Create a feature branch

## Development Process

### 1. Pick an Issue

- Browse [open issues](https://github.com/novasight/novasight/issues)
- Comment that you're working on it
- Ask questions if unclear

### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 3. Make Changes

- Follow code style guidelines
- Write tests for new functionality
- Update documentation as needed

### 4. Test Your Changes

```bash
# Run all tests
make test

# Run linting
make lint
```

### 5. Commit Your Changes

We use [Conventional Commits](https://conventionalcommits.org/):

```bash
git commit -m "feat(dashboard): add drag-and-drop widget reordering"
git commit -m "fix(auth): handle expired refresh tokens"
git commit -m "docs(api): add query endpoint examples"
```

Prefixes:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Tests
- `chore`: Maintenance

### 6. Submit a Pull Request

- Push your branch
- Open a PR against `develop`
- Fill out the PR template
- Wait for review

## Code Style

### Python

- Follow PEP 8
- Use type hints
- Max line length: 100 characters
- Use Ruff for linting
- Use Black for formatting

```python
from typing import Optional, List

def process_data(
    data: List[dict],
    filter_key: Optional[str] = None,
) -> List[dict]:
    """
    Process data with optional filtering.
    
    Args:
        data: List of data dictionaries
        filter_key: Optional key to filter by
        
    Returns:
        Processed data list
    """
    if filter_key:
        data = [d for d in data if filter_key in d]
    return data
```

### TypeScript

- Use TypeScript strict mode
- Prefer functional components
- Use named exports

```typescript
interface DashboardProps {
  id: string;
  title: string;
  widgets: Widget[];
}

export function Dashboard({ id, title, widgets }: DashboardProps) {
  return (
    <div className="dashboard">
      <h1>{title}</h1>
      {widgets.map((widget) => (
        <Widget key={widget.id} {...widget} />
      ))}
    </div>
  );
}
```

## Architecture Guidelines

### Template Engine Rules (ADR-002)

**Never** generate code directly. Always use templates:

```python
# ❌ Bad
def generate_sql(table_name: str) -> str:
    return f"SELECT * FROM {table_name}"

# ✅ Good
def generate_sql(table_name: str) -> str:
    return template_engine.render(
        'select_all.sql.j2',
        {'table_name': table_name}
    )
```

### Multi-Tenancy

Always scope data access:

```python
# ❌ Bad
def get_dashboards() -> List[Dashboard]:
    return Dashboard.query.all()

# ✅ Good
def get_dashboards(tenant_id: str) -> List[Dashboard]:
    return Dashboard.query.filter_by(tenant_id=tenant_id).all()
```

## Questions?

- Open a [Discussion](https://github.com/novasight/novasight/discussions)
- Join our [Discord](https://discord.gg/novasight)
- Email: developers@novasight.io
```

## Expected Output

```
docs/developer/
├── README.md
├── architecture.md
├── setup.md
├── contributing.md
├── coding-standards.md
├── testing-guide.md
├── adr/
│   ├── 001-multi-tenancy.md
│   ├── 002-template-engine.md
│   ├── 003-olap-choice.md
│   ├── 004-nl-to-sql.md
│   └── 005-workflow-orchestration.md
└── deployment/
    ├── kubernetes.md
    ├── helm.md
    └── monitoring.md
```

## Acceptance Criteria

- [ ] Architecture clearly documented
- [ ] Setup guide works end-to-end
- [ ] Contributing guide complete
- [ ] ADRs linked and explained
- [ ] Code style documented
- [ ] Testing guide included
- [ ] Deployment docs complete
- [ ] Troubleshooting section

## Reference Documents

- [Orchestrator Agent](../agents/novasight-orchestrator.agent.md)
- [Architecture Decisions](../../docs/requirements/Architecture_Decisions.md)
