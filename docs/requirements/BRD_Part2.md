---

### EPIC 3: dbt Semantic Layer Configuration

**Epic Description:** Enable users to build and manage dbt models through a visual interface, creating a governed semantic layer that serves as the single source of truth for business metrics.

**Business Value:** Provides business users with consistent, validated metrics while maintaining data lineage and documentation automatically.

---

#### US-3.1: Create dbt Model via GUI

**As a** BI Developer  
**I want to** create a dbt model through a visual interface  
**So that** I can define transformations without writing SQL manually

**Acceptance Criteria:**

```gherkin
GIVEN I am on the "Semantic Layer" page
WHEN I click "Create New Model"
THEN I see a model builder with:
  - Model name input (validated: lowercase, underscores only)
  - Description field (for documentation)
  - Materialization dropdown (view, table, incremental)
  - Source table selector (from existing models or raw tables)

GIVEN I select a source table
WHEN the table loads
THEN I see a visual column picker showing:
  - All available columns
  - Column descriptions (if documented)
  - Data types

WHEN I select columns and configure the model
THEN a preview panel shows the generated SQL (read-only)
AND the SQL is generated from dbt_model_template.sql.j2
```

---

#### US-3.2: Visual Join Builder

**As a** BI Developer  
**I want to** join multiple tables visually  
**So that** I can create denormalized models without writing JOIN syntax

**Acceptance Criteria:**

```gherkin
GIVEN I am creating a model with multiple sources
WHEN I add a second source table
THEN a join configuration panel appears

WHEN I configure a join
THEN I can specify:
  - Join type (INNER, LEFT, RIGHT, FULL)
  - Join columns (drag-drop or dropdown)
  - Join alias (optional)

GIVEN I configure multiple joins
WHEN I view the model diagram
THEN I see a visual representation of table relationships
AND can click any join to edit it

WHEN the model is saved
THEN the JOIN SQL is generated from join_template.sql.j2
```

---

#### US-3.3: Define Calculated Columns

**As a** BI Developer  
**I want to** create calculated columns using a formula builder  
**So that** I can add business logic without raw SQL

**Acceptance Criteria:**

```gherkin
GIVEN I am in the model builder
WHEN I click "Add Calculated Column"
THEN I see a formula builder with:
  - Column name input
  - Formula type dropdown:
    - Arithmetic (+, -, *, /)
    - Aggregation (SUM, AVG, COUNT, MIN, MAX)
    - Conditional (CASE WHEN)
    - Date functions (DATE_DIFF, DATE_TRUNC)
    - String functions (CONCAT, SUBSTRING)
  - Column selector for operands
  - Preview of generated expression

GIVEN I build a formula
WHEN I click "Validate"
THEN the system checks syntax validity
AND shows expected output data type

GIVEN formula is valid
WHEN I save the model
THEN the calculated column is included in generated SQL
```

---

#### US-3.4: Configure dbt Tests

**As a** BI Developer  
**I want to** add data quality tests to my models  
**So that** data issues are caught before reaching dashboards

**Acceptance Criteria:**

```gherkin
GIVEN I am configuring a model
WHEN I click on a column
THEN I see a "Tests" tab with options:
  - unique: Ensure all values are unique
  - not_null: Ensure no NULL values
  - accepted_values: Specify allowed values list
  - relationships: Referential integrity check
  - Custom threshold: (e.g., "values must be > 0")

WHEN I add tests to columns
THEN tests are stored in model metadata
AND generated in schema.yml from dbt_test_template.yml.j2

GIVEN tests are configured
WHEN dbt runs
THEN test results are captured and displayed in UI
```

---

#### US-3.5: Model Documentation

**As a** BI Developer  
**I want to** document my models and columns  
**So that** business users understand what data means

**Acceptance Criteria:**

```gherkin
GIVEN I am editing a model
WHEN I click "Documentation" tab
THEN I can add:
  - Model description (Markdown supported)
  - Column descriptions for each column
  - Tags for categorization
  - Owner assignment

WHEN I save documentation
THEN it's stored in metadata AND generated in schema.yml
AND appears in the data catalog
```

---

#### US-3.6: Model Lineage Visualization

**As a** BI Developer  
**I want to** see the lineage of my models  
**So that** I understand data flow and impact of changes

**Acceptance Criteria:**

```gherkin
GIVEN I am viewing a model
WHEN I click "View Lineage"
THEN I see an interactive DAG showing:
  - Upstream sources (raw tables, other models)
  - The current model
  - Downstream dependents (other models, dashboards)

WHEN I click on any node
THEN I see a summary panel with:
  - Model name and description
  - Last run timestamp
  - Row count
  - Link to full details
```

---

### EPIC 4: Airflow Orchestration GUI

**Epic Description:** Provide a visual, low-code interface for building Apache Airflow DAGs, enabling users to sequence data ingestion and transformation tasks without writing Python code.

**Business Value:** Reduces DAG development time from days to minutes while ensuring all DAGs follow security-approved patterns.

---

#### US-4.1: Visual DAG Builder

**As a** Data Engineer  
**I want to** build Airflow DAGs using drag-and-drop  
**So that** I can orchestrate data pipelines visually

**Acceptance Criteria:**

```gherkin
GIVEN I am on the "Orchestration" page
WHEN I click "Create New DAG"
THEN I see a canvas with:
  - LEFT: Palette of available task types
    - PySpark Ingestion Job (from saved jobs)
    - dbt Run (model/tag/all)
    - dbt Test
    - SQL Query
    - Email Notification
    - HTTP Sensor
    - Time Sensor
  - CENTER: Canvas for building DAG
  - RIGHT: Properties panel for selected task

WHEN I drag a task onto the canvas
THEN it appears as a node
AND the properties panel shows configuration options

WHEN I connect two tasks (drag from one to another)
THEN a dependency arrow appears
AND the downstream task depends on upstream completion
```

