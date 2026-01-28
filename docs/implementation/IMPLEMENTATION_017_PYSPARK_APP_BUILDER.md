# Implementation 017: PySpark App Builder Feature

## 📋 Feature Overview

**Feature**: PySpark Application Generator
**Date**: January 28, 2026
**Status**: 🟡 In Progress

### Description
Allow users to generate PySpark applications through a UI wizard where they can:
- Select a data source from existing connections
- Select a table or write a custom SQL query
- Select required columns
- Define Primary Key (PK)
- Define SCD (Slowly Changing Dimension) type and write mode
- Define CDC (Change Data Capture) column
- Define partition column(s)
- Save and generate the PySpark job

---

## 🏗️ Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PySpark App Builder                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Frontend (React)                                                            │
│  ├── PySparkAppBuilderPage         - Main wizard page                       │
│  ├── SourceSelector                 - Connection & table selection          │
│  ├── ColumnSelector                 - Column selection with types           │
│  ├── KeyConfiguration               - PK, CDC, partition column config      │
│  ├── SCDConfiguration               - SCD type & write mode selection       │
│  ├── SQLQueryEditor                 - Custom SQL query input                │
│  └── PySparkPreview                 - Generated code preview                │
│                                                                              │
│  Backend (Flask)                                                             │
│  ├── PySparkApp Model              - Database model                         │
│  ├── PySparkAppService             - Business logic                         │
│  ├── PySparkApp API                - REST endpoints                         │
│  └── PySpark Templates             - Jinja2 templates                       │
│                                                                              │
│  Template Engine                                                             │
│  ├── pyspark/extract_job.py.j2     - Source extraction template            │
│  ├── pyspark/scd_type1.py.j2       - SCD Type 1 template                   │
│  ├── pyspark/scd_type2.py.j2       - SCD Type 2 template                   │
│  └── pyspark/cdc_job.py.j2         - CDC processing template               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Data Model

### PySparkApp Entity

```python
class WriteMode(enum.Enum):
    APPEND = "append"
    OVERWRITE = "overwrite"
    MERGE = "merge"
    
class SCDType(enum.Enum):
    NONE = "none"
    TYPE1 = "type1"  # Overwrite
    TYPE2 = "type2"  # Historical tracking

class PySparkApp(db.Model):
    id: UUID
    tenant_id: UUID (FK)
    connection_id: UUID (FK)  # Source connection
    
    # Identity
    name: str
    description: str
    
    # Source Configuration
    source_type: str  # 'table' | 'query'
    source_table: str  # Schema.Table name
    source_query: str  # Custom SQL query
    
    # Column Configuration
    selected_columns: JSONB  # List of selected columns with types
    primary_key_columns: JSONB  # List of PK column names
    
    # CDC Configuration
    cdc_column: str  # Column for change detection
    cdc_type: str  # 'timestamp' | 'version' | 'hash'
    
    # Partitioning
    partition_columns: JSONB  # List of partition columns
    
    # SCD & Write Configuration
    scd_type: SCDType
    write_mode: WriteMode
    
    # Target Configuration
    target_database: str  # ClickHouse target
    target_table: str
    
    # Generated Artifacts
    generated_code: Text
    generated_at: DateTime
    
    # Audit
    created_by: UUID
    created_at: DateTime
    updated_at: DateTime
```

---

## 🔄 Agent Delegation Plan

### Phase 1: Backend Foundation
**Duration**: 2-3 days

#### Task 1.1: Database Model
```markdown
[DELEGATE: @backend]
Task: Create PySparkApp SQLAlchemy model
Context: New model for storing PySpark app configurations
Expected Output:
  - backend/app/models/pyspark_app.py
  - Alembic migration
  - Model relationships with Connection and Tenant
Prompt Reference: 017-pyspark-model.md
[/DELEGATE]
```

#### Task 1.2: PySpark App Service
```markdown
[DELEGATE: @backend]
Task: Create PySparkAppService for business logic
Context: Service to manage CRUD operations and code generation
Expected Output:
  - backend/app/services/pyspark_app_service.py
  - Integration with TemplateEngine for code generation
  - Validation logic for configurations
Prompt Reference: 017-pyspark-service.md
[/DELEGATE]
```

