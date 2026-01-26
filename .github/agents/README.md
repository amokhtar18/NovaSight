# NovaSight Agents Index

This document provides an index of all specialized agents in the NovaSight multi-agent framework.

---

## 🎯 Agent Overview

| Agent | Purpose | Primary Use Cases |
|-------|---------|-------------------|
| [Orchestrator](#orchestrator) | Master coordinator | Phase management, delegation, status tracking |
| [Infrastructure](#infrastructure) | DevOps & deployment | Docker, databases, networking |
| [Backend](#backend) | Flask API development | REST APIs, services, models |
| [Frontend](#frontend) | React UI development | Components, pages, state |
| [Template Engine](#template-engine) | Code generation | PySpark, DAGs, dbt models |
| [Orchestration](#orchestration) | Airflow DAGs | Pipeline scheduling, monitoring |
| [AI](#ai) | LLM integration | NL to SQL, query assistance |
| [Data Sources](#data-sources) | Database connections | Connection CRUD, introspection |
| [dbt](#dbt) | Semantic layer | Model builder, lineage |
| [Dashboard](#dashboard) | Analytics & visualization | Charts, dashboards, SQL editor |
| [Admin](#admin) | Tenant management | Users, roles, quotas |
| [Security](#security) | Security hardening | Auth, validation, audit |
| [Testing](#testing) | Quality assurance | Unit, integration, E2E tests |

---

## 📁 Agent Files

### Orchestrator
**File:** `novasight-orchestrator.agent.md`

Master orchestrator that coordinates the overall implementation across all phases and agents.

**Key Responsibilities:**
- Phase management and tracking
- Cross-agent task coordination
- Implementation status reporting
- Dependency resolution

**When to Use:**
- Starting a new implementation phase
- Getting overall project status
- Coordinating multi-component features

---

### Infrastructure
**File:** `infrastructure-agent.agent.md`

Handles all infrastructure and DevOps concerns.

**Key Responsibilities:**
- Docker Compose configuration
- Database setup (PostgreSQL, ClickHouse)
- Service configuration (Airflow, Redis, Ollama)
- Network and volume management

**When to Use:**
- Setting up development environment
- Configuring production deployment
- Troubleshooting infrastructure issues

---

### Backend
**File:** `backend-agent.agent.md`

Implements Flask REST APIs and business logic.

**Key Responsibilities:**
- Flask application structure
- REST API endpoints
- Service layer implementation
- SQLAlchemy models
- Authentication/authorization

**When to Use:**
- Creating API endpoints
- Implementing business services
- Database model design

---

### Frontend
**File:** `frontend-agent.agent.md`

Builds React user interface components.

**Key Responsibilities:**
- React component development
- Page and layout creation
- Form handling with validation
- State management (Zustand, TanStack Query)
- Shadcn/UI integration

**When to Use:**
- Creating UI components
- Building pages
- Implementing forms

---

### Template Engine
**File:** `template-engine-agent.agent.md`

Manages secure code generation from templates.

**Key Responsibilities:**
- Jinja2 template management
- Pydantic validation schemas
- Artifact generation (PySpark, DAGs, dbt)
- Security validation

**⚠️ CRITICAL:** Enforces Template Engine Rule - no arbitrary code generation.

**When to Use:**
- Generating PySpark jobs
- Creating Airflow DAGs
- Building dbt models

---

### Orchestration
**File:** `orchestration-agent.agent.md`

Handles Airflow DAG creation and management.

**Key Responsibilities:**
- DAG configuration API
- Airflow REST integration
- Visual DAG builder (ReactFlow)
- Pipeline monitoring

**When to Use:**
- Creating pipeline DAGs
- Scheduling jobs
- Monitoring executions

---

### AI
**File:** `ai-agent.agent.md`

Integrates Ollama for natural language processing.

**Key Responsibilities:**
- Ollama client integration
- Prompt building with schema context
- SQL validation
- RLS filter injection

**When to Use:**
- Implementing query assistant
- Natural language to SQL
- AI-powered suggestions

---

### Data Sources
**File:** `data-sources-agent.agent.md`

Manages database connections and schema introspection.

**Key Responsibilities:**
- Connection CRUD
- Credential encryption
- Schema introspection (PostgreSQL, Oracle, SQL Server)
- Connection testing

**When to Use:**
- Adding data source support
- Schema browsing features
- Connection management

---

### dbt
**File:** `dbt-agent.agent.md`

Implements the semantic layer with dbt.

**Key Responsibilities:**
- dbt project management
- Model configuration
- Join builder
- Lineage extraction
- Test configuration

**When to Use:**
- Building semantic models
- Creating transformations
- Lineage visualization

---

### Dashboard
**File:** `dashboard-agent.agent.md`

Creates analytics and visualization features.

**Key Responsibilities:**
- SQL query execution
- Chart configuration
- Dashboard canvas
- Widget management
- Export functionality

**When to Use:**
- Building charts
- Creating dashboards
- SQL editor features

---

### Admin
**File:** `admin-agent.agent.md`

Handles tenant and user administration.

**Key Responsibilities:**
- Tenant CRUD
- User management
- Role and permission management
- Quota management
- Audit log viewing

**When to Use:**
- Admin panel features
- User management
- RBAC implementation

---

### Security
**File:** `security-agent.agent.md`

Ensures security best practices.

**Key Responsibilities:**
- Authentication implementation
- Input validation
- SQL injection prevention
- Audit logging
- Security headers

**When to Use:**
- Security code review
- Implementing auth
- Hardening endpoints

---

### Testing
**File:** `testing-agent.agent.md`

Manages quality assurance and testing.

**Key Responsibilities:**
- pytest unit tests
- Vitest frontend tests
- Playwright E2E tests
- Test fixtures
- Coverage targets

**When to Use:**
- Writing tests
- Setting up test infrastructure
- Achieving coverage goals

---

## 🔗 Related Resources

- [Skills Index](../skills/README.md)
- [Prompts Collection](../prompts/PROMPTS.md)
- [Instructions](../instructions/INSTRUCTIONS.md)
- [Implementation Plan](../../docs/implementation/IMPLEMENTATION_PLAN.md)

---

*NovaSight Agents Index v1.0*
