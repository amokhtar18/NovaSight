# Agentic AI Module - Quick Reference

## 🎯 Task Breakdown by Agent

### Week 1-2: Core Infrastructure

```
┌────────────────────────────────────────────────────────────────────┐
│  TASK: Core Agent Infrastructure                                    │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  @backend (Opus 4.5) - 5 days                                      │
│  ├── [001] Create database migration for agent tables              │
│  ├── [002] TenantAgentConfig model (SQLAlchemy)                    │
│  ├── [003] AgentConversation model                                 │
│  ├── [004] TenantAgentService class                                │
│  └── [005] ContextBuilderService (schema loading)                  │
│                                                                     │
│  @security (Opus 4.5) - 3 days                                     │
│  ├── [006] PromptGuardService implementation                       │
│  ├── [007] Jailbreak detection patterns                            │
│  └── [008] Output filtering & sanitization                         │
│                                                                     │
│  @ai (Opus 4.5) - 2 days                                           │
│  ├── [009] Enhanced agent prompt templates                         │
│  └── [010] Response format validation                              │
│                                                                     │
│  @testing (Sonnet 4.5) - 2 days                                    │
│  ├── [011] Unit tests for TenantAgentService                       │
│  └── [012] Unit tests for PromptGuardService                       │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Week 2-3: API Endpoints

```
┌────────────────────────────────────────────────────────────────────┐
│  TASK: Agent API Development                                        │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  @backend (Opus 4.5) - 4 days                                      │
│  ├── [013] POST /api/v1/agents/chat endpoint                       │
│  ├── [014] GET /api/v1/agents/suggestions endpoint                 │
│  ├── [015] GET /api/v1/agents/history endpoint                     │
│  ├── [016] POST /api/v1/agents/assist-sql endpoint                 │
│  └── [017] Agent config CRUD endpoints                             │
│                                                                     │
│  @admin (Haiku 4.5) - 2 days                                       │
│  ├── [018] GET /api/v1/portal/agents (list all tenants)            │
│  └── [019] PUT /api/v1/portal/agents/{id} (admin config)           │
│                                                                     │
│  @security (Opus 4.5) - 1 day                                      │
│  └── [020] Rate limiting middleware for agent endpoints            │
│                                                                     │
│  @testing (Sonnet 4.5) - 2 days                                    │
│  ├── [021] API integration tests                                   │
│  └── [022] Security boundary tests                                 │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Week 3-4: Ask AI Frontend

```
┌────────────────────────────────────────────────────────────────────┐
│  TASK: Ask AI Page Implementation                                   │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  @frontend (Sonnet 4.5) - 5 days                                   │
│  ├── [023] AskAIPage.tsx - main page layout                        │
│  ├── [024] AskAIChat.tsx - chat interface                          │
│  ├── [025] ChatMessage.tsx - message components                    │
│  ├── [026] SuggestionChips.tsx - clickable suggestions             │
│  ├── [027] ResultsView.tsx - table/chart toggle                    │
│  ├── [028] SchemaContext.tsx - available data sidebar              │
│  ├── [029] useAgentChat.ts hook                                    │
│  └── [030] agentService.ts API client                              │
│                                                                     │
│  @dashboard (Sonnet 4.5) - 2 days                                  │
│  ├── [031] Chart type auto-detection                               │
│  └── [032] Results visualization integration                       │
│                                                                     │
│  @testing (Sonnet 4.5) - 2 days                                    │
│  ├── [033] E2E tests for Ask AI flow                               │
│  └── [034] Component unit tests                                    │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Week 4-5: SQL Editor Integration

```
┌────────────────────────────────────────────────────────────────────┐
│  TASK: SQL Editor AI Features                                       │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  @frontend (Sonnet 4.5) - 4 days                                   │
│  ├── [035] AIAssistPanel.tsx component                             │
│  ├── [036] QuickAskInput.tsx inline input                          │
│  ├── [037] SQL suggestions display                                 │
│  └── [038] useAIAssist.ts hook                                     │
│                                                                     │
│  @ai (Opus 4.5) - 2 days                                           │
│  ├── [039] SQL explanation prompt template                         │
│  └── [040] Query optimization suggestions                          │
│                                                                     │
│  @testing (Sonnet 4.5) - 1 day                                     │
│  └── [041] SQL Editor AI integration tests                         │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Week 5-6: Portal Management

