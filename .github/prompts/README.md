# NovaSight Implementation Prompts

Prompts are organized in execution order following the 6-phase implementation plan.
All 51 prompts have been created and are ready for execution.

## 📋 Prompt Execution Order

### Phase 1: Foundation Infrastructure (Weeks 1-4)

| # | Prompt File | Agent | Model | Description |
|---|------------|-------|-------|-------------|
| 001 | [001-init-infrastructure.md](001-init-infrastructure.md) | @infrastructure | sonnet 4.5 | Docker Compose setup |
| 002 | [002-database-setup.md](002-database-setup.md) | @infrastructure | sonnet 4.5 | PostgreSQL & ClickHouse |
| 003 | [003-flask-app-structure.md](003-flask-app-structure.md) | @backend | opus 4.5 | Flask app factory |
| 004 | [004-auth-system.md](004-auth-system.md) | @security | opus 4.5 | JWT authentication |
| 005 | [005-tenant-middleware.md](005-tenant-middleware.md) | @backend | opus 4.5 | Multi-tenant middleware |
| 006 | [006-react-project.md](006-react-project.md) | @frontend | sonnet 4.5 | Vite + Shadcn/UI setup |
| 007 | [007-auth-ui.md](007-auth-ui.md) | @frontend | sonnet 4.5 | Login/auth components |

### Phase 2: Template Engine & Data Sources (Weeks 5-8)

| # | Prompt File | Agent | Model | Description |
|---|------------|-------|-------|-------------|
| 008 | [008-template-engine-core.md](008-template-engine-core.md) | @template-engine | opus 4.5 | Core template engine |
| 009 | [009-sql-templates.md](009-sql-templates.md) | @template-engine | opus 4.5 | SQL query templates |
| 010 | [010-dbt-templates.md](010-dbt-templates.md) | @template-engine | opus 4.5 | dbt model templates |
| 011 | [011-airflow-templates.md](011-airflow-templates.md) | @template-engine | opus 4.5 | Airflow DAG templates |
| 012 | [012-clickhouse-templates.md](012-clickhouse-templates.md) | @template-engine | opus 4.5 | ClickHouse DDL templates |
| 013 | [013-data-source-connectors.md](013-data-source-connectors.md) | @data-sources | sonnet 4.5 | Database connectors |
| 014 | [014-data-source-api.md](014-data-source-api.md) | @backend | opus 4.5 | Connection API endpoints |
| 015 | [015-data-source-ui.md](015-data-source-ui.md) | @frontend | sonnet 4.5 | Connection management UI |
| 016 | [016-ingestion-dag-generator.md](016-ingestion-dag-generator.md) | @orchestration | sonnet 4.5 | Ingestion DAG generation |

### Phase 3: Semantic Layer & AI Integration (Weeks 9-12)

| # | Prompt File | Agent | Model | Description |
|---|------------|-------|-------|-------------|
| 017 | [017-dbt-project-setup.md](017-dbt-project-setup.md) | @dbt | sonnet 4.5 | dbt project structure |
| 018 | [018-dbt-model-generator.md](018-dbt-model-generator.md) | @dbt | sonnet 4.5 | Model generation service |
| 019 | [019-semantic-layer-api.md](019-semantic-layer-api.md) | @backend | opus 4.5 | Semantic layer API |
| 020 | [020-semantic-layer-ui.md](020-semantic-layer-ui.md) | @frontend | sonnet 4.5 | Semantic layer UI |
| 021 | [021-transformation-dag-generator.md](021-transformation-dag-generator.md) | @orchestration | sonnet 4.5 | Transform DAG generation |
| 022 | [022-ollama-integration.md](022-ollama-integration.md) | @ai | opus 4.5 | Ollama LLM integration |
| 023 | [023-nl-to-sql.md](023-nl-to-sql.md) | @ai | opus 4.5 | Natural language to SQL |

### Phase 4: Analytics & Dashboards (Weeks 13-16)

| # | Prompt File | Agent | Model | Description |
|---|------------|-------|-------|-------------|
| 024 | [024-dashboard-api.md](024-dashboard-api.md) | @dashboard | sonnet 4.5 | Dashboard CRUD API |
| 025 | [025-dashboard-builder-ui.md](025-dashboard-builder-ui.md) | @frontend | sonnet 4.5 | Dashboard builder UI |
| 026 | [026-chart-components.md](026-chart-components.md) | @frontend | sonnet 4.5 | Recharts components |
| 027 | [027-query-interface-ui.md](027-query-interface-ui.md) | @frontend | sonnet 4.5 | SQL query interface |

### Phase 5: Administration & Security (Weeks 17-20)

| # | Prompt File | Agent | Model | Description |
|---|------------|-------|-------|-------------|
| 028 | [028-tenant-management-api.md](028-tenant-management-api.md) | @admin | haiku 4.5 | Tenant management |
| 029 | [029-user-management-api.md](029-user-management-api.md) | @admin | haiku 4.5 | User management |
| 030 | [030-admin-dashboard-ui.md](030-admin-dashboard-ui.md) | @frontend | sonnet 4.5 | Admin dashboard UI |
| 031 | [031-rbac-implementation.md](031-rbac-implementation.md) | @security | opus 4.5 | RBAC system |
| 032 | [032-audit-logging.md](032-audit-logging.md) | @security | opus 4.5 | Audit logging |
| 033 | [033-data-encryption.md](033-data-encryption.md) | @security | opus 4.5 | Data encryption |

