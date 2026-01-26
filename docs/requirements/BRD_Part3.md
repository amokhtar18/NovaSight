---

### EPIC 5: KPI Alerting System

**Epic Description:** Enable users to define threshold-based alerts on business KPIs, with automated scheduling and multi-channel notifications.

**Business Value:** Proactive issue detection reduces response time from hours to minutes, preventing business impact before it escalates.

---

#### US-5.1: Create KPI Alert

**As a** BI Developer  
**I want to** create alerts on semantic layer KPIs  
**So that** stakeholders are notified when thresholds are breached

**Acceptance Criteria:**

```gherkin
GIVEN I am on the "Alerts" page
WHEN I click "Create Alert"
THEN I see a wizard with:

STEP 1 - Select KPI:
  - Browse semantic layer models
  - Select measure/metric column
  - Preview current value
  - Filter scope (optional: by dimension values)

STEP 2 - Define Condition:
  - Operator dropdown:
    - Less than (<)
    - Greater than (>)
    - Equals (=)
    - Not equals (≠)
    - Between
    - Outside range
    - Percent change from previous
  - Threshold value(s) input
  - Comparison period (for % change)

STEP 3 - Configure Schedule:
  - Check frequency:
    - Every N minutes (min: 5)
    - Hourly
    - Daily at specific time
    - Custom CRON
  - Time zone selection
  - Effective period (optional: only during business hours)

STEP 4 - Set Notifications:
  - Email recipients (multi-select from tenant users + manual entry)
  - Email subject template
  - Include: Current value, threshold, timestamp
  - Optional: Attach snapshot chart

STEP 5 - Review & Activate:
  - Summary of configuration
  - Test alert (dry run)
  - Activate immediately or schedule activation
```

---

#### US-5.2: Alert Condition Builder

**As a** BI Developer  
**I want to** build complex alert conditions  
**So that** I can create nuanced business rules

**Acceptance Criteria:**

```gherkin
GIVEN I am defining alert conditions
WHEN I click "Advanced Mode"
THEN I can build compound conditions:
  - AND/OR logic between conditions
  - Multiple metrics in same alert
  - Comparison between two metrics (e.g., Revenue < Cost)

Example Compound Alert:
  (Daily_Sales < 10000) AND (Inventory_Level < 500)

WHEN I configure a compound alert
THEN the system validates all metrics exist
AND displays a natural language summary:
  "Alert when Daily Sales is below $10,000 AND Inventory Level is below 500 units"
```

---

#### US-5.3: Alert Templates

**As a** BI Developer  
**I want to** create reusable alert templates  
**So that** common patterns can be quickly applied

**Acceptance Criteria:**

```gherkin
GIVEN I have created an alert
WHEN I click "Save as Template"
THEN I can specify:
  - Template name
  - Description
  - Parameterized values (e.g., threshold as variable)

GIVEN a template exists
WHEN I create a new alert
THEN I can choose "From Template"
AND fill in the parameterized values
AND customize further if needed
```

---

#### US-5.4: Alert Dashboard

**As a** Data Engineer  
**I want to** view all alerts in a central dashboard  
**So that** I can monitor alert health and activity

**Acceptance Criteria:**

```gherkin
GIVEN I navigate to Alert Dashboard
WHEN the page loads
THEN I see:
  - Summary cards:
    - Total Active Alerts
    - Alerts Triggered (last 24h)
    - Alerts in Error State
  - Alert list with columns:
    - Alert Name
    - KPI
    - Condition
    - Last Check
    - Last Triggered
    - Status (Active/Paused/Error)

WHEN I filter by status
THEN the list updates accordingly

WHEN I click an alert
THEN I see alert detail page with:
  - Configuration summary
  - Trigger history (timeline)
  - Performance chart (metric value over time with threshold line)
```

---

#### US-5.5: Alert History & Audit

**As a** Tenant Admin  
**I want to** view complete alert trigger history  
**So that** I can audit and analyze alert patterns

