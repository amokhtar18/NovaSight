# NovaSight Agent Handoff System

## Overview

The handoff system coordinates task routing between 13 specialized agents in the NovaSight multi-agent framework. It defines clear responsibilities, priorities, and delegation protocols to ensure efficient collaboration.

## Configuration

The handoff configuration is defined in `.github/handoff.yml` and includes:

1. **Agent Definitions** - 13 specialized agents with capabilities
2. **Handoff Rules** - Pattern-based routing to appropriate agents
3. **Phase Mappings** - Project phases and involved agents
4. **Priority Resolution** - Conflict resolution when patterns match multiple agents
5. **Delegation Protocol** - Standard format for agent communication
6. **Context Sharing** - Shared files and constraints

## Agents

### Master Coordinator

- **novasight-orchestrator** - Coordinates all agents, manages phases, tracks progress

### Domain Specialists

- **infrastructure** - DevOps, Docker, Kubernetes, CI/CD
- **backend** - Flask API, SQLAlchemy, authentication
- **frontend** - React, TypeScript, UI/UX
- **template-engine** - Jinja2 templates, code generation (security-critical)
- **data-sources** - Database connections, schema introspection
- **dbt** - dbt models, semantic layer, transformations
- **orchestration** - Dagster pipelines, scheduling
- **dashboard** - Analytics, charts, visualizations
- **ai** - Ollama integration, NL2SQL
- **admin** - Tenant management, RBAC
- **testing** - Unit, integration, E2E tests
- **security** - Security review, encryption, audit (critical)

## Priority Order

When multiple patterns match a task, agents are prioritized as follows:

1. **novasight-orchestrator** - Master coordinator (highest)
2. **security** - Security-critical tasks
3. **template-engine** - Code generation tasks
4. **Domain specialists** (ai, dbt, orchestration, dashboard, data-sources)
5. **General implementation** (backend, frontend)
6. **admin** - Administrative tasks
7. **testing** - Verification tasks
8. **infrastructure** - Infrastructure tasks (lowest for non-infra)

## Handoff Rules

Handoff rules use regex patterns to route tasks:

```yaml
- patterns:
    - "docker|dockerfile|compose"
    - "kubernetes|k8s|helm"
  target: infrastructure
  prompts:
    - "001-init-infrastructure.md"
```

### Rule Structure

- **patterns**: List of regex patterns to match task descriptions
- **target**: Agent ID to handle matching tasks
- **prompts**: Reference prompt files for the agent
- **require_review**: Optional flag for critical tasks

## Delegation Protocol

### Standard Format

```
[DELEGATE: @{agent_id}]
Task: {task_description}
Context: {relevant_context}
Expected Output: {expected_output}
Prompt Reference: {prompt_file}
[/DELEGATE]
```

### Response Format

```
✅ Task Complete: {task_description}
📁 Files modified:
  {file_list}
🧪 Tests: {test_status}
📊 Progress: {progress}

Next: {next_task}
```

## Critical Constraints

### Template Engine Rule (ADR-002)

**NO ARBITRARY CODE GENERATION.** All executable artifacts (dlt pipelines, Dagster ops, dbt models) must use pre-approved, security-audited Jinja2 templates.

Applies to: template-engine, orchestration, dbt, data-sources

### Multi-Tenant Isolation

All data access must be scoped to tenant context.

Applies to: backend, data-sources, dashboard, admin

### Credential Encryption

All credentials must be encrypted using AES-256 via Fernet.

Applies to: backend, data-sources, security

## Validation

Run the validation script to check handoff configuration:

```bash
python3 .github/scripts/validate_handoff.py
```

This checks:
- Agent file references exist
- Priority order includes all agents
- Handoff rule targets are valid
- Phase definitions reference valid agents
- Constraint references are valid
- Metadata matches actual configuration

## Implementation Phases

The handoff system supports 8 implementation phases:

1. **Phase 1** - Foundation & Infrastructure (Weeks 1-2)
2. **Phase 2** - Template Engine (Week 3)
3. **Phase 3** - Data Sources (Weeks 4-5)
4. **Phase 4** - Semantic Layer (Weeks 6-7)
5. **Phase 5** - Analytics & AI (Weeks 8-9)
6. **Phase 6** - Governance (Week 10)
7. **Phase 7** - Testing (Week 11)
8. **Phase 8** - Deployment (Week 12)

Each phase specifies which agents are involved and which prompts to use.

## Escalation Rules

### Require Human Review

- Security changes
- Schema migrations
- Template modifications
- Third-party additions
- Architecture changes

### Notifications

- Phase completion
- Test failures
- Security warnings
- Integration errors

## Usage Examples

### Delegating to Backend Agent

```
[DELEGATE: @backend]
Task: Create REST API endpoint for data source connections
Context: Need CRUD operations with multi-tenant isolation
Expected Output: Flask blueprint with SQLAlchemy models
Prompt Reference: 014-data-source-api.md
[/DELEGATE]
```

### Delegating to Security Agent

```
[DELEGATE: @security]
Task: Review credential encryption implementation
Context: New data source connector with database passwords
Expected Output: Security audit report with recommendations
Prompt Reference: 033-data-encryption.md
[/DELEGATE]
```

## Maintenance

### Adding a New Agent

1. Add agent definition to `agents` section in `handoff.yml`
2. Add agent to `priority_order` at appropriate position
3. Create agent file in `.github/agents/{agent-name}.agent.md`
4. Add handoff rules with patterns and target
5. Update relevant phase definitions
6. Run validation script to verify

### Modifying Handoff Rules

1. Update patterns in `handoff_rules` section
2. Ensure target agent exists
3. Add/update prompt references
4. Run validation script to verify
5. Test with sample tasks

## References

- [Agent Files](../agents/README.md)
- [Implementation Plan](../../docs/implementation/IMPLEMENTATION_PLAN.md)
- [Architecture Decisions](../../docs/requirements/Architecture_Decisions.md)
- [Validation Script](scripts/validate_handoff.py)

---

*Last Updated: 2026-01-28*
