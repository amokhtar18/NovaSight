---

### EPIC 7: Multi-Tenancy & Administration

**Epic Description:** Implement complete tenant isolation with separate URLs and schemas, role-based access control (RBAC), row-level security (RLS), and administrative portals for both tenant admins and platform super admins.

**Business Value:** Ensures enterprise-grade security and governance while enabling scalable multi-tenant operations.

---

#### US-7.1: Tenant Provisioning

**As a** Super Admin  
**I want to** provision new tenants  
**So that** new customers can be onboarded to the platform

**Acceptance Criteria:**

```gherkin
GIVEN I am logged in as Super Admin
WHEN I navigate to "Tenant Management"
AND click "Create Tenant"
THEN I see a provisioning form with:
  - Tenant Name
  - Tenant Slug (for URL: slug.novasight.com)
  - Primary Admin Email
  - Subscription Tier (Basic, Pro, Enterprise)
  - Resource Limits:
    - Max users
    - Max data storage (GB)
    - Max DAG runs per day
    - AI queries per month

WHEN I submit the form
THEN the system:
  - Creates tenant record in platform metadata
  - Creates isolated PostgreSQL schema: tenant_{slug}
  - Creates ClickHouse database: tenant_{slug}
  - Creates Airflow DAG folder: /dags/tenant_{slug}/
  - Creates dbt project folder: /dbt/tenant_{slug}/
  - Sends invitation email to Primary Admin

GIVEN provisioning completes
WHEN Primary Admin clicks invitation link
THEN they can set password and access tenant at {slug}.novasight.com
```

---

#### US-7.2: Tenant URL & Schema Isolation

**As a** Tenant User  
**I want to** access my tenant via a unique URL  
**So that** I have a branded, isolated experience

**Acceptance Criteria:**

```gherkin
GIVEN I navigate to acme.novasight.com
WHEN the system processes the request
THEN it:
  - Identifies tenant from subdomain
  - Routes to tenant-specific schema
  - Applies tenant branding (if configured)
  - Loads only tenant's data and configurations

GIVEN I am authenticated in Tenant A
WHEN I attempt to access Tenant B's URL
THEN I am redirected to Tenant B login
AND my Tenant A session does not grant access

GIVEN queries execute
WHEN they run against ClickHouse
THEN they are scoped to tenant's database
AND cross-tenant access is impossible at query level
```

---

#### US-7.3: Role-Based Access Control (RBAC)

**As a** Tenant Admin  
**I want to** define roles and assign permissions  
**So that** users only access what they need

**Acceptance Criteria:**

```gherkin
GIVEN I am on "User Management" > "Roles"
WHEN I create a new role
THEN I can configure permissions across modules:

DATA SOURCES:
  - View connections
  - Create/Edit connections
  - Delete connections

INGESTION:
  - View jobs
  - Create/Edit jobs
  - Run jobs
  - Delete jobs

SEMANTIC LAYER:
  - View models
  - Create/Edit models
  - Publish models
  - Delete models

ORCHESTRATION:
  - View DAGs
  - Create/Edit DAGs
  - Deploy DAGs
  - Trigger runs
  - Pause/Resume

EXPLORATION:
  - Run queries
  - Create charts
  - Create dashboards
  - Share dashboards
  - Use AI assistant

ADMINISTRATION:
  - Manage users
  - Manage roles
  - View audit logs
  - Configure tenant settings

GIVEN I assign a role to a user
WHEN they access the application
THEN UI elements for unauthorized actions are hidden
AND API calls for unauthorized actions return 403
```

---

#### US-7.4: Row-Level Security (RLS)

**As a** Tenant Admin  
**I want to** configure row-level security policies  
**So that** users only see data they're authorized to view

**Acceptance Criteria:**

