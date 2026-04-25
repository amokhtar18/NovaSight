# NovaSight Prompts Collection

This document contains reusable prompts for implementing NovaSight components using the multi-agent framework.

---

## 🏗️ Infrastructure Prompts

### Prompt: Initialize Project Infrastructure
```
Set up the NovaSight development infrastructure including:
1. Docker Compose with PostgreSQL, ClickHouse, Redis, Airflow, and Ollama
2. Create backend Flask application structure with app factory
3. Create frontend React/Vite project with Shadcn/UI
4. Set up shared networking and volume mounts
5. Configure environment variables template

Follow the infrastructure-agent specifications and ensure all services can communicate.
```

### Prompt: Configure Airflow for Multi-Tenant DAGs
```
Configure Apache Airflow to support multi-tenant DAG execution:
1. Set up CeleryExecutor with Redis broker
2. Configure DAG folder structure for tenant isolation
3. Set up Airflow REST API access
4. Create custom connection for tenant databases
5. Implement DAG discovery and registration

Ensure DAGs are isolated per tenant and follow the Template Engine Rule.
```

---

## 🔧 Backend Prompts

### Prompt: Create REST API Endpoint
```
Create a Flask REST API endpoint for [RESOURCE_NAME] with:
1. Blueprint registration at /api/v1/[resource]
2. CRUD operations (GET, POST, PUT, DELETE)
3. Pydantic schema validation for request/response
4. JWT authentication with @jwt_required
5. Permission checking with @require_permission
6. Tenant isolation through g.tenant context
7. Proper error handling and response format

Follow the flask-api skill patterns and backend-agent specifications.
```

### Prompt: Implement Service Layer
```
Implement the [SERVICE_NAME]Service class with:
1. Constructor accepting dependencies (other services, config)
2. Business logic methods with proper typing
3. Database operations using SQLAlchemy
4. Tenant context awareness (g.tenant)
5. Input validation using Pydantic schemas
6. Error handling with meaningful messages
7. Audit logging for sensitive operations

Follow the service layer patterns from backend-agent.
```

### Prompt: Create SQLAlchemy Model
```
Create SQLAlchemy model for [TABLE_NAME] with:
1. TenantMixin for multi-tenant isolation
2. UUID primary key
3. All required columns with proper types
4. Relationships to related models
5. to_dict() method for serialization
6. Indexes for common queries
7. Created/updated timestamps

Follow the model patterns from backend-agent.
```

---

## 🎨 Frontend Prompts

### Prompt: Create List Page
```
Create a React list page for [RESOURCE_NAME] with:
1. PageHeader component with title and action button
2. DataTable with columns, sorting, filtering
3. TanStack Query hook for data fetching
4. Loading and error states
5. Empty state handling
6. Row actions (edit, delete)
7. Pagination

Follow react-components skill patterns and frontend-agent specifications.
```

### Prompt: Create Form Component
```
Create a React form for [RESOURCE_NAME] with:
1. React Hook Form setup with Zod validation
2. Shadcn/UI Form components
3. Field validation with error messages
4. Submit handler with mutation
5. Loading state during submission
6. Toast notifications for success/error
7. Cancel button navigation

Use the form patterns from react-components skill.
```

### Prompt: Create Detail Page
```
Create a React detail page for [RESOURCE_NAME] with:
1. Route parameter extraction (id)
2. TanStack Query for fetching data
3. Loading skeleton state
4. Error state with retry
5. Display all resource fields
6. Edit and delete actions
7. Back navigation

Follow the page patterns from frontend-agent.
```

---

## 🔄 Data Pipeline Prompts

### Prompt: Create Ingestion Pipeline Configuration
```
Create an ingestion pipeline for [SOURCE_TABLE] to [TARGET_TABLE]:
1. Define DltExtractDefinition / DltMergeDefinition / DltSCD2Definition with validated schema
2. Map source columns to target columns with types
3. Configure load type (full/incremental)
4. Set partition strategy if needed
5. Generate dlt pipeline using template engine
6. Create Airflow DAG for scheduling

Follow the template-engine skill and Template Engine Rule strictly.
```

### Prompt: Create dbt Model
```
Create a dbt model for [MODEL_NAME] with:
1. Define DbtModelConfig with source/columns
2. Configure joins if needed
3. Add calculated columns/aggregations
4. Configure materialization (view/table/incremental)
5. Add column tests (unique, not_null, etc.)
6. Generate model SQL and schema YAML
7. Update lineage graph

Use dbt-agent specifications and template patterns.
```