**Acceptance Criteria:**

```gherkin
GIVEN I am viewing an alert
WHEN I click "History"
THEN I see:
  - List of all triggers with:
    - Timestamp
    - Metric value at trigger
    - Threshold at time
    - Recipients notified
    - Delivery status (Sent/Failed)
  - Export to CSV option

WHEN I click a specific trigger
THEN I see:
  - Full notification content (email preview)
  - Delivery log with timestamps
  - Any errors encountered
```

---

#### US-5.6: Snooze & Acknowledge Alerts

**As a** Data Analyst  
**I want to** snooze or acknowledge triggered alerts  
**So that** I can manage alert fatigue

**Acceptance Criteria:**

```gherkin
GIVEN an alert has triggered
WHEN I receive the notification
THEN I can click "Acknowledge" link in email
AND the alert is marked as acknowledged
AND acknowledgment is logged with user and timestamp

GIVEN I am viewing a triggered alert
WHEN I click "Snooze"
THEN I can specify snooze duration (1h, 4h, 24h, custom)
AND the alert won't trigger again until snooze expires
AND snooze is logged in history
```

---

### EPIC 6: Data Exploration & AI

**Epic Description:** Provide self-service data exploration tools including SQL querying, chart building, dashboard creation, and AI-powered natural language data interaction.

**Business Value:** Empowers business users to find insights independently, reducing dependency on technical teams by 70%.

---

#### US-6.1: SQL Query Editor

**As a** Data Analyst  
**I want to** write and execute SQL queries  
**So that** I can explore data flexibly

**Acceptance Criteria:**

```gherkin
GIVEN I am on the "Explore" page
WHEN I open the SQL Editor
THEN I see:
  - LEFT: Schema browser (expandable tree)
    - Shows only tables/models user has access to (RLS)
  - CENTER: Query editor with:
    - Syntax highlighting
    - Auto-complete for tables/columns
    - Multiple tabs for queries
    - Query history sidebar
  - BOTTOM: Results panel

WHEN I write a query and click "Run"
THEN the query executes against ClickHouse
AND results display in a paginated table
AND I see execution time and row count

WHEN query has errors
THEN error message displays with line number highlight

WHEN I am satisfied with results
THEN I can:
  - Export to CSV/Excel
  - Save query for later
  - Create chart from results
```

---

#### US-6.2: Query Parameterization

**As a** Data Analyst  
**I want to** create parameterized queries  
**So that** I can reuse queries with different inputs

**Acceptance Criteria:**

```gherkin
GIVEN I am writing a query
WHEN I include {{parameter_name}} syntax
THEN the editor recognizes it as a parameter

WHEN I click "Run"
THEN a parameter input form appears
AND I must fill all parameters before execution

GIVEN I save a parameterized query
WHEN I or others run it later
THEN the parameter form appears with:
  - Parameter name
  - Input type (text, number, date, dropdown)
  - Default value (if set)
```

---

#### US-6.3: Visual Chart Builder

**As a** Data Analyst  
**I want to** create charts from query results  
**So that** I can visualize patterns and trends

**Acceptance Criteria:**

```gherkin
GIVEN I have query results
WHEN I click "Create Chart"
THEN I see a chart builder with:
  - Chart type selector:
    - Bar (horizontal/vertical)
    - Line
    - Area
    - Pie/Donut
    - Scatter
    - Table (formatted)
    - Big Number (KPI card)
    - Map (if geo data)
  - Data mapping panel:
    - Drag columns to X-axis, Y-axis, Color, Size
    - Aggregation selector for Y-axis
  - Styling options:
    - Colors/themes
    - Labels
    - Legend position
    - Axis formatting

WHEN I configure the chart
THEN preview updates in real-time

WHEN I click "Save Chart"
THEN I can:
  - Name the chart
  - Add to existing dashboard or create new
  - Set refresh schedule (for live data)
```

---