```gherkin
GIVEN I am on "Security" > "Row-Level Security"
WHEN I create an RLS policy
THEN I can configure:
  - Policy name
  - Target table(s) or model(s)
  - Filter column
  - Filter logic:
    - User attribute match (e.g., region = user.region)
    - Role-based values (e.g., role = 'manager' sees all)
    - Custom expression

Example Policy:
  Name: "Regional Sales Access"
  Target: sales_data
  Logic: sales_region IN (SELECT region FROM user_regions WHERE user_id = current_user_id())

GIVEN RLS is configured
WHEN a user queries the table
THEN the RLS filter is automatically applied
AND users only see rows matching their policy
AND this applies to:
  - Direct SQL queries
  - Dashboard views
  - AI assistant queries
  - Exports
```

---

#### US-7.5: User Management

**As a** Tenant Admin  
**I want to** manage users in my tenant  
**So that** I control who has access

**Acceptance Criteria:**

```gherkin
GIVEN I navigate to "User Management"
WHEN I view the user list
THEN I see:
  - Name
  - Email
  - Role(s)
  - Status (Active, Invited, Disabled)
  - Last login
  - Created date

WHEN I click "Invite User"
THEN I can:
  - Enter email address
  - Select role(s)
  - Set RLS attributes (e.g., region = "West")
  - Send invitation

WHEN I edit a user
THEN I can:
  - Change roles
  - Update RLS attributes
  - Reset password (sends email)
  - Disable/Enable account

WHEN I disable a user
THEN their sessions are immediately invalidated
AND they cannot log in
AND their data remains for audit purposes
```

---

#### US-7.6: Audit Logging

**As a** Tenant Admin  
**I want to** view comprehensive audit logs  
**So that** I can track all system activity

**Acceptance Criteria:**

```gherkin
GIVEN I navigate to "Security" > "Audit Logs"
WHEN I view the log
THEN I see entries for:
  - User authentication (login, logout, failed attempts)
  - Data access (queries executed, exports)
  - Configuration changes (jobs, DAGs, models)
  - Permission changes (roles, users)
  - Administrative actions

Each entry includes:
  - Timestamp
  - User
  - Action type
  - Resource affected
  - Details (before/after for changes)
  - IP address
  - User agent

WHEN I filter/search logs
THEN I can filter by:
  - Date range
  - User
  - Action type
  - Resource
AND export filtered results to CSV

GIVEN logs are generated
WHEN retention period expires (configurable, default 90 days)
THEN old logs are archived to cold storage
AND remain queryable via separate interface
```

---

#### US-7.7: Super Admin Artifact Portal

**As a** Super Admin  
**I want to** view generated artifacts (code files)  
**So that** I can debug and audit what the system creates

**Acceptance Criteria:**

```gherkin
GIVEN I am logged in as Super Admin
WHEN I navigate to "Artifact Portal"
THEN I see a file browser showing:
  - Tenant selector (dropdown)
  - Artifact type tabs:
    - Airflow DAGs
    - PySpark Scripts
    - dbt Models
    - dbt Schema YAML

WHEN I select a tenant and artifact type
THEN I see list of generated files with:
  - Filename
  - Last modified
  - Generated from (job/DAG/model name)
  - Status (Active, Deprecated)

WHEN I click on a file
THEN I see:
  - Full file content (syntax highlighted)
  - Generation metadata:
    - Template used
    - Input parameters
    - Generated timestamp
    - Generated by user
  - Diff view (compare with previous version)

WHEN I need to debug an issue
THEN I can:
  - Download the file
  - View template that generated it
  - View input configuration
  - Trace back to UI configuration
```

---

#### US-7.8: Tenant Settings & Branding

**As a** Tenant Admin  
**I want to** configure tenant settings and branding  
**So that** I can customize the experience for my organization

**Acceptance Criteria:**

```gherkin
GIVEN I navigate to "Settings" > "General"
WHEN I configure tenant settings
THEN I can set:
  - Organization name
  - Logo (appears in header)
  - Primary color (accent color throughout app)
  - Favicon
  - Login page message
  - Default timezone
  - Date format preference
  - Number format (locale)

WHEN I save settings
THEN branding applies immediately to all users
AND persists across sessions
```

---

#### US-7.9: Resource Usage & Quotas

**As a** Tenant Admin  
**I want to** monitor resource usage against quotas  
**So that** I can manage capacity

**Acceptance Criteria:**