---

## 🤖 AI Integration Prompts

### Prompt: Implement AI Query Assistant
```
Implement the AI query assistant that:
1. Takes natural language question as input
2. Builds context from dbt model schema
3. Calls Ollama with structured prompt
4. Extracts SQL from response
5. Validates SQL with SQLValidator
6. Injects RLS filters
7. Returns validated query

Follow ai-agent patterns and security requirements.
```

### Prompt: Add Schema Context to AI
```
Enhance AI prompts with schema context:
1. Fetch relevant dbt models for the context
2. Format column information (name, type, description)
3. Include relationship information
4. Add sample values for categorical columns
5. Include business rules/constraints
6. Format as structured prompt section

Use the PromptBuilder patterns from ai-agent.
```

---

## 🔒 Security Prompts

### Prompt: Implement Authentication Flow
```
Implement JWT authentication flow with:
1. Login endpoint with credentials validation
2. Password hashing with Argon2
3. JWT token generation (access + refresh)
4. Token refresh endpoint
5. Logout with token blacklisting
6. Failed login tracking and lockout
7. Audit logging for auth events

Follow security-agent patterns and best practices.
```

### Prompt: Add Row-Level Security
```
Implement RLS for [MODEL_NAME] with:
1. Define RLS rule (column, user_attribute)
2. Register rule in RLSService
3. Integrate with query execution
4. Test with different user contexts
5. Verify filters are applied correctly
6. Add audit logging for RLS application

Use the RLS patterns from multi-tenant-db skill.
```

---

## 🧪 Testing Prompts

### Prompt: Write Unit Tests
```
Write pytest unit tests for [SERVICE_NAME]Service:
1. Create test fixtures (app, db_session, tenant, user)
2. Test happy path for each method
3. Test validation errors
4. Test error handling
5. Test edge cases
6. Mock external dependencies
7. Achieve >80% coverage

Follow testing-agent patterns and pytest best practices.
```

### Prompt: Write Integration Tests
```
Write integration tests for [ENDPOINT] API:
1. Set up test client with auth headers
2. Test successful operations
3. Test authentication required
4. Test authorization (forbidden)
5. Test tenant isolation
6. Test validation errors
7. Test not found scenarios

Use testing-agent patterns with proper fixtures.
```

---

## 📊 Dashboard Prompts

### Prompt: Create Chart Component
```
Create a [CHART_TYPE] chart component with:
1. ChartConfig schema validation
2. Recharts implementation
3. Responsive container
4. Configurable colors
5. Tooltip and legend
6. Loading state
7. Empty state

Follow dashboard-agent patterns and Recharts documentation.
```

### Prompt: Implement Dashboard Canvas
```
Implement the dashboard canvas with:
1. react-grid-layout integration
2. Widget rendering system
3. Drag and drop in edit mode
4. Resize functionality
5. Layout persistence
6. Widget configuration panel
7. Add/remove widgets

Use dashboard-agent specifications.
```

---

## 🔧 DevOps Prompts

### Prompt: Create CI/CD Pipeline
```
Create GitHub Actions CI/CD pipeline with:
1. Backend pytest with coverage
2. Frontend Vitest with coverage
3. E2E tests with Playwright
4. Docker image building
5. Security scanning (Trivy)
6. Deployment to staging/production
7. Slack notifications

Follow DevOps best practices for containerized applications.
```

### Prompt: Set Up Monitoring
```
Set up application monitoring with:
1. Prometheus metrics endpoint in Flask
2. Grafana dashboards for key metrics
3. AlertManager for critical alerts
4. Request tracing with Jaeger
5. Log aggregation with Loki
6. Error tracking with Sentry
7. Uptime monitoring

Configure for multi-tenant visibility.
```

---

## Usage Guide

### How to Use These Prompts

1. **Select the appropriate prompt** based on what you need to implement
2. **Replace placeholders** (text in [BRACKETS]) with actual values
3. **Reference the appropriate agent** mentioned in each prompt
4. **Follow the linked skills** for detailed implementation patterns
5. **Verify against acceptance criteria** in the BRD

### Customizing Prompts

You can extend these prompts by adding:
- Specific business requirements
- Additional constraints
- Reference to existing code
- Specific technology choices

### Prompt Chaining

For complex features, chain prompts together:
1. Start with backend model
2. Create service layer
3. Add API endpoints
4. Build frontend components
5. Write tests

---

*NovaSight Prompts Collection v1.0*