#### Task 1.3: REST API Endpoints
```markdown
[DELEGATE: @backend]
Task: Create PySpark App API endpoints
Context: REST endpoints for CRUD and code generation
Expected Output:
  - backend/app/api/v1/pyspark_apps.py
  - Endpoints: list, create, get, update, delete, generate, preview
  - Proper validation and error handling
Prompt Reference: 017-pyspark-api.md
[/DELEGATE]
```

### Phase 2: Template Engine
**Duration**: 2-3 days

#### Task 2.1: PySpark Templates
```markdown
[DELEGATE: @template-engine]
Task: Create Jinja2 templates for PySpark job generation
Context: Pre-approved templates following ADR-002
Expected Output:
  - backend/templates/pyspark/extract_job.py.j2
  - backend/templates/pyspark/scd_type1.py.j2
  - backend/templates/pyspark/scd_type2.py.j2
  - backend/templates/pyspark/cdc_job.py.j2
  - backend/templates/pyspark/common_utils.py.j2
  - Update manifest.json with schemas
Prompt Reference: 017-pyspark-templates.md
[/DELEGATE]
```

#### Task 2.2: Template Validation Schemas
```markdown
[DELEGATE: @template-engine]
Task: Create Pydantic validation schemas for PySpark templates
Context: Input validation for template parameters
Expected Output:
  - backend/app/schemas/pyspark_schemas.py
  - Validation rules for all template parameters
Prompt Reference: 017-pyspark-schemas.md
[/DELEGATE]
```

### Phase 3: Frontend UI
**Duration**: 3-4 days

#### Task 3.1: Types and API Client
```markdown
[DELEGATE: @frontend]
Task: Create TypeScript types and API client for PySpark apps
Context: Type definitions and API integration
Expected Output:
  - frontend/src/types/pyspark.ts
  - frontend/src/services/pysparkApi.ts
  - React Query hooks
Prompt Reference: 017-pyspark-frontend-types.md
[/DELEGATE]
```

#### Task 3.2: PySpark Builder Components
```markdown
[DELEGATE: @frontend]
Task: Create PySpark App Builder wizard components
Context: Multi-step wizard for creating PySpark apps
Expected Output:
  - frontend/src/features/pyspark/components/
    - SourceSelector.tsx
    - ColumnSelector.tsx
    - KeyConfiguration.tsx
    - SCDConfiguration.tsx
    - SQLQueryEditor.tsx
    - PySparkPreview.tsx
Prompt Reference: 017-pyspark-components.md
[/DELEGATE]
```

#### Task 3.3: PySpark Pages
```markdown
[DELEGATE: @frontend]
Task: Create PySpark App pages
Context: List and builder pages
Expected Output:
  - frontend/src/pages/pyspark/PySparkAppsListPage.tsx
  - frontend/src/pages/pyspark/PySparkAppBuilderPage.tsx
  - frontend/src/pages/pyspark/PySparkAppDetailPage.tsx
  - Route configuration updates
Prompt Reference: 017-pyspark-pages.md
[/DELEGATE]
```

### Phase 4: Testing & Security
**Duration**: 1-2 days

#### Task 4.1: Backend Tests
```markdown
[DELEGATE: @testing]
Task: Create unit and integration tests for PySpark feature
Context: Comprehensive test coverage
Expected Output:
  - backend/tests/unit/test_pyspark_app_model.py
  - backend/tests/unit/test_pyspark_app_service.py
  - backend/tests/unit/test_pyspark_templates.py
  - backend/tests/integration/test_pyspark_api.py
Prompt Reference: 017-pyspark-tests.md
[/DELEGATE]
```

#### Task 4.2: Security Review
```markdown
[DELEGATE: @security]
Task: Security review of PySpark App Builder
Context: Ensure template engine compliance and input validation
Expected Output:
  - Security audit report
  - Validation improvements
  - SQL injection prevention verification
Prompt Reference: 017-pyspark-security.md
[/DELEGATE]
```