#### US-6.4: Dashboard Builder

**As a** Data Analyst  
**I want to** create interactive dashboards  
**So that** I can share insights with stakeholders

**Acceptance Criteria:**

```gherkin
GIVEN I am on the "Dashboards" page
WHEN I click "Create Dashboard"
THEN I see:
  - Canvas with grid layout
  - Component palette:
    - Saved charts
    - Text/Markdown boxes
    - Filters
    - Dividers
    - Images/logos

WHEN I drag a chart onto canvas
THEN I can:
  - Resize by dragging corners
  - Reposition by dragging
  - Configure via properties panel

WHEN I add a Filter component
THEN I can:
  - Link to multiple charts
  - Configure filter type (dropdown, date range, search)
  - Set default values

WHEN I save the dashboard
THEN I can:
  - Set title and description
  - Configure refresh interval
  - Set access permissions
```

---

#### US-6.5: Dashboard Sharing & Embedding

**As a** Data Analyst  
**I want to** share dashboards with others  
**So that** stakeholders can access insights

**Acceptance Criteria:**

```gherkin
GIVEN I have a saved dashboard
WHEN I click "Share"
THEN I see options:
  - Share with users (select from tenant)
  - Share with roles
  - Generate public link (if allowed by admin)
  - Embed code (iframe snippet)

GIVEN I share with specific users
WHEN they log in
THEN the dashboard appears in their "Shared with Me" section

GIVEN I generate embed code
WHEN it's used in external site
THEN the dashboard renders (respecting RLS of authenticated user)
```

---

#### US-6.6: AI Chat with Data

**As a** Data Analyst  
**I want to** ask questions about data in natural language  
**So that** I can get insights without writing SQL

**Acceptance Criteria:**

```gherkin
GIVEN I am on the "AI Assistant" page
WHEN I type a natural language question
THEN the AI:
  - Receives a system prompt containing:
    - Available tables/models (filtered by user's RLS)
    - Column descriptions from semantic layer
    - Tenant context
  - Generates SQL based on question
  - Shows generated SQL for transparency
  - Executes query (with user approval optional)
  - Presents results with explanation

Example interaction:
  User: "What were the top 5 products by revenue last month?"
  AI: 
    - Shows generated SQL
    - Displays results table
    - Provides natural language summary

WHEN AI cannot answer
THEN it explains why and suggests alternatives

WHEN user asks follow-up questions
THEN AI maintains conversation context
```

---

#### US-6.7: AI Guardrails & Transparency

**As a** Tenant Admin  
**I want to** configure AI behavior and limits  
**So that** I can ensure safe and appropriate AI usage

**Acceptance Criteria:**

```gherkin
GIVEN I am in Tenant Admin settings
WHEN I configure AI settings
THEN I can:
  - Enable/disable AI features per role
  - Set query complexity limits
  - Require SQL approval before execution
  - View all AI-generated queries (audit log)
  - Configure custom system prompt additions

GIVEN AI generates a query
WHEN it would access restricted data
THEN RLS is enforced server-side
AND query only returns permitted rows

GIVEN AI is used
WHEN query executes
THEN audit log captures:
  - User
  - Original question
  - Generated SQL
  - Execution result
  - Timestamp
```

---

#### US-6.8: Saved Questions & Favorites

**As a** Data Analyst  
**I want to** save and organize my queries and charts  
**So that** I can quickly access frequently used analyses

**Acceptance Criteria:**

```gherkin
GIVEN I have created queries and charts
WHEN I click "Save"
THEN I can:
  - Name the item
  - Add to folder (create new or select existing)
  - Add tags
  - Mark as favorite

GIVEN I navigate to "My Work"
THEN I see:
  - Favorites (quick access)
  - Recent (last 20 items)
  - Folders (organized view)
  - Shared with me

WHEN I search my work
THEN I can filter by:
  - Type (query, chart, dashboard)
  - Tags
  - Created date
  - Folder
```