---

#### US-4.2: Configure DAG Properties

**As a** Data Engineer  
**I want to** set DAG-level properties  
**So that** the pipeline runs on my desired schedule

**Acceptance Criteria:**

```gherkin
GIVEN I am editing a DAG
WHEN I open "DAG Properties"
THEN I can configure:
  - DAG ID (auto-generated, editable)
  - Description
  - Schedule: 
    - Preset (Hourly, Daily, Weekly, Monthly)
    - Custom CRON expression (with preview)
    - Manual only (no schedule)
  - Start Date (date picker)
  - Catchup (Yes/No)
  - Max Active Runs (default: 1)
  - Default Retry Policy:
    - Retries (0-5)
    - Retry Delay (minutes)
  - Tags (for filtering)

WHEN I set a CRON expression
THEN I see next 5 scheduled run times
AND validation if expression is invalid
```

---

#### US-4.3: Configure Task Properties

**As a** Data Engineer  
**I want to** configure individual task properties  
**So that** each task behaves correctly

**Acceptance Criteria:**

```gherkin
GIVEN I select a PySpark Ingestion task
WHEN I view properties panel
THEN I see:
  - Task ID (editable)
  - Select Ingestion Job (dropdown of saved jobs)
  - Timeout (minutes)
  - Retry policy (inherit from DAG or override)
  - Trigger rule (all_success, one_success, all_failed, etc.)

GIVEN I select a dbt Run task
WHEN I view properties
THEN I see:
  - Task ID
  - Run mode: 
    - Specific model(s) (multi-select)
    - Tag-based (select tags)
    - Full run
  - Include tests (Yes/No)
  - Full refresh (Yes/No)

GIVEN I select an Email Notification task
WHEN I view properties
THEN I see:
  - Recipients (email list)
  - Subject template
  - Body template (with variable placeholders)
  - Attach logs (Yes/No)
```

---

#### US-4.4: DAG Validation

**As a** Data Engineer  
**I want to** validate my DAG before deployment  
**So that** I catch configuration errors early

**Acceptance Criteria:**

```gherkin
GIVEN I have built a DAG
WHEN I click "Validate"
THEN the system checks:
  - No orphan tasks (all connected)
  - No circular dependencies
  - All required task properties filled
  - All referenced jobs/models exist
  - CRON expression valid

GIVEN validation fails
WHEN I view results
THEN I see a list of issues with:
  - Severity (Error, Warning)
  - Description
  - Click to highlight affected task

GIVEN validation passes
WHEN I view results
THEN I see "Ready to Deploy" status
```

---

#### US-4.5: Deploy DAG

**As a** Data Engineer  
**I want to** deploy my DAG to Airflow  
**So that** it becomes active and scheduled

**Acceptance Criteria:**

```gherkin
GIVEN my DAG is validated
WHEN I click "Deploy"
THEN the system:
  - Generates DAG Python file from dag_template.py.j2
  - Stores file in tenant's DAG folder
  - Triggers Airflow DAG refresh
  - Shows deployment status

GIVEN deployment succeeds
WHEN I view the DAG list
THEN my DAG appears with status "Active"
AND shows next scheduled run time

GIVEN deployment fails
WHEN I view error
THEN I see specific error message
AND can retry after fixing
```

---

#### US-4.6: Trigger Manual DAG Run

**As a** Data Engineer  
**I want to** manually trigger a DAG run  
**So that** I can test or run on-demand

**Acceptance Criteria:**

```gherkin
GIVEN I am viewing a deployed DAG
WHEN I click "Trigger Run"
THEN I see a confirmation dialog with:
  - Option to pass runtime parameters (if DAG supports)
  - Execution date (default: now)

WHEN I confirm trigger
THEN a new DAG run starts
AND I'm taken to the run monitoring view
```

---

#### US-4.7: Monitor DAG Runs

**As a** Data Engineer  
**I want to** monitor DAG execution in real-time  
**So that** I can track progress and troubleshoot failures

**Acceptance Criteria:**

```gherkin
GIVEN I navigate to DAG Runs page
WHEN I view the list
THEN I see all runs with:
  - Run ID
  - Status (Running, Success, Failed, Queued)
  - Start time
  - Duration
  - Trigger type (Scheduled, Manual)

WHEN I click on a run
THEN I see task-level view:
  - Visual DAG with task status colors
    - Green: Success
    - Red: Failed
    - Yellow: Running
    - Gray: Pending
  - Click task for details

WHEN I click a task
THEN I see:
  - Task logs (streaming if running)
  - Start/end timestamps
  - Retry attempts
  - XCom values (if any)
```

---

#### US-4.8: Pause/Resume DAG

**As a** Data Engineer  
**I want to** pause a DAG's schedule  
**So that** I can perform maintenance without deleting it

**Acceptance Criteria:**

```gherkin
GIVEN I am viewing an active DAG
WHEN I click "Pause"
THEN the DAG stops being scheduled
AND status shows "Paused"
AND currently running instances continue to completion

GIVEN a DAG is paused
WHEN I click "Resume"
THEN scheduling resumes
AND status shows "Active"
AND next run is calculated from schedule
```

---

#### US-4.9: View DAG History & Metrics

**As a** Data Engineer  
**I want to** view historical DAG performance  
**So that** I can identify trends and optimize

**Acceptance Criteria:**

```gherkin
GIVEN I am viewing a DAG
WHEN I click "History & Metrics"
THEN I see:
  - Run history chart (success/fail over time)
  - Average duration trend
  - Task duration breakdown
  - Failure rate by task

WHEN I select a date range
THEN charts update to show selected period
AND I can export data to CSV
```