---

## 📁 File Structure

```
backend/
├── app/
│   ├── models/
│   │   └── pyspark_app.py           # New: PySpark App model
│   ├── schemas/
│   │   └── pyspark_schemas.py       # New: Validation schemas
│   ├── services/
│   │   └── pyspark_app_service.py   # New: Business logic
│   └── api/v1/
│       └── pyspark_apps.py          # New: API endpoints
├── templates/
│   └── pyspark/                     # New: PySpark templates
│       ├── extract_job.py.j2
│       ├── scd_type1.py.j2
│       ├── scd_type2.py.j2
│       ├── cdc_job.py.j2
│       └── common_utils.py.j2
└── tests/
    ├── unit/
    │   ├── test_pyspark_app_model.py
    │   ├── test_pyspark_app_service.py
    │   └── test_pyspark_templates.py
    └── integration/
        └── test_pyspark_api.py

frontend/
├── src/
│   ├── types/
│   │   └── pyspark.ts               # New: TypeScript types
│   ├── services/
│   │   └── pysparkApi.ts            # New: API client
│   ├── features/
│   │   └── pyspark/                 # New: PySpark feature
│   │       ├── components/
│   │       │   ├── SourceSelector.tsx
│   │       │   ├── ColumnSelector.tsx
│   │       │   ├── KeyConfiguration.tsx
│   │       │   ├── SCDConfiguration.tsx
│   │       │   ├── SQLQueryEditor.tsx
│   │       │   └── PySparkPreview.tsx
│   │       ├── hooks/
│   │       │   └── index.ts
│   │       └── index.ts
│   └── pages/
│       └── pyspark/                 # New: PySpark pages
│           ├── PySparkAppsListPage.tsx
│           ├── PySparkAppBuilderPage.tsx
│           └── PySparkAppDetailPage.tsx
```

---

## 🔗 API Endpoints

### PySpark Apps API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/pyspark-apps` | List all PySpark apps |
| POST | `/api/v1/pyspark-apps` | Create new PySpark app |
| GET | `/api/v1/pyspark-apps/{id}` | Get PySpark app details |
| PUT | `/api/v1/pyspark-apps/{id}` | Update PySpark app |
| DELETE | `/api/v1/pyspark-apps/{id}` | Delete PySpark app |
| POST | `/api/v1/pyspark-apps/{id}/generate` | Generate PySpark code |
| GET | `/api/v1/pyspark-apps/{id}/preview` | Preview generated code |
| POST | `/api/v1/pyspark-apps/preview` | Preview without saving |

### Connection Schema API (Extended)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/connections/{id}/columns` | Get table columns |
| POST | `/api/v1/connections/{id}/query/validate` | Validate SQL query |
| POST | `/api/v1/connections/{id}/query/columns` | Get columns from query |

---

## ✅ Acceptance Criteria

1. **Data Source Selection**
   - [ ] User can select from available connections
   - [ ] User can browse tables within connection
   - [ ] User can write custom SQL query
   - [ ] SQL query is validated before proceeding

2. **Column Configuration**
   - [ ] User can select/deselect columns
   - [ ] Column data types are displayed
   - [ ] User can define primary key column(s)
   - [ ] User can define CDC tracking column
   - [ ] User can define partition column(s)

3. **SCD & Write Mode**
   - [ ] User can select SCD Type (None, Type 1, Type 2)
   - [ ] User can select Write Mode (Append, Overwrite, Merge)
   - [ ] Configuration validated based on selections

4. **Code Generation**
   - [ ] PySpark code generated from templates
   - [ ] Code preview available before saving
   - [ ] Generated code follows best practices
   - [ ] No arbitrary code - all from templates

5. **Save & Manage**
   - [ ] User can save PySpark app configuration
   - [ ] User can edit existing configurations
   - [ ] User can delete configurations
   - [ ] Audit trail maintained

---

## 🚀 Next Steps

1. Start with Phase 1: Backend Foundation
2. Create model, service, and API endpoints
3. Proceed to Template Engine phase
4. Build Frontend components
5. Complete testing and security review