### Phase 6: Testing, DevOps & Documentation (Weeks 21-24)

| # | Prompt File | Agent | Model | Description |
|---|------------|-------|-------|-------------|
| 034 | [034-unit-test-suite.md](034-unit-test-suite.md) | @testing | sonnet 4.5 | pytest unit tests |
| 035 | [035-integration-test-suite.md](035-integration-test-suite.md) | @testing | sonnet 4.5 | Integration tests |
| 036 | [036-e2e-test-suite.md](036-e2e-test-suite.md) | @testing | sonnet 4.5 | Playwright E2E tests |
| 037 | [037-cicd-pipeline.md](037-cicd-pipeline.md) | @infrastructure | sonnet 4.5 | CI/CD with GitHub Actions |
| 038 | [038-kubernetes-manifests.md](038-kubernetes-manifests.md) | @infrastructure | sonnet 4.5 | Kubernetes deployment |
| 039 | [039-helm-charts.md](039-helm-charts.md) | @infrastructure | sonnet 4.5 | Helm chart packaging |
| 040 | [040-monitoring-setup.md](040-monitoring-setup.md) | @infrastructure | sonnet 4.5 | Prometheus + Grafana |
| 041 | [041-logging-infrastructure.md](041-logging-infrastructure.md) | @infrastructure | sonnet 4.5 | Centralized logging |
| 042 | [042-alerting-configuration.md](042-alerting-configuration.md) | @infrastructure | sonnet 4.5 | Alertmanager setup |
| 043 | [043-backup-recovery.md](043-backup-recovery.md) | @infrastructure | sonnet 4.5 | Backup & recovery |
| 044 | [044-performance-testing.md](044-performance-testing.md) | @testing | sonnet 4.5 | k6 load testing |
| 045 | [045-security-testing.md](045-security-testing.md) | @security | opus 4.5 | Security scanning |
| 046 | [046-api-documentation.md](046-api-documentation.md) | @backend | opus 4.5 | OpenAPI documentation |
| 047 | [047-user-documentation.md](047-user-documentation.md) | @backend | opus 4.5 | User guides |
| 048 | [048-developer-documentation.md](048-developer-documentation.md) | @backend | opus 4.5 | Developer docs |
| 049 | [049-deployment-runbook.md](049-deployment-runbook.md) | @infrastructure | sonnet 4.5 | Deployment runbook |
| 050 | [050-launch-checklist.md](050-launch-checklist.md) | @security | opus 4.5 | Production launch checklist |
| 051 | [051-ui-redesign.md](051-ui-redesign.md) | @frontend | sonnet 4.5 | UI redesign & polish |

## 🚀 Usage

To execute a prompt:

```
@orchestrator Execute prompt 001-init-infrastructure.md
```

Or delegate directly:

```
[DELEGATE: @infrastructure]
Prompt: 001-init-infrastructure.md
[/DELEGATE]
```

## 📊 Model Distribution

| Model | Count | Use Cases |
|-------|-------|-----------|
| opus 4.5 | 18 | Security, AI, templates, complex backend, documentation |
| sonnet 4.5 | 31 | Frontend, infrastructure, testing, data processing, UI redesign |
| haiku 4.5 | 2 | Admin CRUD operations |

## 🎯 Agent Distribution

| Agent | Prompts | Focus Area |
|-------|---------|------------|
| @infrastructure | 9 | DevOps, K8s, CI/CD, Monitoring |
| @frontend | 9 | React UI components, UI redesign |
| @backend | 5 | Flask API services |
| @template-engine | 5 | Jinja2 templates (ADR-002) |
| @security | 6 | Auth, RBAC, Audit, Encryption |
| @testing | 4 | Unit, Integration, E2E, Performance |
| @ai | 2 | Ollama, NL-to-SQL |
| @dbt | 2 | dbt models and projects |
| @orchestration | 2 | Airflow DAG generation |
| @dashboard | 1 | Dashboard API |
| @admin | 2 | Tenant/User management |
| @data-sources | 1 | Database connectors |

## 📁 Related Files

- [PROMPTS.md](PROMPTS.md) - Reusable prompt templates
- [../agents/](../agents/) - Agent definitions
- [../skills/](../skills/) - Skill implementations
- [../../docs/](../../docs/) - Project documentation

---

## 🎉 Implementation Complete!

All 51 implementation prompts have been created covering:
- ✅ **Phase 1**: Foundation infrastructure (7 prompts)
- ✅ **Phase 2**: Template engine & data sources (9 prompts)
- ✅ **Phase 3**: Semantic layer & AI (7 prompts)
- ✅ **Phase 4**: Analytics & dashboards (4 prompts)
- ✅ **Phase 5**: Administration & security (6 prompts)
- ✅ **Phase 6**: Testing, DevOps, documentation & UI polish (18 prompts)

Execute prompts in numerical order using the orchestrator agent for optimal results.
