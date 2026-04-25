# NovaSight Multi-Agent Framework

This directory contains the multi-agent framework for implementing NovaSight, a self-service end-to-end BI solution.

## 📁 Directory Structure

```
.github/
├── agents/                    # Specialized implementation agents
│   ├── README.md              # Agents index
│   ├── novasight-orchestrator.agent.md
│   ├── infrastructure-agent.agent.md
│   ├── backend-agent.agent.md
│   ├── frontend-agent.agent.md
│   ├── template-engine-agent.agent.md
│   ├── orchestration-agent.agent.md
│   ├── ai-agent.agent.md
│   ├── data-sources-agent.agent.md
│   ├── ingestion-agent.agent.md       # dlt + Iceberg-on-S3 (replaces PySpark)
│   ├── dbt-agent.agent.md
│   ├── testing-agent.agent.md
│   ├── security-agent.agent.md
│   ├── admin-agent.agent.md
│   └── dashboard-agent.agent.md
│
├── skills/                    # Reusable implementation patterns
│   ├── README.md              # Skills index
│   ├── flask-api/SKILL.md
│   ├── react-components/SKILL.md
│   ├── template-engine/SKILL.md
│   ├── dlt-iceberg/SKILL.md            # tenant-isolated dlt + Iceberg
│   ├── multi-tenant-db/SKILL.md
│   └── airflow-dags/SKILL.md
│
├── prompts/
│   └── PROMPTS.md             # Implementation prompt templates
│
├── instructions/
│   ├── INSTRUCTIONS.md        # Framework usage instructions
│   └── MIGRATION_SPARK_TO_DLT.md  # Active: replace Spark with dlt + Iceberg + dbt
│
└── README.md                  # This file
```

## 🚀 Quick Start

### 1. Read the Instructions
Start by reading [INSTRUCTIONS.md](instructions/INSTRUCTIONS.md) for a complete guide on using this framework.

### 2. Check Implementation Plan
Review the [Implementation Plan](../docs/implementation/IMPLEMENTATION_PLAN.md) to understand the phases and timeline.

### 3. Start with Orchestrator
Use the orchestrator agent to begin implementation:
```
@orchestrator Initialize Phase 1 of the NovaSight implementation.
```

## 📋 Key Documents

| Document | Location | Purpose |
|----------|----------|---------|
| Instructions | [instructions/INSTRUCTIONS.md](instructions/INSTRUCTIONS.md) | How to use the framework |
| Agents Index | [agents/README.md](agents/README.md) | List of all agents |
| Skills Index | [skills/README.md](skills/README.md) | List of all skills |
| Prompts | [prompts/PROMPTS.md](prompts/PROMPTS.md) | Implementation prompts |
| BRD | [docs/requirements/](../docs/requirements/) | Business requirements |
| Architecture | [docs/requirements/Architecture_Decisions.md](../docs/requirements/Architecture_Decisions.md) | ADRs |
| Implementation Plan | [docs/implementation/](../docs/implementation/) | 24-week roadmap |

## ⚠️ Critical Rules

### Template Engine Rule (ADR-002)
**NO ARBITRARY CODE GENERATION.** All executable artifacts (dlt pipelines, Dagster ops, dbt models) must be generated from pre-approved, security-audited Jinja2 templates.

### Multi-Tenancy
- PostgreSQL: Schema-per-tenant
- ClickHouse: Database-per-tenant
- Always verify tenant context before database operations

### Security
- All inputs validated with Pydantic
- JWT authentication required
- Role-based access control (RBAC)
- Audit logging for sensitive operations

## 🏗️ Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React, TypeScript, Vite, Shadcn/UI, TanStack Query |
| Backend | Flask, SQLAlchemy, Pydantic |
| Ingestion | dlt + Apache Iceberg (per-tenant S3) |
| Orchestration | Apache Airflow |
| Data Warehouse | ClickHouse |
| Transformations | dbt |
| AI | Ollama (codellama:13b) |
| Metadata | PostgreSQL |
| Cache | Redis |

## 📊 Implementation Phases

| Phase | Weeks | Focus |
|-------|-------|-------|
| 1 | 1-4 | Infrastructure & Core |
| 2 | 5-8 | Data Sources & Ingestion |
| 3 | 9-12 | dbt & Orchestration |
| 4 | 13-16 | Templates & AI |
| 5 | 17-20 | Analytics & Dashboards |
| 6 | 21-24 | Admin & Polish |

---

*NovaSight Multi-Agent Framework v1.0*
