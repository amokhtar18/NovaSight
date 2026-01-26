# 047 - User Documentation

## Metadata

```yaml
prompt_id: "047"
phase: 6
agent: "@orchestrator"
model: "opus 4.5"
priority: P1
estimated_effort: "3 days"
dependencies: ["all previous"]
```

## Objective

Create comprehensive user documentation for the NovaSight platform.

## Task Description

Write user-facing documentation covering all features, tutorials, and best practices.

## Requirements

### Documentation Structure

```markdown
docs/
├── getting-started/
│   ├── README.md
│   ├── quick-start.md
│   ├── concepts.md
│   └── first-dashboard.md
├── guides/
│   ├── data-sources/
│   │   ├── connecting-postgresql.md
│   │   ├── connecting-mysql.md
│   │   ├── connecting-s3.md
│   │   └── sync-configuration.md
│   ├── semantic-layer/
│   │   ├── dimensions-measures.md
│   │   ├── relationships.md
│   │   └── calculated-fields.md
│   ├── dashboards/
│   │   ├── building-dashboards.md
│   │   ├── widget-types.md
│   │   ├── filters-interactions.md
│   │   └── sharing-permissions.md
│   ├── natural-language/
│   │   ├── how-it-works.md
│   │   ├── writing-queries.md
│   │   └── tips-tricks.md
│   └── administration/
│       ├── user-management.md
│       ├── tenant-settings.md
│       └── security-audit.md
├── reference/
│   ├── api/
│   ├── sql-reference.md
│   └── keyboard-shortcuts.md
└── troubleshooting/
    ├── common-issues.md
    ├── performance.md
    └── faq.md
```

### Getting Started Guide

```markdown
<!-- docs/getting-started/quick-start.md -->
# Quick Start Guide

Welcome to NovaSight! This guide will help you get up and running in minutes.

## Prerequisites

- A NovaSight account (sign up at https://novasight.io)
- Access to a data source (database credentials or API access)

## Step 1: Connect Your Data

1. Navigate to **Data Sources** in the sidebar
2. Click **Add Data Source**
3. Select your database type (PostgreSQL, MySQL, etc.)
4. Enter your connection details:
   - Host: Your database server address
   - Port: Database port (e.g., 5432 for PostgreSQL)
   - Database: Database name
   - Username/Password: Your credentials

![Connect Data Source](./images/connect-datasource.png)

5. Click **Test Connection** to verify
6. Click **Save** to add the data source

> 💡 **Tip**: Use read-only credentials for safety

## Step 2: Define Your Semantic Layer

The semantic layer translates your database schema into business terms.

1. Go to **Semantic Layer** > **Models**
2. Click **Create Model**
3. Select tables from your data source
4. Define dimensions (things you group by):
   - Customer Name
   - Product Category
   - Region
5. Define measures (things you calculate):
   - Total Sales
   - Order Count
   - Average Order Value

![Semantic Layer](./images/semantic-layer.png)

## Step 3: Ask Questions

Now you can ask questions in plain English!

1. Go to the **Query** page
2. Type your question: "What were total sales by region last month?"
3. Press Enter or click **Ask**
4. View your results in a chart or table

![Query Interface](./images/query-interface.png)

## Step 4: Build a Dashboard

Save your insights to a dashboard:

1. After running a query, click **Save to Dashboard**
2. Create a new dashboard or choose an existing one
3. Add more widgets by clicking **Add Widget**
4. Drag and resize widgets to organize your layout
5. Click **Save** when done

![Dashboard Builder](./images/dashboard-builder.png)

## Next Steps

- [Understanding Concepts](./concepts.md)
- [Building Your First Dashboard](./first-dashboard.md)
- [Data Source Deep Dive](../guides/data-sources/)
```

### Feature Guide