```gherkin
GIVEN I navigate to "Settings" > "Usage"
WHEN I view the dashboard
THEN I see:
  - User count: X / Y (current / limit)
  - Storage used: X GB / Y GB
  - DAG runs this month: X / Y
  - AI queries this month: X / Y
  - Query execution time (total hours)

Each metric shows:
  - Current value
  - Limit (based on subscription)
  - Trend chart (last 30 days)
  - % utilized with color coding (green/yellow/red)

GIVEN usage approaches limit (>80%)
WHEN threshold is crossed
THEN Tenant Admin receives notification email
AND banner appears in UI

GIVEN usage exceeds limit
WHEN user attempts action
THEN action is blocked
AND user sees upgrade prompt
```

---

## 6. Non-Functional Requirements

### NFR-1: Performance

| Metric | Requirement |
|--------|-------------|
| Page load time | < 2 seconds for 95th percentile |
| Query execution | < 30 seconds for 95th percentile |
| DAG deployment | < 60 seconds end-to-end |
| Chart rendering | < 3 seconds for 95th percentile |
| Concurrent users per tenant | 100 minimum |
| API response time | < 500ms for 95th percentile |

### NFR-2: Scalability

| Aspect | Requirement |
|--------|-------------|
| Tenant count | 500+ tenants supported |
| Data volume per tenant | Up to 1TB in ClickHouse |
| DAGs per tenant | Up to 500 active DAGs |
| Concurrent DAG runs (platform) | 1000+ |
| Horizontal scaling | All stateless components must support horizontal scaling |

### NFR-3: Availability

| Metric | Requirement |
|--------|-------------|
| Uptime SLA | 99.9% monthly |
| Planned maintenance window | Max 4 hours/month, announced 72h ahead |
| RPO (Recovery Point Objective) | 1 hour |
| RTO (Recovery Time Objective) | 4 hours |
| Backup frequency | Daily full, hourly incremental |

### NFR-4: Security

| Requirement | Details |
|-------------|---------|
| Authentication | SSO (SAML, OIDC), MFA support |
| Authorization | RBAC, RLS enforced at API and database level |
| Encryption at rest | AES-256 for all data stores |
| Encryption in transit | TLS 1.3 for all communications |
| Credential storage | Vault or encrypted secret manager |
| Penetration testing | Annual third-party assessment |
| Compliance | SOC 2 Type II, GDPR compliant |

### NFR-5: Observability

| Aspect | Implementation |
|--------|----------------|
| Application logging | Structured JSON logs to centralized log store |
| Metrics | Prometheus metrics exposed for all services |
| Tracing | Distributed tracing (OpenTelemetry) |
| Alerting | PagerDuty integration for critical alerts |
| Dashboards | Grafana dashboards for platform health |

### NFR-6: Usability

| Requirement | Details |
|-------------|---------|
| Browser support | Chrome, Firefox, Safari, Edge (latest 2 versions) |
| Mobile | Responsive design for dashboard viewing |
| Accessibility | WCAG 2.1 AA compliance |
| Documentation | Comprehensive user guide and API docs |
| Onboarding | Guided tours for first-time users |

---

## 7. Glossary

| Term | Definition |
|------|------------|
| **DAG** | Directed Acyclic Graph - Airflow's representation of a workflow |
| **dbt** | Data Build Tool - SQL-based transformation framework |
| **RLS** | Row-Level Security - Filtering data based on user attributes |
| **RBAC** | Role-Based Access Control - Permission assignment via roles |
| **SCD** | Slowly Changing Dimension - Techniques for tracking historical changes |
| **Semantic Layer** | Business-friendly data model abstracting raw tables |
| **Template Engine** | System that fills pre-approved code templates with user inputs |
| **Tenant** | An isolated customer organization on the platform |
| **PySpark** | Python API for Apache Spark distributed computing |
| **ClickHouse** | Column-oriented OLAP database for analytics |
| **Ollama** | Local LLM runtime for AI features |

---

## Document Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Product Owner | | | |
| Technical Lead | | | |
| Security Lead | | | |
| QA Lead | | | |

---

*End of Business Requirement Document*