```
┌────────────────────────────────────────────────────────────────────┐
│  TASK: Admin Agent Management Console                               │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  @frontend (Sonnet 4.5) - 4 days                                   │
│  ├── [042] AgentManagementPage.tsx                                 │
│  ├── [043] AgentList.tsx component                                 │
│  ├── [044] AgentConfigForm.tsx                                     │
│  ├── [045] AgentUsageStats.tsx                                     │
│  └── [046] AgentSecurityLog.tsx                                    │
│                                                                     │
│  @backend (Opus 4.5) - 2 days                                      │
│  ├── [047] Usage metrics aggregation service                       │
│  └── [048] Security events query service                           │
│                                                                     │
│  @testing (Sonnet 4.5) - 1 day                                     │
│  └── [049] Portal management tests                                 │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Week 6-7: Security Hardening

```
┌────────────────────────────────────────────────────────────────────┐
│  TASK: Security Audit & Polish                                      │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  @security (Opus 4.5) - 3 days                                     │
│  ├── [050] Penetration testing for prompt injection                │
│  ├── [051] Cross-tenant data access audit                          │
│  └── [052] Security documentation                                  │
│                                                                     │
│  @testing (Sonnet 4.5) - 2 days                                    │
│  ├── [053] Load testing agent endpoints                            │
│  └── [054] Fuzzing tests for input validation                      │
│                                                                     │
│  @infrastructure (Sonnet 4.5) - 2 days                             │
│  ├── [055] Monitoring dashboards for agent usage                   │
│  └── [056] Alerting for security events                            │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Files to Create/Modify

### Backend (Python)

```
backend/app/domains/ai/
├── domain/
│   ├── models.py              # NEW: TenantAgentConfig, AgentConversation
│   ├── value_objects.py       # NEW: AgentContext, ChatMessage, AgentResponse
│   └── interfaces.py          # NEW: IAgentService, IPromptGuard, IContextBuilder
├── application/
│   ├── tenant_agent_service.py    # NEW: Main orchestration
│   ├── context_builder_service.py # NEW: Tenant context construction
│   ├── conversation_service.py    # NEW: History management
│   └── nl_to_sql.py               # EXISTING: Minor enhancements
├── infrastructure/
│   └── ollama/
│       ├── prompt_guard.py        # NEW: Anti-jailbreak service
│       ├── agent_prompts.py       # NEW: Agent-specific prompts
│       └── client.py              # EXISTING: No changes needed
├── api/
│   ├── agent_routes.py            # NEW: Chat/suggestion endpoints
│   ├── agent_config_routes.py     # NEW: Config management
│   └── assistant_routes.py        # EXISTING: Minor enhancements
└── schemas/
    └── agent_schemas.py           # NEW: Pydantic schemas

backend/migrations/versions/
└── xxxx_add_agent_tables.py       # NEW: Database migration
```

### Frontend (TypeScript/React)

```
frontend/src/features/ask-ai/
├── components/
│   ├── AskAIChat.tsx              # NEW
│   ├── ChatMessage.tsx            # NEW
│   ├── ResultsView.tsx            # NEW
│   ├── SuggestionChips.tsx        # NEW
│   └── SchemaContext.tsx          # NEW
├── hooks/
│   ├── useAgentChat.ts            # NEW
│   ├── useQuerySuggestions.ts     # NEW
│   └── useChatHistory.ts          # NEW
├── pages/
│   └── AskAIPage.tsx              # NEW
├── services/
│   └── agentService.ts            # NEW
├── types.ts                       # NEW
└── index.ts                       # NEW

frontend/src/features/sql-editor/
├── components/
│   ├── AIAssistPanel.tsx          # NEW
│   └── QuickAskInput.tsx          # NEW
└── hooks/
    └── useAIAssist.ts             # NEW

frontend/src/pages/portal/
├── AgentManagementPage.tsx        # NEW
└── components/
    ├── AgentList.tsx              # NEW
    ├── AgentConfigForm.tsx        # NEW
    ├── AgentUsageStats.tsx        # NEW
    └── AgentSecurityLog.tsx       # NEW

frontend/src/App.tsx               # MODIFY: Add routes
```

---

## 🚀 Quick Start Commands

```bash
# Start Phase 1 - Core Infrastructure
/start-phase 1

# Delegate specific task
/delegate @backend "Create TenantAgentConfig model with SQLAlchemy"

# Check progress
/progress ai-module

# Integration check
/integration-check tenant-agent-service prompt-guard-service
```

---

## 📋 Dependency Graph

```
                    ┌────────────────────────┐
                    │   Database Migration   │
                    └───────────┬────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            ▼                   ▼                   ▼
   ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
   │ TenantAgent     │ │ PromptGuard     │ │ Context         │
   │ Config Model    │ │ Service         │ │ Builder         │
   └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
            │                   │                   │
            └───────────────────┼───────────────────┘
                                ▼
                    ┌────────────────────────┐
                    │  TenantAgentService    │
                    └───────────┬────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            ▼                   ▼                   ▼
   ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
   │ Agent API       │ │ SQL Assist API  │ │ Portal API      │
   │ Endpoints       │ │ Endpoint        │ │ Endpoints       │
   └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
            │                   │                   │
            └───────────────────┼───────────────────┘
                                ▼
            ┌───────────────────┼───────────────────┐
            ▼                   ▼                   ▼
   ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
   │ Ask AI Page     │ │ SQL Editor      │ │ Portal Agent    │
   │ (Frontend)      │ │ Integration     │ │ Management      │
   └─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

*Generated by NovaSight Orchestrator Agent*