```markdown
<!-- docs/guides/natural-language/writing-queries.md -->
# Writing Effective Natural Language Queries

NovaSight uses AI to understand your questions and translate them into database queries. Here's how to get the best results.

## Basic Query Patterns

### Aggregations
Ask for totals, averages, counts, etc.

| What You Type | What You Get |
|---------------|--------------|
| "Total sales" | Sum of all sales |
| "Average order value" | Mean order amount |
| "Number of customers" | Count of customers |
| "Minimum price" | Lowest price |

### Grouping
Add "by" to group your results.

| What You Type | What You Get |
|---------------|--------------|
| "Sales by region" | Sales broken down by region |
| "Orders by month" | Orders grouped by month |
| "Revenue by product category" | Revenue per category |

### Filtering
Use time periods and conditions.

| What You Type | What You Get |
|---------------|--------------|
| "Sales last month" | Sales from the previous month |
| "Orders this year" | Orders from current year |
| "Customers in California" | Only CA customers |
| "Products over $100" | Products priced above $100 |

## Time-Based Queries

### Relative Time
- "yesterday"
- "last week"
- "last 30 days"
- "this quarter"
- "year over year"

### Specific Periods
- "in January 2024"
- "between March and June"
- "Q1 2024"

### Comparisons
- "compared to last month"
- "vs same period last year"
- "growth from Q1 to Q2"

## Advanced Patterns

### Top/Bottom N
```
Top 10 customers by revenue
Bottom 5 products by sales
Highest selling region
```

### Percentages
```
Percentage of orders by category
Sales as % of total
YoY growth percentage
```

### Trends
```
Sales trend over last 12 months
Daily order trend
Revenue growth by quarter
```

## Tips for Better Results

### ✅ Do

1. **Be specific about metrics**: "total revenue" not just "money"
2. **Name your dimensions**: "by product category" not "by type"
3. **Include time context**: "last month" or "in 2024"
4. **Use business terms**: Match your semantic layer definitions

### ❌ Don't

1. **Avoid ambiguity**: "Show me the data" is too vague
2. **Don't ask for raw SQL**: The system generates SQL for you
3. **Avoid complex calculations in one query**: Break them up

## Troubleshooting

### "I didn't understand that query"

Try rephrasing with:
- Clearer metric names
- Specific dimension names
- Simpler sentence structure

### Results don't look right

1. Check your semantic layer definitions
2. Verify the generated SQL in the query details
3. Try a simpler version of your question

### Query is slow

- Narrow the time range
- Reduce the number of dimensions
- Consider pre-aggregating in your semantic layer
```

### Administrator Guide

```markdown
<!-- docs/guides/administration/security-audit.md -->
# Security and Audit Guide

This guide covers security features and audit capabilities for administrators.

## Audit Logging

NovaSight maintains comprehensive audit logs for compliance and security monitoring.

### What's Logged

| Category | Events |
|----------|--------|
| Authentication | Login, logout, failed attempts, password changes |
| Data Access | Query execution, data exports |
| Configuration | Data source changes, permission updates |
| Administration | User creation, role changes, tenant settings |

### Viewing Audit Logs

1. Navigate to **Admin** > **Audit Logs**
2. Use filters to narrow results:
   - User
   - Action type
   - Date range
   - Severity

### Log Retention

- Default retention: 90 days
- Configurable per tenant
- Exportable for long-term archival

## Role-Based Access Control

### Default Roles

| Role | Permissions |
|------|-------------|
| **Admin** | Full access to all features |
| **Analyst** | Create/edit dashboards, run queries |
| **Viewer** | View shared dashboards only |

### Custom Roles

Create custom roles with granular permissions:

1. Go to **Admin** > **Roles**
2. Click **Create Role**
3. Select permissions:
   - Data Sources: View, Create, Edit, Delete
   - Semantic Layer: View, Create, Edit, Delete
   - Dashboards: View, Create, Edit, Delete, Share
   - Users: View, Create, Edit, Delete
   - Admin: Access admin panel

### Permission Inheritance

Roles can inherit from parent roles:

```
Admin
└── Analyst
    └── Viewer
```

## Security Best Practices

### User Management

- ✅ Use strong password policies
- ✅ Enable MFA (when available)
- ✅ Review inactive users regularly
- ✅ Use least-privilege access

### Data Source Security

- ✅ Use read-only credentials
- ✅ Rotate credentials periodically
- ✅ Limit network access to your databases
- ✅ Enable SSL for all connections

### Dashboard Security

- ✅ Review sharing permissions
- ✅ Audit who has access to sensitive dashboards
- ✅ Use row-level security when needed

## Compliance Features

### SOC 2 Support

- Audit logging
- Access controls
- Encryption at rest and in transit
- Regular security assessments

### GDPR Support

- Data export capabilities
- User data deletion
- Consent management
- Data location controls
```

## Expected Output

```
docs/
├── index.md
├── getting-started/
│   ├── README.md
│   ├── quick-start.md
│   ├── concepts.md
│   └── first-dashboard.md
├── guides/
│   ├── data-sources/
│   ├── semantic-layer/
│   ├── dashboards/
│   ├── natural-language/
│   └── administration/
├── reference/
│   ├── api/
│   ├── sql-reference.md
│   └── keyboard-shortcuts.md
├── troubleshooting/
├── images/
└── mkdocs.yml
```

## Acceptance Criteria

- [ ] Quick start guide complete
- [ ] All features documented
- [ ] Screenshots included
- [ ] Code examples provided
- [ ] Search functionality works
- [ ] Mobile-friendly layout
- [ ] PDF export available
- [ ] Version switching works

## Reference Documents

- [Orchestrator Agent](../agents/novasight-orchestrator.agent.md)
- [All Feature Prompts](./README.md)
